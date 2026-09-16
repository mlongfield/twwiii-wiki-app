"""Campaign regions and provinces, from the start-position tables.

Which slot template (and so which resource and buildings) an ordinary
settlement gets is stored only in startpos.esf. Special settlements have slot
templates named after the region, and those are matched here. Every other
settlement is "generic": the web app shows the chains its culture can build.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

from .context import Context, by_key, grouped, opt

SPECIAL = "_special_"
ROLE = re.compile(r"_(primary|secondary|port)(?=_|$)")
ROLE_ORDER = {"primary": 0, "secondary": 1, "port": 2}


def region_stem(region_key: str) -> str | None:
    """wh3_main_combi_region_altdorf -> altdorf."""
    if "_region_" not in region_key:
        return None
    return region_key.split("_region_", 1)[1] or None


def index_special_templates(template_keys: Iterable[str]) -> dict[str, list[dict]]:
    """Map every stem a template key can be read as to that reading.

    A key matches stem S when it ends with _special_S_<role> optionally
    followed by _<variant>; S itself may contain underscores, so every
    _special_ and role occurrence is considered.
    """
    out: dict[str, list[dict]] = defaultdict(list)
    for key in sorted(template_keys):
        start = key.find(SPECIAL)
        while start != -1:
            rest = key[start + len(SPECIAL):]
            for m in ROLE.finditer(rest):
                stem = rest[:m.start()]
                if stem:
                    out[stem].append({"key": key, "role": m.group(1), "variant": rest[m.end() + 1:] or None})
            start = key.find(SPECIAL, start + 1)
    return out


class ChainSets:
    """Resolve building chain sets (parent sets, superchains, removals) to chain keys."""

    def __init__(self, ctx: Context):
        self.superchains: dict[str, set[str]] = defaultdict(set)
        if ctx.table_exists("building_chains"):
            for r in ctx.rows("SELECT key, building_superchain FROM building_chains"):
                if opt(r["building_superchain"]):
                    self.superchains[r["building_superchain"]].add(r["key"])
        self.parents = {k: opt(r["parent_set"]) for k, r in by_key(ctx, "building_chain_sets", "key").items()}
        self.items = grouped(ctx, "building_chain_set_items", "set", "chain, super_chain")

    def chains_of_set(self, set_key: str, seen: frozenset = frozenset()) -> set[str]:
        if set_key in seen:
            return set()
        seen = seen | {set_key}
        parent = self.parents.get(set_key)
        added = self.chains_of_set(parent, seen) if parent else set()
        return self._apply(self.items.get(set_key, []), seen, added)

    def permitted(self, rows: list[dict]) -> list[str]:
        """Chains a slot template allows, from its permitted-chain rows."""
        return sorted(self._apply(rows, frozenset(), set()))

    def _apply(self, rows: list[dict], seen: frozenset, added: set[str]) -> set[str]:
        removed: set[str] = set()
        for row in rows:
            (removed if row["remove"] else added).update(self._row_chains(row, seen))
        return added - removed

    def _row_chains(self, row: dict, seen: frozenset) -> set[str]:
        chains: set[str] = set()
        if opt(row.get("chain")):
            chains.add(row["chain"])
        if opt(row.get("super_chain")):
            chains |= self.superchains.get(row["super_chain"], set())
        if opt(row.get("chain_set")):
            chains |= self.chains_of_set(row["chain_set"], seen)
        return chains


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {"region": {}, "province": {}}
    if ctx.table_exists("regions"):
        for r in ctx.rows("SELECT key FROM regions"):
            out["region"][r["key"]] = ctx.catalog_name("region", f"regions_onscreen_{r['key']}")
    if ctx.table_exists("provinces"):
        for r in ctx.rows("SELECT key FROM provinces"):
            out["province"][r["key"]] = ctx.catalog_name("province", f"provinces_onscreen_{r['key']}")
    return out


def build(ctx: Context) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {"region": [], "province": []}
    start = by_key(ctx, "start_pos_regions", "region")
    ctx.manifest_sections["regions"] = {"special_templates_unmatched": 0}
    if ctx.require("region", "regions"):
        out["region"] = _regions(ctx, start)
    if ctx.require("province", "provinces"):
        out["province"] = _provinces(ctx, start)
    return out


def _regions(ctx: Context, start: dict[str, dict]) -> list[dict]:
    faction_by_id = {k: r["faction"] for k, r in by_key(ctx, "start_pos_factions", "ID").items()}
    junctions = by_key(ctx, "region_to_province_junctions", "region")
    groups = grouped(ctx, "regions_to_region_groups_junctions", "region", '"order", region_group')
    templates = by_key(ctx, "slot_templates", "key")
    resources = by_key(ctx, "resources", "key")
    permitted_rows = grouped(ctx, "slot_template_permitted_building_chains", "slot_template",
                             "chain, chain_set, super_chain")
    special = index_special_templates(k for k in templates if SPECIAL in k)
    chain_sets = ChainSets(ctx)
    chains_for: dict[str, list[str]] = {}
    matched: set[str] = set()

    out = []
    for r in ctx.rows("SELECT key FROM regions ORDER BY key"):
        key = r["key"]
        source = ("region", key)
        s = start.get(key)
        j = junctions.get(key)
        stem = region_stem(key)
        matches = sorted(special.get(stem, []) if stem else [], key=lambda m: (ROLE_ORDER[m["role"]], m["key"]))
        slot_templates = []
        for m in matches:
            matched.add(m["key"])
            if m["key"] not in chains_for:
                chains_for[m["key"]] = chain_sets.permitted(permitted_rows.get(m["key"], []))
            slot_templates.append({
                "key": m["key"],
                "role": m["role"],
                "variant": m["variant"],
                "resource": _resource(ctx, opt(templates[m["key"]]["resource"]), resources),
                "permitted_chains": [ctx.links.link("building_chain", c, source=source, relation="permitted_chains")
                                     for c in chains_for[m["key"]]],
            })
        if s is not None and j is None:
            ctx.links.missing["region.province->province"] += 1
        out.append({
            "key": key,
            "name": ctx.links.name("region", key),
            "campaign": s["campaign"] if s else None,
            "is_settlement": s is not None,
            "province": ctx.links.link("province", j["province"], source=source, relation="province") if j else None,
            "is_province_capital": bool(j and j["is_capital"]),
            "starting_owner": _owner(ctx, s, faction_by_id, source),
            "is_faction_capital": bool(s and s["faction_capital"]),
            "slot_cap": s["slot_cap"] if s else None,
            "cultural_originator": ctx.links.link("subculture", opt(s["cultural_originator"]), source=source,
                                                  relation="cultural_originator") if s else None,
            "region_groups": [g["region_group"] for g in groups.get(key, [])],
            "template_source": "special" if slot_templates else "generic",
            "slot_templates": slot_templates,
        })
    ctx.manifest_sections["regions"] = {
        "special_templates_unmatched": sum(1 for k in templates if SPECIAL in k and k not in matched)}
    return out


def _owner(ctx: Context, s: dict | None, faction_by_id: dict[str, str], source: tuple[str, str]) -> dict | None:
    owner_id = opt(s["owning_faction"]) if s else None
    if owner_id is None:
        return None
    faction = faction_by_id.get(owner_id)
    if faction is None:
        ctx.links.missing["region.starting_owner->faction"] += 1
        return None
    return ctx.links.link("faction", faction, source=source, relation="starting_owner")


def _resource(ctx: Context, key: str | None, resources: dict[str, dict]) -> dict | None:
    if key is None:
        return None
    row = resources.get(key)
    if row is None:
        ctx.links.missing["region.slot_template_resource->resources"] += 1
    return {
        "key": key,
        "name": ctx.loc.text(f"resources_onscreen_text_{key}"),
        "icon_image": ctx.images.resolve("region.resource.icon_image", row["icon_filepath"] if row else None),
    }


def _provinces(ctx: Context, start: dict[str, dict]) -> list[dict]:
    members = grouped(ctx, "region_to_province_junctions", "province", "region")
    out = []
    for r in ctx.rows("SELECT key FROM provinces ORDER BY key"):
        key = r["key"]
        source = ("province", key)
        rows = members.get(key, [])
        capital = next((j["region"] for j in rows if j["is_capital"]), None)
        out.append({
            "key": key,
            "name": ctx.links.name("province", key),
            "campaign": next((start[j["region"]]["campaign"] for j in rows if j["region"] in start), None),
            "regions": [ctx.links.link("region", j["region"], source=source, relation="regions") for j in rows],
            "capital": ctx.links.link("region", capital, source=source, relation="capital"),
        })
    return out
