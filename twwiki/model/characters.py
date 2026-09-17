"""Characters (agent subtypes), their skill trees, and skills."""

from __future__ import annotations

from collections import Counter, defaultdict

from .context import Context, by_key, grouped, opt
from .effects import effect_application
from .images import SKILL_ICONS


def _land_units(ctx: Context) -> dict[str, str | None]:
    """Load unit -> land_unit mapping, or empty dict if table missing."""
    return {r["unit"]: opt(r["land_unit"]) for r in ctx.rows("SELECT unit, land_unit FROM main_units")} \
        if ctx.table_exists("main_units") else {}


def agent_type_labels(ctx: Context) -> dict[str, dict[str, str]]:
    """agent -> culture -> onscreen name, from agent_culture_details rows that have text."""
    labels: dict[str, dict[str, str]] = defaultdict(dict)
    if ctx.table_exists("agent_culture_details"):
        for r in ctx.rows("SELECT agent, culture, key FROM agent_culture_details ORDER BY agent, culture, level, key"):
            name = ctx.loc.text(f"agent_culture_details_onscreen_name_{r['key']}")
            if name and r["culture"] not in labels[r["agent"]]:
                labels[r["agent"]][r["culture"]] = name
    return labels


def agent_type(ctx: Context, labels: dict[str, dict[str, str]], agent: str, culture: str | None) -> dict:
    """The culture's own name for an agent type, else the name most cultures use
    (ties go to the earliest culture key). A type with no name at all is counted."""
    names = labels.get(agent, {})
    name = names.get(culture) if culture else None
    if name is None and names:
        counts = Counter(names.values())
        first_culture: dict[str, str] = {}
        for c in sorted(names):
            first_culture.setdefault(names[c], c)
        name = min(counts, key=lambda n: (-counts[n], first_culture[n]))
    if name is None:
        ctx.tally["unresolved_agent_type_names"] += 1
    return {"key": agent, "name": name}


def faction_cultures(ctx: Context) -> dict[str, str]:
    """faction key -> culture key, through the faction's subculture."""
    subcultures = by_key(ctx, "cultures_subcultures", "subculture")
    out = {}
    for key, faction in by_key(ctx, "factions", "key").items():
        sub = subcultures.get(faction["subculture"])
        if sub and opt(sub["culture"]):
            out[key] = sub["culture"]
    return out


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {"character": {}, "skill": {}}
    if ctx.table_exists("agent_subtypes"):
        land_unit = _land_units(ctx)
        for r in ctx.rows("SELECT key, associated_unit_override FROM agent_subtypes"):
            lu = land_unit.get(r["associated_unit_override"])
            name = (ctx.loc.text(f"land_units_onscreen_name_{lu}") if lu else None) \
                or ctx.loc.text(f"agent_subtypes_onscreen_name_override_{r['key']}")
            if name is None:
                ctx.missing_names["character"] += 1
            out["character"][r["key"]] = name
    if ctx.table_exists("character_skills"):
        for r in ctx.rows("SELECT key FROM character_skills"):
            out["skill"][r["key"]] = ctx.catalog_name("skill", f"character_skills_localised_name_{r['key']}")
    return out


def build(ctx: Context) -> dict[str, list[dict]]:
    return {"character": _characters(ctx), "skill": _skills(ctx)}


def _characters(ctx: Context) -> list[dict]:
    if not ctx.require("character", "agent_subtypes"):
        return []
    land_unit = _land_units(ctx)
    unit_abilities = grouped(ctx, "land_units_to_unit_abilites_junctions", "land_unit", "ability")
    permitted = grouped(ctx, "faction_agent_permitted_subtypes", "subtype", "faction, agent")
    trees = _skill_trees(ctx)
    labels = agent_type_labels(ctx)
    cultures = faction_cultures(ctx)
    # campaign_to_agent_subtypes lists every campaign a subtype appears in (Karl Franz has
    # rows for both Immortal Empires and The Realm of Chaos). No rows means no data; the
    # web app treats an empty list as every campaign.
    campaign_rows = grouped(ctx, "campaign_to_agent_subtypes", "agent_subtype", "campaign_type")

    out = []
    for r in ctx.rows("SELECT * FROM agent_subtypes ORDER BY key"):
        key = r["key"]
        source = ("character", key)
        lore = opt(r["magic_lore"])
        lu = land_unit.get(r["associated_unit_override"])
        rows = permitted.get(key, [])
        faction_keys = sorted({p["faction"] for p in rows})
        culture = cultures.get(faction_keys[0]) if faction_keys else None
        out.append({
            "key": key,
            "name": ctx.links.name("character", key),
            "title": ctx.loc.text(f"agent_subtypes_onscreen_name_override_{key}"),
            "description": ctx.loc.text(f"agent_subtypes_description_text_override_{key}"),
            "agent_types": [agent_type(ctx, labels, a, culture) for a in sorted({p["agent"] for p in rows})],
            "associated_unit": ctx.links.link("unit", opt(r["associated_unit_override"]), source=source,
                                              relation="associated_unit"),
            "lore_of_magic": {"key": lore, "name": ctx.loc.text(f"special_ability_groups_name_{lore}")} if lore else None,
            "is_caster": r["is_caster"],
            "can_equip_ancillaries": r["can_equip_ancillaries"],
            "recruitable": r["recruitable"],
            "can_gain_xp": r["can_gain_xp"],
            "cost": r["cost"],
            "cap": r["cap"],
            "factions": [ctx.links.link("faction", f, source=source, relation="factions")
                         for f in faction_keys],
            "campaigns": [ctx.links.link("campaign", c, source=source, relation="campaigns")
                          for c in sorted({row["campaign_type"] for row in campaign_rows.get(key, [])})],
            "abilities": [ctx.links.link("ability", a["ability"], source=source, relation="abilities")
                          for a in (unit_abilities.get(lu, []) if lu else [])],
            "skill_trees": [_tree(ctx, key, t) for t in trees.get(key, [])],
            "items": [],
        })
    return out


