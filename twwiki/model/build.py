"""Run every model module, link, validate and write model/<build_id>/."""

from __future__ import annotations

import json
import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from . import abilities, buildings, characters, effects, factions, items, technologies, units
from .context import Context
from .schemas import ENTITY_MODELS

log = logging.getLogger(__name__)

MODEL_VERSION = 1
MODULES = [effects, abilities, units, characters, technologies, buildings, items, factions]

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
}


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
    for sub in ("entities", "index", "schema"):
        (staging / sub).mkdir(parents=True)

    for entity_type, rows in sorted(entities.items()):
        with (staging / "entities" / f"{entity_type}.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        index = [{"key": r["key"], "name": ctx.links.name(entity_type, r["key"]),
                  **{f: r[f] for f in INDEX_FIELDS.get(entity_type, [])}} for r in rows]
        (staging / "index" / f"{entity_type}.json").write_text(
            json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")

    for entity_type, model in sorted(ENTITY_MODELS.items()):
        (staging / "schema" / f"{entity_type}.schema.json").write_text(
            json.dumps(model.model_json_schema(), indent=2), encoding="utf-8")

    manifest = {
        "build_id": build_id,
        "model_version": MODEL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {t: len(rows) for t, rows in sorted(entities.items())},
        "missing_names": dict(sorted(ctx.missing_names.items())),
        "missing_links": dict(sorted(ctx.links.missing.items())),
        "unresolved_text_targets": len(ctx.loc.unresolved_targets),
        "partial": ctx.partial,
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if final.exists():
        shutil.rmtree(final)  # a model is always rebuilt from the database, never patched
    staging.rename(final)
    return final


def run(db_path: Path, out_root: Path) -> Path:
    started = time.perf_counter()
    ctx = Context.open(db_path)
    try:
        build_id = ctx.con.execute("SELECT build_id FROM _build").fetchone()[0]
        entities = build_all(ctx)
        absent = sorted(set(ENTITY_MODELS) - set(entities))
        if absent:
            raise ModelBuildError(f"entity types not built: {absent}")
        out = write_output(ctx, entities, out_root, build_id)
    finally:
        ctx.con.close()
    log.info("model %s written to %s in %.0fs; missing names %d, missing links %d, partial types %s",
             build_id, out, time.perf_counter() - started, sum(ctx.missing_names.values()),
             sum(ctx.links.missing.values()), sorted(ctx.partial) or "none")
    return out
