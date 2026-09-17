"""Units: base stats as components, weapons, and what the unit connects to.

Stats are not combined here (no total HP, no buffs); the stat engine does that.
"""

from __future__ import annotations

from collections import defaultdict

from .context import Context, by_key, opt
from .images import UNIT_CARDS
from .text import split_title_body
from .unit_sets import resolve_unit_sets

LAND_STAT_FIELDS = (
    "bonus_hit_points", "melee_attack", "melee_defence", "charge_bonus", "morale", "accuracy",
    "reload", "primary_ammo", "secondary_ammo", "damage_mod_physical", "damage_mod_magic",
    "damage_mod_flame", "damage_mod_missile", "damage_mod_all", "healing_power", "spell_mastery",
    "num_mounts", "rank_depth",
)
ENTITY_STAT_FIELDS = ("walk_speed", "run_speed", "charge_speed", "fly_speed", "mass")
MELEE_FIELDS = (
    "key", "damage", "ap_damage", "bonus_v_large", "bonus_v_infantry", "is_magical",
    "splash_attack_max_attacks", "splash_attack_power_multiplier", "melee_attack_interval",
    "building_damage_multiplier", "ignition_amount",
)
PROJECTILE_FIELDS = (
    "key", "category", "damage", "ap_damage", "bonus_v_large", "bonus_v_infantry", "effective_range",
    "minimum_range", "base_reload_time", "projectile_number", "shots_per_volley", "burst_size",
    "marksmanship_bonus", "is_magical", "ignition_amount", "shockwave_radius",
)
SHIELD_FIELDS = ("key", "shield_defence_value", "shield_armour_value", "missile_block_chance")


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    names: dict[str, str | None] = {}
    if ctx.table_exists("main_units"):
        for r in ctx.rows("SELECT unit, land_unit FROM main_units"):
            land_unit = opt(r["land_unit"])
            names[r["unit"]] = (ctx.catalog_name("unit", f"land_units_onscreen_name_{land_unit}")
                                if land_unit else None)
            if not land_unit:
                ctx.missing_names["unit"] += 1
    return {"unit": names}


