"""Effects, effect bundles, and what each effect targets.

The 53 effect_bonus_value_* tables all say "effect E, bonus type B, applied to
thing T". They are normalised into one BonusTarget list per effect. Column
roles come from the schema metadata in _columns, so new bonus tables in a
patch are picked up without code changes.
"""

from __future__ import annotations

from collections import defaultdict

from .context import Context, opt

ENTITY_TYPE_FOR_TABLE = {
    "main_units": "unit",
    "unit_abilities": "ability",
    "agent_subtypes": "character",
    "effects": "effect",
    "building_levels": "building_level",
    "building_chains": "building_chain",
    "technologies": "technology",
    "ancillaries": "item",
    "factions": "faction",
    "cultures": "culture",
    "cultures_subcultures": "subculture",
}
# Junction tables that pair a unit set with one specific thing.
COMBINED_UNIT_SET_TABLES = {
    "unit_set_unit_ability_junctions": "unit_ability",
    "unit_set_unit_attribute_junctions": "unit_attribute",
    "unit_set_special_ability_phase_junctions": "special_ability_phase",
}
EFFECT_COLUMNS = ("effect", "effect_key")
BONUS_COLUMNS = ("bonus_value_id", "bonus_value")


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {"effect": {}, "effect_bundle": {}}
    if ctx.table_exists("effects"):
        for r in ctx.rows("SELECT effect FROM effects"):
            out["effect"][r["effect"]] = ctx.catalog_name("effect", f"effects_description_{r['effect']}")
    if ctx.table_exists("effect_bundles"):
        for r in ctx.rows("SELECT key FROM effect_bundles"):
            out["effect_bundle"][r["key"]] = ctx.catalog_name(
                "effect_bundle", f"effect_bundles_localised_title_{r['key']}")
    return out


def effect_application(ctx: Context, effect_key: str, *, scope: str | None, value: float,
                       source: tuple[str, str], **extra) -> dict:
    app = {
        "effect": ctx.links.link("effect", effect_key, source=source, relation="effect"),
        "scope": opt(scope),
        "value": float(value),
        "source": ctx.links.link(source[0], source[1], source=None, relation="source"),
    }
    app.update(extra)
    return app


def bonus_targets(ctx: Context) -> dict[str, list[dict]]:
    tables = [r["table_name"] for r in ctx.rows(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_name LIKE 'effect_bonus_value%' ORDER BY table_name")]
    combined = {t: {r["key"]: r for r in ctx.rows(f'SELECT * FROM "{t}"')}
                for t in COMBINED_UNIT_SET_TABLES if ctx.table_exists(t)}

    out: dict[str, list[dict]] = defaultdict(list)
    for table in tables:
        cols = {r["column_name"]: r["ref_table"] for r in ctx.rows(
            "SELECT column_name, ref_table FROM _columns WHERE table_name = ?", [table])}
        effect_col = next(c for c in EFFECT_COLUMNS if c in cols)
        bonus_col = next(c for c in BONUS_COLUMNS if c in cols)
        target_cols = [c for c in cols if c not in (effect_col, bonus_col)]
        target_col = target_cols[0] if target_cols else None
        select = f'"{effect_col}" AS effect, "{bonus_col}" AS bonus'
        if target_col:
            select += f', "{target_col}" AS target'
        for r in ctx.rows(f'SELECT {select} FROM "{table}"'):
            out[r["effect"]].append(_bonus_target(
                ctx, table, cols.get(target_col), r.get("target"), r["bonus"], r["effect"], combined))
    for targets in out.values():
        targets.sort(key=lambda t: (t["source_table"], t["bonus_value_id"], t["target_key"] or ""))
    return out


def _bonus_target(ctx: Context, table: str, target_table: str | None, raw_key, bonus: str,
                  effect: str, combined: dict) -> dict:
    key = None if raw_key is None or raw_key == "" else str(raw_key)
    target = {"bonus_value_id": bonus, "source_table": table, "target_table": target_table,
              "target_key": key, "target": None, "unit_set": None, "ability": None,
              "attribute": None, "phase": None}
    source = ("effect", effect)
    entity_type = ENTITY_TYPE_FOR_TABLE.get(target_table)
    if entity_type and key:
        target["target"] = ctx.links.link(entity_type, key, source=source, relation="bonus_target")
    if target_table == "unit_sets":
        target["unit_set"] = key
    elif target_table in combined and key in combined[target_table]:
        row = combined[target_table][key]
        target["unit_set"] = row["unit_set"]
        if target_table == "unit_set_unit_ability_junctions":
            target["ability"] = ctx.links.link("ability", row["unit_ability"], source=source,
                                               relation="bonus_target")
        elif target_table == "unit_set_unit_attribute_junctions":
            target["attribute"] = row["unit_attribute"]
        else:
            target["phase"] = row["special_ability_phase"]
    return target


def build(ctx: Context) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {"effect": [], "effect_bundle": []}

    if ctx.require("effect", "effects"):
        targets = bonus_targets(ctx) if ctx.table_exists("_columns") else {}
        for r in ctx.rows("SELECT * FROM effects ORDER BY effect"):
            key = r["effect"]
            out["effect"].append({
                "key": key,
                "description": ctx.links.name("effect", key),
                "additional_tooltip": ctx.loc.text(
                    f"effects_additional_tooltip_details_localised_description_{key}"),
                "category": r["category"],
                "icon": opt(r["icon"]),
                "icon_negative": opt(r["icon_negative"]),
                "priority": r["priority"],
                "is_positive_value_good": r["is_positive_value_good"],
                "bonus_targets": targets.get(key, []),
                "sources": [],
            })

    if ctx.require("effect_bundle", "effect_bundles", "effect_bundles_to_effects_junctions"):
        apps: dict[str, list[dict]] = defaultdict(list)
        for r in ctx.rows("SELECT * FROM effect_bundles_to_effects_junctions "
                          "ORDER BY effect_bundle_key, effect_key"):
            apps[r["effect_bundle_key"]].append(effect_application(
                ctx, r["effect_key"], scope=r["effect_scope"], value=r["value"],
                source=("effect_bundle", r["effect_bundle_key"]),
                advancement_stage=opt(r["advancement_stage"])))
        for r in ctx.rows("SELECT * FROM effect_bundles ORDER BY key"):
            key = r["key"]
            out["effect_bundle"].append({
                "key": key,
                "title": ctx.links.name("effect_bundle", key),
                "description": ctx.loc.text(f"effect_bundles_localised_description_{key}"),
                "target": r["bundle_target"],
                "priority": r["priority"],
                "icon": opt(r["ui_icon"]),
                "is_global_effect": r["is_global_effect"],
                "effects": apps.get(key, []),
            })
    return out
