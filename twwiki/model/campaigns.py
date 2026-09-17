"""Campaigns (Immortal Empires, The Realm of Chaos, ...) and which factions start in each."""

from __future__ import annotations

from .context import Context, grouped, opt


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {"campaign": {}}
    if ctx.table_exists("campaigns"):
        for r in ctx.rows("SELECT campaign_name FROM campaigns"):
            key = r["campaign_name"]
            out["campaign"][key] = ctx.catalog_name("campaign", f"campaigns_onscreen_name_{key}")
    return out


def build(ctx: Context) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {"campaign": []}
    if not ctx.require("campaign", "campaigns"):
        return out
    starts = grouped(ctx, "start_pos_factions", "campaign", "faction")
    for r in ctx.rows("SELECT * FROM campaigns ORDER BY campaign_name"):
        key = r["campaign_name"]
        source = ("campaign", key)
        rows = starts.get(key, [])

        def factions(relation: str, flag: str | None = None) -> list[dict]:
            keys = sorted({s["faction"] for s in rows if flag is None or s[flag]})
            return [ctx.links.link("faction", f, source=source, relation=relation) for f in keys]

        out["campaign"].append({
            "key": key,
            "name": ctx.links.name("campaign", key),
            "map": opt(r["map_name"]),
            "script_folder": opt(r["script_path"]),
            "factions": factions("factions"),
            "playable_factions": factions("playable_factions", "playable"),
            "major_factions": factions("major_factions", "is_major"),
            "regions": [],
        })
    return out
