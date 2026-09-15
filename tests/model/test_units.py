from twwiki.model import schemas, units
from tests.model.fixtures import make_context


def main_unit(**o):
    row = {"unit": "gs", "land_unit": "gs_land", "caste": "melee_infantry", "is_naval": False, "tier": 3,
           "num_men": 120, "recruitment_cost": 850, "upkeep_cost": 225, "multiplayer_cost": 700,
           "campaign_cap": -1, "multiplayer_cap": 0}
    row.update(o)
    return row


def land_unit(**o):
    row = {"key": "gs_land", "category": "inf_melee", "class": "inf_mel", "man_entity": "man",
           "primary_melee_weapon": "greatsword", "primary_missile_weapon": "", "armour": "plate",
           "shield": "none", "mount": "", "attribute_group": "gs_attrs", "short_description_text": "gs_short",
           "bonus_hit_points": 68, "melee_attack": 32, "melee_defence": 30, "charge_bonus": 18, "morale": 75,
           "accuracy": 10, "reload": 0, "primary_ammo": 0, "secondary_ammo": 0, "damage_mod_physical": 0,
           "damage_mod_magic": 0, "damage_mod_flame": 0, "damage_mod_missile": 0, "damage_mod_all": 0,
           "healing_power": 1.0, "spell_mastery": 1.0, "num_mounts": 0, "rank_depth": 4}
    row.update(o)
    return row


def unit_context(extra_tables: dict | None = None):
    tables = {
        "main_units": [main_unit(),
                       main_unit(unit="ship", land_unit="", caste="warship", is_naval=True),
                       main_unit(unit="archers", land_unit="arch_land", caste="missile_infantry")],
        "land_units": [land_unit(),
                       land_unit(key="arch_land", primary_melee_weapon="nope", primary_missile_weapon="bow",
                                 attribute_group="", shield="small")],
        "battle_entities": [{"key": "man", "hit_points": 8, "walk_speed": 1.2, "run_speed": 2.8,
                             "charge_speed": 3.5, "fly_speed": 0.0, "mass": 90.0}],
        "melee_weapons": [{"key": "greatsword", "damage": 10, "ap_damage": 25, "bonus_v_large": 0,
                           "bonus_v_infantry": 14, "is_magical": False, "splash_attack_target_size": "",
                           "splash_attack_max_attacks": 0, "splash_attack_power_multiplier": 1.0,
                           "melee_attack_interval": 4.0, "building_damage_multiplier": 1.0, "ignition_amount": 0.0}],
        "missile_weapons": [{"key": "bow", "default_projectile": "arrow"}],
        "projectiles": [{"key": "arrow", "category": "arrow", "damage": 20, "ap_damage": 5, "bonus_v_large": 0,
                         "bonus_v_infantry": 0, "effective_range": 150, "minimum_range": 0, "base_reload_time": 10.0,
                         "projectile_number": 1, "shots_per_volley": 1, "burst_size": 1, "marksmanship_bonus": 0.0,
                         "is_magical": False, "ignition_amount": 0.0, "shockwave_radius": -1.0, "explosion_type": ""}],
        "unit_armour_types": [{"key": "plate", "armour_value": 95}],
        "unit_shield_types": [{"key": "small", "shield_defence_value": 3, "shield_armour_value": 10, "missile_block_chance": 35}],
        "unit_attributes_to_groups_junctions": [{"attribute": "hide_forest", "attribute_group": "gs_attrs"}],
        "land_units_to_unit_abilites_junctions": [{"ability": "hold", "land_unit": "gs_land"},
                                                  {"ability": "missing_ability", "land_unit": "gs_land"}],
        "agent_subtypes": [{"key": "captain", "associated_unit_override": "gs"}],
        "units_custom_battle_permissions": [{"faction": "reikland", "unit": "gs"}, {"faction": "reikland", "unit": "gs"}],
        "building_units_allowed": [{"building": "barracks_2", "unit": "gs"}],
    }
    if extra_tables:
        tables.update(extra_tables)
    ctx = make_context(tables, loc={
        "land_units_onscreen_name_gs_land": "Greatswords",
        "unit_description_short_texts_text_gs_short": "Elite melee.",
        "unit_castes_localised_name_melee_infantry": "Melee Infantry",
        "unit_category_localised_name_inf_melee": "Infantry",
        "unit_class_onscreen_inf_mel": "Melee Infantry",
        "unit_attributes_imued_effect_text_hide_forest": "Hide (forest)",
        "unit_attributes_bullet_text_hide_forest": "Hide (forest)||Can hide in forests.",
    })
    for entity_type, names in units.catalog(ctx).items():
        ctx.links.register(entity_type, names)
    ctx.links.register("ability", {"hold": "Hold the Line!"})
    ctx.links.register("character", {"captain": "Empire Captain"})
    ctx.links.register("faction", {"reikland": "Reikland"})
    ctx.links.register("building_level", {"barracks_2": "Barracks"})
    return ctx


