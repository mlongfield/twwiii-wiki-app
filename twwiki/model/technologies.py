"""Technologies and research trees.

Research cost lives on the tree node, not the technology: one technology can
sit in several trees at different costs, so each technology lists placements.
"""

from __future__ import annotations

from collections import defaultdict

from .context import Context, by_key, grouped, opt
from .effects import effect_application
from .images import TECHNOLOGY_ICONS


def load_resource_costs(ctx: Context) -> dict[str, dict]:
    costs = {
        key: {"key": key, "treasury_cost": row["treasury_cost"], "pooled_resources": [], "trade_resources": []}
        for key, row in by_key(ctx, "resource_costs", "id").items()
    }
    for key, rows in grouped(ctx, "resource_cost_pooled_resource_junctions", "resource_cost",
                             "resource_cost, pooled_resource_factor").items():
        if key in costs:
            costs[key]["pooled_resources"] = [
                {"pooled_resource_factor": r["pooled_resource_factor"], "amount": r["amount"], "context": r["context"]}
                for r in rows]
    for key, rows in grouped(ctx, "resource_cost_trade_resource_junctions", "resource_cost",
                             "resource_cost, trade_resource").items():
        if key in costs:
            costs[key]["trade_resources"] = [r["trade_resource"] for r in rows]
    return costs


def derived_tree_name(ctx: Context, tree: dict) -> str | None:
    """'<faction or culture name> Technologies' for a tree the game leaves unnamed."""
    owner = ctx.loc.text(f"factions_screen_name_{tree['faction_key']}") if opt(tree["faction_key"]) else None
    if owner is None and opt(tree["culture"]):
        owner = ctx.loc.text(f"cultures_name_{tree['culture']}")
    return f"{owner} Technologies" if owner else None


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {"technology": {}, "technology_tree": {}}
    if ctx.table_exists("technologies"):
        for r in ctx.rows("SELECT key FROM technologies"):
            out["technology"][r["key"]] = ctx.catalog_name("technology", f"technologies_onscreen_name_{r['key']}")
    if ctx.table_exists("technology_node_sets"):
        for r in ctx.rows("SELECT key, culture, faction_key FROM technology_node_sets"):
            name = ctx.loc.text(f"technology_node_sets_localised_name_{r['key']}") or derived_tree_name(ctx, r)
            if name is None:
                ctx.missing_names["technology_tree"] += 1
            out["technology_tree"][r["key"]] = name
    return out


