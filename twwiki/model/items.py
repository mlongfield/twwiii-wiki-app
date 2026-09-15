"""Items (ancillaries) and character traits."""

from __future__ import annotations

from .context import Context, by_key, grouped, opt
from .effects import effect_application


def _trait_levels(ctx: Context) -> dict[str, list[dict]]:
    return grouped(ctx, "character_trait_levels", "trait", "level, key")


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {"item": {}, "trait": {}}
    if ctx.table_exists("ancillaries"):
        for r in ctx.rows("SELECT key FROM ancillaries"):
            out["item"][r["key"]] = ctx.catalog_name("item", f"ancillaries_onscreen_name_{r['key']}")
    if ctx.table_exists("character_traits"):
        levels = _trait_levels(ctx)
        for r in ctx.rows("SELECT key FROM character_traits"):
            key = r["key"]
            own = [l for l in levels.get(key, []) if l["key"] == key]
            chosen = own[0] if own else (levels.get(key) or [None])[0]
            name = ctx.loc.text(f"character_trait_levels_onscreen_name_{chosen['key']}") if chosen else None
            if name is None:
                ctx.missing_names["trait"] += 1
            out["trait"][key] = name
    return out


def build(ctx: Context) -> dict[str, list[dict]]:
    return {"item": _items(ctx), "trait": _traits(ctx)}


def _items(ctx: Context) -> list[dict]:
    if not ctx.require("item", "ancillaries"):
        return []
    effect_rows = grouped(ctx, "ancillary_to_effects", "ancillary", "effect")
    agents = grouped(ctx, "ancillary_to_included_agents", "ancillary", "agent")
    subtypes = grouped(ctx, "ancillaries_included_agent_subtypes", "ancillary", "agent_subtype")
    required = grouped(ctx, "ancillaries_required_skills", "ancillary", "required_skill")
    types = by_key(ctx, "ancillary_types", "type")

    out = []
    for r in ctx.rows("SELECT * FROM ancillaries ORDER BY key"):
        key = r["key"]
        source = ("item", key)
        out.append({
            "key": key,
            "name": ctx.links.name("item", key),
            "description": ctx.loc.text(f"ancillaries_colour_text_{key}"),
            "explanation": ctx.loc.text(f"ancillaries_explanation_text_{key}"),
            "icon_image": ctx.images.resolve(
                "item.icon_image", types[r["type"]]["ui_icon"] if r["type"] in types else None),
            "type": r["type"],
            "category": r["category"],
            "subcategory": opt(r["subcategory"]),
            "legendary": r["legendary_item"],
            "applies_to": r["applies_to"],
            "transferrable": r["transferrable"],
            "unique_to_world": r["unique_to_world"],
            "unique_to_faction": r["unique_to_faction"],
            "bodyguard_unit": ctx.links.link("unit", opt(r["provided_bodyguard_unit"]), source=source, relation="bodyguard"),
            "agent_types": sorted({a["agent"] for a in agents.get(key, [])}),
            "agent_subtypes": [ctx.links.link("character", s["agent_subtype"], source=source, relation="agent_subtypes")
                               for s in subtypes.get(key, [])],
            "required_skills": [{"skill": ctx.links.link("skill", s["required_skill"], source=source, relation="required_skills"),
                                 "level": s["required_skill_level"]} for s in required.get(key, [])],
            "effects": [effect_application(ctx, e["effect"], scope=e["effect_scope"], value=e["value"], source=source)
                        for e in effect_rows.get(key, [])],
        })
    return out


def _traits(ctx: Context) -> list[dict]:
    if not ctx.require("trait", "character_traits"):
        return []
    levels = _trait_levels(ctx)
    effect_rows = grouped(ctx, "trait_level_effects", "trait_level", "effect")
    antitraits = grouped(ctx, "trait_to_antitraits", "trait", "antitrait")
    categories = by_key(ctx, "trait_categories", "category")

    out = []
    for r in ctx.rows("SELECT * FROM character_traits ORDER BY key"):
        key = r["key"]
        source = ("trait", key)
        out.append({
            "key": key,
            "name": ctx.links.name("trait", key),
            "hidden": r["hidden"],
            "precedence": r["precedence"],
            "icon": r["icon"],
            "icon_image": ctx.images.resolve(
                "trait.icon_image", categories[r["icon"]]["icon_path"] if r["icon"] in categories else None),
            "no_going_back_level": r["no_going_back_level"],
            "levels": [{
                "key": l["key"],
                "level": l["level"],
                "name": ctx.loc.text(f"character_trait_levels_onscreen_name_{l['key']}"),
                "description": ctx.loc.text(f"character_trait_levels_colour_text_{l['key']}"),
                "threshold_points": l["threshold_points"],
                "effects": [effect_application(ctx, e["effect"], scope=e["effect_scope"], value=e["value"], source=source)
                            for e in effect_rows.get(l["key"], [])],
            } for l in levels.get(key, [])],
            "antitraits": [ctx.links.link("trait", a["antitrait"], source=source, relation="antitraits")
                           for a in antitraits.get(key, [])],
        })
    return out
