"""Run every model module, link, validate and write model/<build_id>/."""

from __future__ import annotations

import json
import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from . import abilities, buildings, characters, effects, factions, items, regions, technologies, units
from .context import Context, by_key
from .images import INLINE_ICONS, ImageIndex, inline_targets
from .link_report import link_report
from .schemas import ENTITY_MODELS
from .text import round_float

log = logging.getLogger(__name__)

MODEL_VERSION = 3
MODULES = [effects, abilities, units, characters, technologies, buildings, items, factions, regions]

# (target type, field, relation, source type or None for any)
REVERSE = [
    ("effect", "sources", "effect", None),
    ("ability", "units", "abilities", "unit"),
    ("ability", "characters", "abilities", "character"),
    ("ability", "modified_by_effects", "bonus_target", "effect"),
    ("character", "items", "agent_subtypes", "item"),
    ("skill", "characters", "skill_tree", "character"),
    ("faction", "units", "custom_battle_factions", "unit"),
    ("faction", "characters", "factions", "character"),
    ("culture", "subcultures", "culture", "subculture"),
    ("culture", "factions", "culture", "faction"),
    ("subculture", "factions", "subculture", "faction"),
]

# Extra fields copied into index/<type>.json next to key and name.
INDEX_FIELDS = {
    "unit": ["caste", "category", "unit_class", "tier", "is_naval"],
    "character": ["agent_types", "is_caster"],
    "skill": ["unlocked_at_rank"],
    "ability": ["type", "source_type"],
    "effect": ["category"],
    "effect_bundle": ["target"],
    "building_level": ["level", "cultures"],
    "building_chain": ["category"],
    "technology": ["is_hidden"],
    "item": ["category", "legendary"],
    "trait": ["hidden"],
    "difficulty_level": ["level"],
    "campaign_variable": ["value"],
    "region": ["campaign", "is_settlement", "template_source"],
    "province": ["campaign"],
}

# Counters builders add to ctx.tally; each is written to the manifest, 0 when never touched.
QUALITY_COUNTS = (
    "effect_applications_without_scope_text",
    "unmatched_rarity_scores",
    "unresolved_agent_type_names",
    "campaign_exclusive_permissions_excluded",
    "unresolved_building_availability_keys",
    "ui_labels_without_text",
)


def round_floats(value):
    """Round every float in a JSON-like value; ints, bools and strings are unchanged."""
    if isinstance(value, float):
        return round_float(value)
    if isinstance(value, dict):
        return {k: round_floats(v) for k, v in value.items()}
    if isinstance(value, list):
        return [round_floats(v) for v in value]
    return value


def unnamed_by_type(entities: dict[str, list[dict]]) -> dict[str, int]:
    counts = {t: sum(1 for r in rows if "name" in r and r["name"] is None) for t, rows in sorted(entities.items())}
    return {t: n for t, n in counts.items() if n}


class ModelBuildError(Exception):
    pass


def build_all(ctx: Context, modules=MODULES) -> dict[str, list[dict]]:
    for module in modules:
        for entity_type, names in module.catalog(ctx).items():
            ctx.links.register(entity_type, names)

    entities: dict[str, list[dict]] = {}
    for module in modules:
        started = time.perf_counter()
        built = module.build(ctx)
        entities.update(built)
        log.info("%-14s %s in %.1fs", module.__name__.rsplit(".", 1)[-1] if hasattr(module, "__name__") else "module",
                 ", ".join(f"{t}={len(rows)}" for t, rows in built.items()), time.perf_counter() - started)

    for target, field, relation, source_type in REVERSE:
        for entity in entities.get(target, []):
            entity[field] = ctx.links.referrers(target, entity["key"], relation, source_type)

    validated: dict[str, list[dict]] = {}
    for entity_type, rows in entities.items():
        model = ENTITY_MODELS[entity_type]
        out = []
        for entity in rows:
            try:
                out.append(model.model_validate(entity).model_dump(mode="json"))
            except ValidationError as e:
                raise ModelBuildError(f"{entity_type} {entity.get('key')}: {e}") from e
        validated[entity_type] = out
    return validated


