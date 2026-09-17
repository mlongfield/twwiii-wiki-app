"""Factions, cultures, subcultures, difficulty handicaps and campaign variables."""

from __future__ import annotations

from collections import defaultdict

from .context import Context, by_key, grouped, opt
from .effects import effect_application


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {
        "faction": {}, "culture": {}, "subculture": {}, "difficulty_level": {}, "campaign_variable": {}}
    if ctx.table_exists("factions"):
        for r in ctx.rows("SELECT key FROM factions"):
            out["faction"][r["key"]] = ctx.catalog_name("faction", f"factions_screen_name_{r['key']}")
    if ctx.table_exists("cultures"):
        for r in ctx.rows("SELECT key FROM cultures"):
            out["culture"][r["key"]] = ctx.catalog_name("culture", f"cultures_name_{r['key']}")
    if ctx.table_exists("cultures_subcultures"):
        for r in ctx.rows("SELECT subculture FROM cultures_subcultures"):
            out["subculture"][r["subculture"]] = ctx.catalog_name(
                "subculture", f"cultures_subcultures_name_{r['subculture']}")
    if ctx.table_exists("campaign_difficulty_handicap_effects"):
        for r in ctx.rows("SELECT DISTINCT campaign_difficulty_handicap AS level FROM campaign_difficulty_handicap_effects"):
            out["difficulty_level"][str(r["level"])] = None  # no display name in data; not counted as missing
    if ctx.table_exists("campaign_variables"):
        for r in ctx.rows("SELECT variable_key FROM campaign_variables"):
            out["campaign_variable"][r["variable_key"]] = r["variable_key"]
    return out


def _campaign_links(ctx: Context, rows: list[dict], source: tuple[str, str], relation: str,
                    flag: str | None = None) -> list[dict]:
    keys = sorted({r["campaign"] for r in rows if flag is None or r[flag]})
    return [ctx.links.link("campaign", k, source=source, relation=relation) for k in keys]


def build(ctx: Context) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {
        "faction": [], "culture": [], "subculture": [], "difficulty_level": [], "campaign_variable": []}
    subcultures = by_key(ctx, "cultures_subcultures", "subculture")

    if ctx.require("faction", "factions"):
        starts = grouped(ctx, "start_pos_factions", "faction", "campaign")
        for r in ctx.rows("SELECT * FROM factions ORDER BY key"):
            key = r["key"]
            source = ("faction", key)
            sub = subcultures.get(r["subculture"])
            out["faction"].append({
                "key": key,
                "name": ctx.links.name("faction", key),
                "adjective": ctx.loc.text(f"factions_screen_adjective_{key}"),
                "subculture": ctx.links.link("subculture", opt(r["subculture"]), source=source, relation="subculture"),
                "culture": ctx.links.link("culture", sub["culture"] if sub else None, source=source, relation="culture"),
                "category": opt(r["category"]),
                "is_rebel": r["is_rebel"],
                "is_quest_faction": r["is_quest_faction"],
                "flags_path": r["flags_path"],
                "flag_image": ctx.images.resolve(
                    "faction.flag_image", f"{r['flags_path']}/mon_64.png" if opt(r["flags_path"]) else None),
                "primary_colour": opt(r["primary_colour_hex"]),
                "start_campaigns": _campaign_links(ctx, starts.get(key, []), source, "start_campaigns"),
                "playable_in": _campaign_links(ctx, starts.get(key, []), source, "playable_in", "playable"),
                "major_in": _campaign_links(ctx, starts.get(key, []), source, "major_in", "is_major"),
                "units": [],
                "characters": [],
            })

    if ctx.require("culture", "cultures"):
        for r in ctx.rows("SELECT key FROM cultures ORDER BY key"):
            out["culture"].append({"key": r["key"], "name": ctx.links.name("culture", r["key"]),
                                   "subcultures": [], "factions": []})

    if ctx.require("subculture", "cultures_subcultures"):
        for key, r in sorted(subcultures.items()):
            out["subculture"].append({
                "key": key,
                "name": ctx.links.name("subculture", key),
                "culture": ctx.links.link("culture", opt(r["culture"]), source=("subculture", key), relation="culture"),
                "factions": [],
            })

    if ctx.require("difficulty_level", "campaign_difficulty_handicap_effects"):
        levels: dict[int, dict[str, list[dict]]] = defaultdict(lambda: {"ai": [], "human": []})
        for r in ctx.rows("SELECT * FROM campaign_difficulty_handicap_effects "
                          "ORDER BY campaign_difficulty_handicap, human, effect, optional_campaign_key"):
            level = r["campaign_difficulty_handicap"]
            levels[level]["human" if r["human"] else "ai"].append({
                "application": effect_application(ctx, r["effect"], scope=r["effect_scope"], value=r["effect_value"],
                                                  source=("difficulty_level", str(level))),
                "campaign": opt(r["optional_campaign_key"]),
            })
        for level in sorted(levels):
            out["difficulty_level"].append({"key": str(level), "level": level, **levels[level]})

    if ctx.require("campaign_variable", "campaign_variables"):
        overrides = grouped(ctx, "campaigns_campaign_variables_junctions", "variable_key",
                            "campaign_name, difficulty, campaign_type, value")
        for r in ctx.rows("SELECT * FROM campaign_variables ORDER BY variable_key"):
            key = r["variable_key"]
            out["campaign_variable"].append({
                "key": key,
                "value": r["value"],
                "overrides": [{"campaign": o["campaign_name"], "difficulty": opt(o["difficulty"]),
                               "campaign_type": opt(o["campaign_type"]), "value": o["value"]}
                              for o in overrides.get(key, [])],
            })
    return out
