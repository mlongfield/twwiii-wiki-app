from twwiki.model import schemas, technologies
from tests.model.fixtures import make_context


def node(key, tech, tree, rp, tier=0, indent=0, cost_per_round=0, resource_cost=""):
    return {"key": key, "technology_key": tech, "technology_node_set": tree, "tier": tier, "indent": indent,
            "research_points_required": rp, "cost_per_round": cost_per_round, "food_cost": 0,
            "optional_ui_group": "", "resource_cost": resource_cost, "required_parents": 0,
            "pixel_offset_x": 0, "pixel_offset_y": 0, "faction_key": "", "campaign_key": ""}


def tech_context():
    ctx = make_context({
        "technologies": [
            {"key": "heavy_weapons", "building_level": "", "icon_name": "hw.png", "is_civil": False,
             "is_engineering": False, "is_military": True, "is_hidden": False},
            {"key": "agent_unlock", "building_level": "pyramid_1", "icon_name": "a.png", "is_civil": True,
             "is_engineering": False, "is_military": False, "is_hidden": False},
            {"key": "piracy", "building_level": "", "icon_name": "p.png", "is_civil": False,
             "is_engineering": False, "is_military": False, "is_hidden": False},
        ],
        "technology_node_sets": [
            {"key": "emp_civ_reworkd", "culture": "wh_main_emp_empire", "subculture": "", "faction_key": "",
             "campaign_key": "", "colour_hex": "#ffffff"},
            {"key": "emp_wulfhart", "culture": "wh_main_emp_empire", "subculture": "", "faction_key": "wulfhart_faction",
             "campaign_key": "", "colour_hex": "#000000"},
        ],
        "technology_nodes": [
            node("hw_node", "heavy_weapons", "emp_civ_reworkd", 900, tier=1, indent=1),
            node("hw_wulf_node", "heavy_weapons", "emp_wulfhart", 700, tier=0, indent=1),
            node("agent_node", "agent_unlock", "emp_civ_reworkd", 500, cost_per_round=5000, resource_cost="jars_250"),
        ],
        "technology_node_links": [{"parent_key": "agent_node", "child_key": "hw_node", "initial_descent_tiers": 0, "visible_in_ui": True}],
        "technology_required_technology_junctions": [{"technology": "heavy_weapons", "required_technology": "agent_unlock"}],
        "technology_required_building_levels_junctions": [{"technology": "heavy_weapons", "required_building_level": "forge_2"}],
        "technology_effects_junction": [{"technology": "heavy_weapons", "effect": "e_attack", "effect_scope": "faction_to_force_own", "value": 4.0}],
        "resource_costs": [{"id": "jars_250", "treasury_cost": 0}],
        "resource_cost_pooled_resource_junctions": [{"resource_cost": "jars_250", "pooled_resource_factor": "canopic_jars_technology",
                                                     "amount": -250, "context": "absolute"}],
        "resource_cost_trade_resource_junctions": [{"resource_cost": "jars_250", "trade_resource": "res_gems"}],
    }, loc={
        "technologies_onscreen_name_heavy_weapons": "Improved Heavy Weapons",
        "technologies_short_description_heavy_weapons": "Bigger swords.",
        "technology_node_sets_localised_name_emp_civ_reworkd": "Empire Civil Tech",
    })
    for entity_type, names in technologies.catalog(ctx).items():
        ctx.links.register(entity_type, names)
    ctx.links.register("effect", {"e_attack": "Melee attack: %+n"})
    ctx.links.register("building_level", {"pyramid_1": "Pyramid", "forge_2": "Forge"})
    ctx.links.register("culture", {"wh_main_emp_empire": "The Empire"})
    ctx.links.register("faction", {"wulfhart_faction": "Wulfhart"})
    return ctx


def test_resource_costs_embed_pooled_and_trade_resources():
    ctx = tech_context()
    assert technologies.load_resource_costs(ctx)["jars_250"] == {
        "key": "jars_250", "treasury_cost": 0,
        "pooled_resources": [{"pooled_resource_factor": "canopic_jars_technology", "amount": -250, "context": "absolute"}],
        "trade_resources": ["res_gems"],
    }


def test_technology_placements_carry_per_tree_costs():
    ctx = tech_context()
    built = technologies.build(ctx)
    techs = {t["key"]: t for t in built["technology"]}
    hw = techs["heavy_weapons"]
    assert hw["name"] == "Improved Heavy Weapons" and hw["description"] == "Bigger swords."
    assert [(p["tree"]["key"], p["research_points_required"], p["tier"]) for p in hw["placements"]] == [
        ("emp_civ_reworkd", 900, 1), ("emp_wulfhart", 700, 0)]
    assert [t["key"] for t in hw["required_technologies"]] == ["agent_unlock"]
    assert hw["required_buildings"][0]["name"] == "Forge"
    assert hw["effects"][0]["value"] == 4.0 and hw["effects"][0]["source"]["key"] == "heavy_weapons"

    agent = techs["agent_unlock"]
    assert agent["unlocked_by_building"]["key"] == "pyramid_1"
    placement = agent["placements"][0]
    assert placement["cost_per_round"] == 5000
    assert placement["resource_cost"]["pooled_resources"][0]["amount"] == -250

    assert techs["piracy"]["placements"] == []
    for tech in techs.values():
        schemas.ENTITY_MODELS["technology"].model_validate(tech)


def test_technology_tree_scope_nodes_and_links():
    ctx = tech_context()
    trees = {t["key"]: t for t in technologies.build(ctx)["technology_tree"]}
    civ = trees["emp_civ_reworkd"]
    assert civ["name"] == "Empire Civil Tech" and civ["culture"]["name"] == "The Empire"
    assert civ["faction"] is None
    assert [n["key"] for n in civ["nodes"]] == ["agent_node", "hw_node"]
    assert civ["nodes"][1]["technology"]["key"] == "heavy_weapons"
    assert civ["links"] == [{"parent": "agent_node", "child": "hw_node", "initial_descent_tiers": 0, "visible_in_ui": True}]
    assert trees["emp_wulfhart"]["faction"]["key"] == "wulfhart_faction"
    for tree in trees.values():
        schemas.ENTITY_MODELS["technology_tree"].model_validate(tree)