def write_output(ctx: Context, entities: dict[str, list[dict]], out_root: Path, build_id: str) -> Path:
    final = out_root / build_id
    staging = out_root / f"{build_id}.partial"
    if staging.exists():
        shutil.rmtree(staging)
    for sub in ("entities", "index", "schema", "images"):
        (staging / sub).mkdir(parents=True)

    for entity_type, rows in sorted(entities.items()):
        with (staging / "entities" / f"{entity_type}.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
            for row in rows:
                fh.write(json.dumps(round_floats(row), ensure_ascii=False) + "\n")
        index = [{"key": r["key"], "name": ctx.links.name(entity_type, r["key"]),
                  **{f: r[f] for f in INDEX_FIELDS.get(entity_type, [])}} for r in rows]
        (staging / "index" / f"{entity_type}.json").write_text(
            json.dumps(round_floats(index), ensure_ascii=False, indent=1), encoding="utf-8")

    for entity_type, model in sorted(ENTITY_MODELS.items()):
        (staging / "schema" / f"{entity_type}.schema.json").write_text(
            json.dumps(model.model_json_schema(mode="serialization"), indent=2), encoding="utf-8")

    # [[img:<key>]] names a ui_tagged_images row; anything else is written as a path.
    tagged = {k: r["image_path"] for k, r in by_key(ctx, "ui_tagged_images", "key").items()}
    inline = {target: ctx.images.resolve("inline", tagged.get(target.strip(), target), INLINE_ICONS)
              for target in inline_targets(entities)}
    (staging / "images" / "inline.json").write_text(
        json.dumps(inline, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    files_copied = ctx.images.copy_used(staging / "images")

    manifest = {
        "build_id": build_id,
        "model_version": MODEL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {t: len(rows) for t, rows in sorted(entities.items())},
        "missing_names": dict(sorted(ctx.missing_names.items())),
        "missing_links": dict(sorted(ctx.links.missing.items())),
        "unresolved_text_targets": len(ctx.loc.unresolved_targets),
        "text": ctx.loc.text_report(),
        "unnamed_by_type": unnamed_by_type(entities),
        **{name: ctx.tally[name] for name in QUALITY_COUNTS},
        "partial": ctx.partial,
        "images": ctx.images.manifest(files_copied),
    }
    manifest.update(ctx.manifest_sections)
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    report = link_report(ctx.con, ctx.tables_read)
    (staging / "link_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    if report["available"]:
        log.info("link report: %s", ", ".join(f"{k} {v}" for k, v in report["summary"].items()))

    # a model is always rebuilt from the database, never patched; keep the old
    # one under a .old suffix until the new one is safely in place, so a
    # failed rename never leaves us with no model at all.
    old = out_root / f"{build_id}.old"
    if old.exists():
        shutil.rmtree(old)
    if final.exists():
        final.rename(old)
    try:
        staging.rename(final)
    except Exception:
        if old.exists():
            old.rename(final)
        raise
    if old.exists():
        shutil.rmtree(old)
    return final


def run(db_path: Path, out_root: Path, raw_root: Path) -> Path:
    started = time.perf_counter()
    ctx = Context.open(db_path)
    try:
        build_id = ctx.con.execute("SELECT build_id FROM _build").fetchone()[0]
        ctx.images = ImageIndex.scan(Path(raw_root) / build_id / "images")
        if not ctx.images.available:
            log.warning("no images at %s; image fields will be null", Path(raw_root) / build_id / "images")
        entities = build_all(ctx)
        absent = sorted(set(ENTITY_MODELS) - set(entities))
        if absent:
            raise ModelBuildError(f"entity types not built: {absent}")
        out = write_output(ctx, entities, out_root, build_id)
    finally:
        ctx.con.close()
    log.info("model %s written to %s in %.0fs; missing names %d, missing links %d, images copied %d, partial types %s",
             build_id, out, time.perf_counter() - started, sum(ctx.missing_names.values()),
             sum(ctx.links.missing.values()), len(ctx.images.used), sorted(ctx.partial) or "none")
    return out