def _distinct(ctx: Context, table: str, key_col: str, value_col: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    if ctx.table_exists(table):
        for r in ctx.rows(f'SELECT DISTINCT "{key_col}" AS k, "{value_col}" AS v FROM "{table}" ORDER BY 1, 2'):
            if opt(r["v"]):
                out[r["k"]].append(r["v"])
    return out


def _custom_battle_factions(ctx: Context) -> dict[str, list[str]]:
    """Factions that field each unit in custom battles; campaign-exclusive rows are left out and counted."""
    out: dict[str, list[str]] = defaultdict(list)
    if not ctx.table_exists("units_custom_battle_permissions"):
        return out
    for r in ctx.rows("SELECT DISTINCT unit, faction, campaign_exclusive FROM units_custom_battle_permissions "
                      "ORDER BY unit, faction, campaign_exclusive"):
        if r["campaign_exclusive"]:
            ctx.tally["campaign_exclusive_permissions_excluded"] += 1
        elif opt(r["faction"]) and r["faction"] not in out[r["unit"]]:
            out[r["unit"]].append(r["faction"])
    return out


def _attribute(ctx: Context, key: str) -> dict:
    """An attribute's name and description; the bullet text's title names it when it has no name of its own."""
    title, body = split_title_body(ctx.loc.text(f"unit_attributes_bullet_text_{key}"))
    return {"key": key, "name": ctx.loc.text(f"unit_attributes_imued_effect_text_{key}") or title, "description": body}


def build(ctx: Context) -> dict[str, list[dict]]:
    if not ctx.require("unit", "main_units", "land_units"):
        return {"unit": []}
    land = by_key(ctx, "land_units", "key")
    entities = by_key(ctx, "battle_entities", "key")
    melee = by_key(ctx, "melee_weapons", "key")
    missile = by_key(ctx, "missile_weapons", "key")
    projectiles = by_key(ctx, "projectiles", "key")
    armour = by_key(ctx, "unit_armour_types", "key")
    shields = by_key(ctx, "unit_shield_types", "key")
    attributes = _distinct(ctx, "unit_attributes_to_groups_junctions", "attribute_group", "attribute")
    abilities = _distinct(ctx, "land_units_to_unit_abilites_junctions", "land_unit", "ability")
    characters = _distinct(ctx, "agent_subtypes", "associated_unit_override", "key")
    factions = _custom_battle_factions(ctx)
    buildings = _distinct(ctx, "building_units_allowed", "unit", "building")
    unit_sets = resolve_unit_sets(ctx)
    # Faction-specific cards are out of scope; take the unit's default card.
    cards = {r["unit"]: r["unit_card"] for r in ctx.rows(
        "SELECT unit, unit_card FROM unit_variants WHERE faction = ''")} if ctx.table_exists("unit_variants") else {}
    # Characters mostly have no card; their custom-battle portrait stands in.
    portraits: dict[str, str] = {}
    if ctx.table_exists("units_custom_battle_permissions"):
        for p in ctx.rows("SELECT * FROM units_custom_battle_permissions ORDER BY unit, faction"):
            if opt(p.get("general_portrait")) and p["unit"] not in portraits:
                portraits[p["unit"]] = p["general_portrait"]

    out = []
    for r in ctx.rows("SELECT * FROM main_units ORDER BY unit"):
        key = r["unit"]
        source = ("unit", key)
        lu = land.get(opt(r["land_unit"]))
        link = lambda t, k, rel: ctx.links.link(t, k, source=source, relation=rel)  # noqa: E731
        out.append({
            "key": key,
            "name": ctx.links.name("unit", key),
            "short_description": ctx.loc.text(f"unit_description_short_texts_text_{lu['short_description_text']}") if lu else None,
            "caste": r["caste"],
            "caste_name": ctx.loc.text(f"unit_castes_localised_name_{r['caste']}"),
            "category": lu["category"] if lu else None,
            "category_name": ctx.loc.text(f"unit_category_localised_name_{lu['category']}") if lu else None,
            "unit_class": lu["class"] if lu else None,
            "class_name": ctx.loc.text(f"unit_class_onscreen_{lu['class']}") if lu else None,
            "is_naval": r["is_naval"],
            "tier": r["tier"],
            "land_unit": lu["key"] if lu else None,
            "card_image": ctx.images.resolve("unit.card_image", cards.get(lu["key"]) if lu else None, UNIT_CARDS),
            "portrait_image": ctx.images.resolve("unit.portrait_image", portraits.get(key)),
            "recruitment_cost": r["recruitment_cost"],
            "upkeep_cost": r["upkeep_cost"],
            "multiplayer_cost": r["multiplayer_cost"],
            "campaign_cap": r["campaign_cap"],
            "multiplayer_cap": r["multiplayer_cap"],
            "base_stats": _base_stats(r, lu, entities, armour) if lu else None,
            "melee_weapon": _melee(melee.get(lu["primary_melee_weapon"])) if lu else None,
            "missile_weapon": _missile(missile.get(opt(lu["primary_missile_weapon"])), projectiles) if lu else None,
            "shield": _shield(shields.get(lu["shield"])) if lu else None,
            "mount": opt(lu["mount"]) if lu else None,
            "attributes": [
                _attribute(ctx, a)
                for a in (attributes.get(lu["attribute_group"], []) if lu and opt(lu["attribute_group"]) else [])
            ],
            "abilities": [link("ability", a, "abilities") for a in (abilities.get(lu["key"], []) if lu else [])],
            "characters": [link("character", c, "characters") for c in characters.get(key, [])],
            "unit_sets": unit_sets.get(key, []),
            "custom_battle_factions": [link("faction", f, "custom_battle_factions") for f in factions.get(key, [])],
            "recruited_by_buildings": [link("building_level", b, "recruited_by_buildings") for b in buildings.get(key, [])],
        })
    return {"unit": out}


def _base_stats(main: dict, lu: dict, entities: dict, armour: dict) -> dict:
    entity = entities.get(lu["man_entity"])
    stats = {f: lu[f] for f in LAND_STAT_FIELDS}
    stats.update({f: (entity[f] if entity else None) for f in ENTITY_STAT_FIELDS})
    stats["num_men"] = main["num_men"]
    stats["hit_points_per_entity"] = entity["hit_points"] if entity else None
    armour_row = armour.get(lu["armour"])
    stats["armour"] = armour_row["armour_value"] if armour_row else None
    return stats


def _melee(row: dict | None) -> dict | None:
    if row is None:
        return None
    weapon = {f: row[f] for f in MELEE_FIELDS}
    weapon["splash_attack_target_size"] = opt(row["splash_attack_target_size"])
    return weapon


def _missile(row: dict | None, projectiles: dict) -> dict | None:
    if row is None:
        return None
    projectile = projectiles.get(row["default_projectile"])
    built = None
    if projectile is not None:
        built = {f: projectile[f] for f in PROJECTILE_FIELDS}
        built["explosion_type"] = opt(projectile["explosion_type"])
    return {"key": row["key"], "projectile": built}


def _shield(row: dict | None) -> dict | None:
    if row is None or row["key"] == "none":
        return None
    return {f: row[f] for f in SHIELD_FIELDS}