def built_units():
    ctx = unit_context()
    return ctx, {u["key"]: u for u in units.build(ctx)["unit"]}


def test_greatswords_stats_weapons_and_links():
    ctx, built = built_units()
    gs = built["gs"]
    assert gs["name"] == "Greatswords" and gs["short_description"] == "Elite melee."
    assert (gs["caste_name"], gs["category_name"], gs["class_name"]) == ("Melee Infantry", "Infantry", "Melee Infantry")
    stats = gs["base_stats"]
    assert (stats["num_men"], stats["hit_points_per_entity"], stats["bonus_hit_points"]) == (120, 8, 68)
    assert (stats["melee_attack"], stats["melee_defence"], stats["armour"]) == (32, 30, 95)
    assert gs["melee_weapon"]["damage"] == 10 and gs["melee_weapon"]["ap_damage"] == 25
    assert gs["missile_weapon"] is None and gs["shield"] is None
    assert gs["attributes"] == [{"key": "hide_forest", "name": "Hide (forest)", "description": "Hide (forest)||Can hide in forests."}]
    assert [a["key"] for a in gs["abilities"]] == ["hold", "missing_ability"]
    assert gs["abilities"][1]["missing"] is True
    assert [c["key"] for c in gs["characters"]] == ["captain"]
    assert [f["key"] for f in gs["custom_battle_factions"]] == ["reikland"]
    assert [b["key"] for b in gs["recruited_by_buildings"]] == ["barracks_2"]
    assert [l["key"] for l in ctx.links.referrers("ability", "hold", "abilities")] == ["gs"]
    schemas.ENTITY_MODELS["unit"].model_validate(gs)


def test_archers_missile_weapon_shield_and_missing_melee_weapon():
    _, built = built_units()
    archers = built["archers"]
    assert archers["melee_weapon"] is None
    assert archers["missile_weapon"]["projectile"]["effective_range"] == 150
    assert archers["shield"]["missile_block_chance"] == 35
    schemas.ENTITY_MODELS["unit"].model_validate(archers)


def test_naval_unit_without_land_unit():
    _, built = built_units()
    ship = built["ship"]
    assert ship["name"] is None and ship["land_unit"] is None and ship["base_stats"] is None
    assert ship["category"] is None and ship["attributes"] == [] and ship["unit_sets"] == []
    schemas.ENTITY_MODELS["unit"].model_validate(ship)


def test_units_carry_resolved_unit_sets():
    ctx = unit_context(extra_tables={
        "unit_sets": [{"key": "all_inf_melee", "use_unit_exp_level_range": False, "min_unit_exp_level_inclusive": 0, "max_unit_exp_level_inclusive": 0},
                      {"key": "veteran_gs", "use_unit_exp_level_range": True, "min_unit_exp_level_inclusive": 3, "max_unit_exp_level_inclusive": 9}],
        "unit_set_to_unit_junctions": [{"unit_set": "all_inf_melee", "exclude": False, "unit_record": "", "unit_caste": "", "unit_category": "inf_melee", "unit_class": ""},
                                       {"unit_set": "veteran_gs", "exclude": False, "unit_record": "gs", "unit_caste": "", "unit_category": "", "unit_class": ""}],
    })
    built = {u["key"]: u for u in units.build(ctx)["unit"]}
    gs = built["gs"]
    archers = built["archers"]
    ship = built["ship"]

    assert gs["unit_sets"] == [{"key": "all_inf_melee", "conditional": False, "min_exp_level": None, "max_exp_level": None},
                                {"key": "veteran_gs", "conditional": True, "min_exp_level": 3, "max_exp_level": 9}]
    assert archers["unit_sets"] == [{"key": "all_inf_melee", "conditional": False, "min_exp_level": None, "max_exp_level": None}]
    assert ship["unit_sets"] == []
    assert "unit" not in ctx.partial
    schemas.ENTITY_MODELS["unit"].model_validate(gs)
    schemas.ENTITY_MODELS["unit"].model_validate(archers)
    schemas.ENTITY_MODELS["unit"].model_validate(ship)
