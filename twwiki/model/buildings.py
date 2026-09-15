"""Building levels and chains.

Level names live on culture variants, keyed by building + culture + subculture
+ faction concatenated without separators. The generic variant wins.
"""

from __future__ import annotations

from .context import Context, grouped, opt
from .effects import effect_application
from .technologies import load_resource_costs


def _variant_order(v: dict) -> tuple:
    specific = bool(opt(v["culture"]) or opt(v["subculture"]) or opt(v["faction"]))
    return (specific, v["culture"] or "", v["subculture"] or "", v["faction"] or "")


def level_name(ctx: Context, level_key: str, variants: list[dict]) -> str | None:
    for v in sorted(variants, key=_variant_order):
        text = ctx.loc.text("building_culture_variants_name_" + level_key
                            + (v["culture"] or "") + (v["subculture"] or "") + (v["faction"] or ""))
        if text:
            return text
    return None


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {"building_level": {}, "building_chain": {}}
    variants = grouped(ctx, "building_culture_variants", "building", "building")
    if ctx.table_exists("building_levels"):
        for r in ctx.rows("SELECT level_name FROM building_levels"):
            key = r["level_name"]
            name = level_name(ctx, key, variants.get(key, []))
            if name is None:
                ctx.missing_names["building_level"] += 1
            out["building_level"][key] = name
    if ctx.table_exists("building_chains"):
        for r in ctx.rows("SELECT key FROM building_chains"):
            name = ctx.loc.text(f"building_chains_encyclopedia_name_{r['key']}") \
                or ctx.loc.text(f"building_chains_chain_tooltip_{r['key']}")
            if name is None:
                ctx.missing_names["building_chain"] += 1
            out["building_chain"][r["key"]] = name
    return out


def build(ctx: Context) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {"building_level": [], "building_chain": []}
    if not ctx.require("building_level", "building_levels"):
        ctx.require("building_chain", "building_chains")
        return out
    variants = grouped(ctx, "building_culture_variants", "building", "building")
    effect_rows = grouped(ctx, "building_effects_junction", "building", "effect, context_requirement")
    recruits = grouped(ctx, "building_units_allowed", "building", "unit")
    costs = load_resource_costs(ctx)
    levels = ctx.rows("SELECT * FROM building_levels ORDER BY chain, level, level_name")

    for r in sorted(levels, key=lambda l: l["level_name"]):
        key = r["level_name"]
        source = ("building_level", key)
        own_variants = sorted(variants.get(key, []), key=_variant_order)
        short = next((ctx.loc.text(f"building_short_description_texts_short_description_{v['short_description']}")
                      for v in own_variants if opt(v["short_description"])), None)
        out["building_level"].append({
            "key": key,
            "name": ctx.links.name("building_level", key),
            "short_description": short,
            "chain": ctx.links.link("building_chain", r["chain"], source=source, relation="chain"),
            "level": r["level"],
            "create_time": r["create_time"],
            "create_cost": r["create_cost"],
            "upkeep_cost": r["upkeep_cost"],
            "development_point_cost": r["development_point_cost"],
            "food_cost": r["food_cost"],
            "only_in_capital": r["only_in_capital"],
            "faction_unique": r["faction_unique"],
            "can_convert": r["can_convert"],
            "visible_in_ui": r["visible_in_ui"],
            "resource_cost": costs.get(opt(r["resource_cost"])),
            "cultures": sorted({v["culture"] for v in own_variants if opt(v["culture"])}),
            "effects": [effect_application(
                ctx, e["effect"], scope=e["effect_scope"], value=e["value"], source=source,
                value_damaged=e["value_damaged"], value_ruined=e["value_ruined"],
                context_requirement=opt(e["context_requirement"]))
                for e in effect_rows.get(key, [])],
            "units_recruited": [ctx.links.link("unit", u, source=source, relation="units_recruited")
                                for u in sorted({row["unit"] for row in recruits.get(key, [])})],
        })

    if ctx.require("building_chain", "building_chains"):
        chain_levels = grouped(ctx, "building_levels", "chain", "level, level_name")
        for r in ctx.rows("SELECT * FROM building_chains ORDER BY key"):
            key = r["key"]
            out["building_chain"].append({
                "key": key,
                "name": ctx.links.name("building_chain", key),
                "category": opt(r["chain_category"]),
                "in_encyclopedia": r["in_encyclopedia"],
                "levels": [ctx.links.link("building_level", l["level_name"], source=("building_chain", key),
                                          relation="levels") for l in chain_levels.get(key, [])],
            })
    return out