def build(ctx: Context) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {"technology": [], "technology_tree": []}
    costs = load_resource_costs(ctx)
    nodes = ctx.rows("SELECT * FROM technology_nodes ORDER BY technology_node_set, key") \
        if ctx.table_exists("technology_nodes") else []

    def node_campaigns(n: dict, source: tuple[str, str]) -> list[dict]:
        key = opt(n["campaign_key"])
        return [ctx.links.link("campaign", key, source=source, relation="campaigns")] if key else []

    if ctx.require("technology", "technologies"):
        placements: dict[str, list[dict]] = defaultdict(list)
        for n in nodes:
            placements[n["technology_key"]].append({
                "tree": ctx.links.link("technology_tree", n["technology_node_set"],
                                       source=("technology", n["technology_key"]), relation="placements"),
                "node_key": n["key"],
                "tier": n["tier"],
                "indent": n["indent"],
                "research_points_required": n["research_points_required"],
                "cost_per_round": n["cost_per_round"],
                "resource_cost": costs.get(opt(n["resource_cost"])),
                "campaigns": node_campaigns(n, ("technology", n["technology_key"])),
            })
        required_techs = grouped(ctx, "technology_required_technology_junctions", "technology", "required_technology")
        required_buildings = grouped(ctx, "technology_required_building_levels_junctions", "technology",
                                     "required_building_level")
        effect_rows = grouped(ctx, "technology_effects_junction", "technology", "effect")
        for r in ctx.rows("SELECT * FROM technologies ORDER BY key"):
            key = r["key"]
            source = ("technology", key)
            out["technology"].append({
                "key": key,
                "name": ctx.links.name("technology", key),
                "description": ctx.loc.text(f"technologies_short_description_{key}"),
                "long_description": ctx.loc.text(f"technologies_long_description_{key}"),
                "icon": r["icon_name"],
                "icon_image": ctx.images.resolve("technology.icon_image", r["icon_name"], TECHNOLOGY_ICONS),
                "is_civil": r["is_civil"],
                "is_engineering": r["is_engineering"],
                "is_military": r["is_military"],
                "is_hidden": r["is_hidden"],
                "unlocked_by_building": ctx.links.link("building_level", opt(r["building_level"]),
                                                       source=source, relation="unlocked_by_building"),
                "required_technologies": [
                    ctx.links.link("technology", j["required_technology"], source=source, relation="required_technologies")
                    for j in required_techs.get(key, [])],
                "required_buildings": [
                    ctx.links.link("building_level", j["required_building_level"], source=source, relation="required_buildings")
                    for j in required_buildings.get(key, [])],
                "effects": [effect_application(ctx, e["effect"], scope=e["effect_scope"], value=e["value"], source=source)
                            for e in effect_rows.get(key, [])],
                "placements": placements.get(key, []),
            })

    if ctx.require("technology_tree", "technology_node_sets", "technology_nodes"):
        tree_nodes: dict[str, list[dict]] = defaultdict(list)
        node_tree = {}
        for n in nodes:
            node_tree[n["key"]] = n["technology_node_set"]
            tree_nodes[n["technology_node_set"]].append({
                "key": n["key"],
                "technology": ctx.links.link("technology", n["technology_key"],
                                             source=("technology_tree", n["technology_node_set"]), relation="tree_nodes"),
                "tier": n["tier"],
                "indent": n["indent"],
                "research_points_required": n["research_points_required"],
                "cost_per_round": n["cost_per_round"],
                "resource_cost": costs.get(opt(n["resource_cost"])),
                "required_parents": n["required_parents"],
                "ui_group": opt(n["optional_ui_group"]),
                "pixel_offset_x": n["pixel_offset_x"],
                "pixel_offset_y": n["pixel_offset_y"],
                "campaigns": node_campaigns(n, ("technology_tree", n["technology_node_set"])),
            })
        tree_links: dict[str, list[dict]] = defaultdict(list)
        if ctx.table_exists("technology_node_links"):
            for l in ctx.rows("SELECT * FROM technology_node_links ORDER BY parent_key, child_key"):
                tree = node_tree.get(l["parent_key"])
                if tree:
                    tree_links[tree].append({"parent": l["parent_key"], "child": l["child_key"],
                                             "initial_descent_tiers": l["initial_descent_tiers"],
                                             "visible_in_ui": l["visible_in_ui"]})
        for r in ctx.rows("SELECT * FROM technology_node_sets ORDER BY key"):
            key = r["key"]
            source = ("technology_tree", key)
            out["technology_tree"].append({
                "key": key,
                "name": ctx.links.name("technology_tree", key),
                "name_derived": ctx.loc.text(f"technology_node_sets_localised_name_{key}") is None
                                and ctx.links.name("technology_tree", key) is not None,
                "culture": ctx.links.link("culture", opt(r["culture"]), source=source, relation="culture"),
                "subculture": ctx.links.link("subculture", opt(r["subculture"]), source=source, relation="subculture"),
                "faction": ctx.links.link("faction", opt(r["faction_key"]), source=source, relation="faction"),
                "campaign": ctx.links.link("campaign", opt(r["campaign_key"]), source=source, relation="campaign"),
                "colour": opt(r["colour_hex"]),
                "nodes": tree_nodes.get(key, []),
                "links": tree_links.get(key, []),
            })
    return out