def _skill_trees(ctx: Context) -> dict[str, list[dict]]:
    """character key -> raw tree dicts with their node, link and lock rows."""
    if not ctx.table_exists("character_skill_node_sets"):
        return {}
    items = grouped(ctx, "character_skill_node_set_items", "set", "item")
    nodes = by_key(ctx, "character_skill_nodes", "key")
    links = grouped(ctx, "character_skill_node_links", "parent_key", "child_key")
    locks = grouped(ctx, "character_skill_nodes_skill_locks", "character_skill_node", "character_skill, level")

    by_character: dict[str, list[dict]] = defaultdict(list)
    for s in ctx.rows("SELECT * FROM character_skill_node_sets ORDER BY key"):
        subtype = opt(s["agent_subtype_key"])
        if not subtype:
            ctx.links.missing["skill_tree.no_agent_subtype"] += 1
            continue
        set_items = items.get(s["key"], [])
        for i in set_items:
            if i["item"] not in nodes:
                ctx.links.missing["skill_tree.missing_node"] += 1
        node_rows = sorted((nodes[i["item"]] for i in set_items if i["item"] in nodes),
                           key=lambda n: (n["indent"], n["tier"], n["key"]))
        node_keys = {n["key"] for n in node_rows}
        tree_links = []
        for k in sorted(node_keys):
            for l in links.get(k, []):
                if l["child_key"] in node_keys:
                    tree_links.append(l)
                else:
                    ctx.links.missing["skill_tree.link_outside_tree"] += 1
        by_character[subtype].append({
            "set": s,
            "nodes": node_rows,
            "links": tree_links,
            "locks": [l for k in sorted(node_keys) for l in locks.get(k, [])],
        })
    return by_character


def _tree(ctx: Context, character: str, tree: dict) -> dict:
    source = ("character", character)
    s = tree["set"]
    return {
        "key": s["key"],
        "agent_type": opt(s["agent_key"]),
        "faction": opt(s["faction_key"]),
        "subculture": opt(s["subculture"]),
        "campaign": ctx.links.link("campaign", opt(s["campaign_key"]), source=source, relation="skill_tree_campaign"),
        "for_army": s["for_army"],
        "for_navy": s["for_navy"],
        "nodes": [{
            "key": n["key"],
            "skill": ctx.links.link("skill", n["character_skill_key"], source=source, relation="skill_tree"),
            "tier": n["tier"],
            "indent": n["indent"],
            "points_on_creation": n["points_on_creation"],
            "required_num_parents": n["required_num_parents"],
            "visible_in_ui": n["visible_in_ui"],
            "faction": opt(n["faction_key"]),
            "subculture": opt(n["subculture"]),
            "campaign": ctx.links.link("campaign", opt(n["campaign_key"]), source=source, relation="skill_tree_campaign"),
        } for n in tree["nodes"]],
        "links": [{"parent": l["parent_key"], "child": l["child_key"], "link_type": l["link_type"],
                   "initial_descent_tiers": l["initial_descent_tiers"]} for l in tree["links"]],
        "locks": [{"node": l["character_skill_node"],
                   "skill": ctx.links.link("skill", l["character_skill"], source=source, relation="skill_lock"),
                   "level": l["level"]} for l in tree["locks"]],
    }


def _skills(ctx: Context) -> list[dict]:
    if not ctx.require("skill", "character_skills"):
        return []
    effect_rows = grouped(ctx, "character_skill_level_to_effects_junctions", "character_skill_key", "level, effect_key")
    # Unlock rank per skill level, from the variant that applies everywhere.
    ranks: dict[str, dict[int, int]] = defaultdict(dict)
    if ctx.table_exists("character_skill_level_details"):
        for d in ctx.rows("""SELECT skill_key, level, unlocked_at_rank FROM character_skill_level_details
                             WHERE faction_key = '' AND subculture_key = '' AND campaign_key = ''"""):
            ranks[d["skill_key"]][d["level"]] = d["unlocked_at_rank"]

    out = []
    for r in ctx.rows("SELECT * FROM character_skills ORDER BY key"):
        key = r["key"]
        skill_ranks = ranks.get(key, {})
        levels: dict[int, list[dict]] = defaultdict(list)
        for e in effect_rows.get(key, []):
            levels[e["level"]].append(effect_application(
                ctx, e["effect_key"], scope=e["effect_scope"], value=e["value"], source=("skill", key)))
        for level in skill_ranks:
            levels.setdefault(level, [])
        out.append({
            "key": key,
            "name": ctx.links.name("skill", key),
            "description": ctx.loc.text(f"character_skills_localised_description_{key}"),
            "image": r["image_path"],
            "icon_image": ctx.images.resolve("skill.icon_image", r["image_path"], SKILL_ICONS),
            "unlocked_at_rank": r["unlocked_at_rank"],
            "is_background_skill": r["is_background_skill"],
            "levels": [{"level": lvl, "unlocked_at_rank": skill_ranks.get(lvl), "effects": levels[lvl]}
                       for lvl in sorted(levels)],
            "characters": [],
        })
    return out
