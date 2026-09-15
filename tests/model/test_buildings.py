from twwiki.model import buildings, schemas
from tests.model.fixtures import make_context


def level(key, chain, lvl, **o):
    row = {"level_name": key, "chain": chain, "level": lvl, "create_time": 1, "create_cost": 750, "upkeep_cost": 0,
           "only_in_capital": False, "faction_unique": False, "can_convert": True, "visible_in_ui": True,
           "development_point_cost": 0, "food_cost": 0, "resource_cost": ""}
    row.update(o)
    return row


def variant(building, culture="", subculture="", faction="", short=""):
    return {"building": building, "culture": culture, "subculture": subculture, "faction": faction,
            "short_description": short, "icon": "", "disables": False}


def building_context():
    ctx = make_context({
        "building_levels": [level("barracks_1", "emp_barracks", 0),
                            level("barracks_2", "emp_barracks", 1, create_cost=1500, resource_cost="scrap_50"),
                            level("tower", "tower_chain", 0)],
        "building_chains": [{"key": "emp_barracks", "chain_category": "military", "in_encyclopedia": True},
                            {"key": "tower_chain", "chain_category": "", "in_encyclopedia": False}],
        "building_culture_variants": [
            variant("barracks_1", culture="wh_main_emp_empire", short="barracks_1"),
            variant("tower", faction="followers"),
            variant("tower"),
        ],
        "building_effects_junction": [
            {"building": "barracks_1", "effect": "e_upkeep", "effect_scope": "province_to_province_own", "value": -5.0,
             "value_damaged": -2.0, "value_ruined": 0.0, "context_requirement": "IsChaosCampaign"}],
        "building_units_allowed": [{"building": "barracks_1", "unit": "spearmen"}],
        "resource_costs": [{"id": "scrap_50", "treasury_cost": 0}],
    }, loc={
        "building_culture_variants_name_barracks_1wh_main_emp_empire": "Training Field",
        "building_culture_variants_name_towerfollowers": "Faction Tower",
        "building_culture_variants_name_tower": "Black Tower",
        "building_short_description_texts_short_description_barracks_1": "Drill troops.",
        "building_chains_encyclopedia_name_emp_barracks": "",
        "building_chains_chain_tooltip_emp_barracks": "Barracks",
    })
    for entity_type, names in buildings.catalog(ctx).items():
        ctx.links.register(entity_type, names)
    ctx.links.register("effect", {"e_upkeep": "Upkeep"})
    ctx.links.register("unit", {"spearmen": "Spearmen"})
    return ctx


def test_level_names_prefer_generic_variant():
    ctx = building_context()
    assert ctx.links.name("building_level", "barracks_1") == "Training Field"
    assert ctx.links.name("building_level", "tower") == "Black Tower"
    assert ctx.links.name("building_level", "barracks_2") is None
    assert ctx.links.name("building_chain", "emp_barracks") == "Barracks"


def test_training_field_level():
    ctx = building_context()
    levels = {b["key"]: b for b in buildings.build(ctx)["building_level"]}
    tf = levels["barracks_1"]
    assert tf["chain"]["name"] == "Barracks" and tf["level"] == 0 and tf["create_cost"] == 750
    assert tf["cultures"] == ["wh_main_emp_empire"]
    assert tf["short_description"] == "Drill troops."
    effect = tf["effects"][0]
    assert (effect["value"], effect["value_damaged"], effect["value_ruined"]) == (-5.0, -2.0, 0.0)
    assert effect["context_requirement"] == "IsChaosCampaign"
    assert [u["key"] for u in tf["units_recruited"]] == ["spearmen"]
    assert levels["barracks_2"]["resource_cost"]["key"] == "scrap_50"
    for b in levels.values():
        schemas.ENTITY_MODELS["building_level"].model_validate(b)


def test_chain_lists_levels_in_order():
    ctx = building_context()
    chains = {c["key"]: c for c in buildings.build(ctx)["building_chain"]}
    assert [l["key"] for l in chains["emp_barracks"]["levels"]] == ["barracks_1", "barracks_2"]
    assert chains["tower_chain"]["category"] is None
    for c in chains.values():
        schemas.ENTITY_MODELS["building_chain"].model_validate(c)
