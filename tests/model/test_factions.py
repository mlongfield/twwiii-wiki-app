from twwiki.model import factions, schemas
from tests.model.fixtures import make_context


def factions_context():
    ctx = make_context({
        "factions": [{"key": "reikland", "subculture": "sc_empire", "category": "", "is_rebel": False,
                      "is_quest_faction": False, "flags_path": "ui/flags/reikland", "primary_colour_hex": "#ffcc00"}],
        "cultures": [{"key": "empire"}],
        "cultures_subcultures": [{"subculture": "sc_empire", "culture": "empire"}],
        "campaign_difficulty_handicap_effects": [
            {"campaign_difficulty_handicap": 2, "human": False, "effect": "e_research_cost", "effect_scope": "faction_to_faction_own_unseen",
             "effect_value": -100.0, "optional_campaign_key": ""},
            {"campaign_difficulty_handicap": 2, "human": True, "effect": "e_growth", "effect_scope": "faction_to_province_own",
             "effect_value": 5.0, "optional_campaign_key": "main_warhammer"},
        ],
        "campaign_variables": [{"variable_key": "base_research_points_per_turn", "value": 100.0},
                               {"variable_key": "minimum_research_rate", "value": 5.0}],
        "campaigns_campaign_variables_junctions": [{"variable_key": "minimum_research_rate", "campaign_name": "wh3_main_chaos",
                                                   "value": 7.0, "difficulty": "", "campaign_type": ""}],
    }, loc={
        "factions_screen_name_reikland": "Reikland",
        "cultures_name_empire": "The Empire",
        "cultures_subcultures_name_sc_empire": "The Empire",
    })
    for entity_type, names in factions.catalog(ctx).items():
        ctx.links.register(entity_type, names)
    ctx.links.register("effect", {"e_research_cost": "Research cost", "e_growth": "Growth"})
    return ctx


def test_faction_culture_and_subculture_links():
    ctx = factions_context()
    built = factions.build(ctx)
    reikland = built["faction"][0]
    assert reikland["name"] == "Reikland"
    assert reikland["subculture"]["key"] == "sc_empire" and reikland["culture"]["name"] == "The Empire"
    assert built["subculture"][0]["culture"]["key"] == "empire"
    assert [l["key"] for l in ctx.links.referrers("culture", "empire", "culture", source_type="faction")] == ["reikland"]
    for entity_type in ("faction", "culture", "subculture"):
        for entity in built[entity_type]:
            schemas.ENTITY_MODELS[entity_type].model_validate(entity)


def test_difficulty_levels_split_ai_and_human():
    ctx = factions_context()
    assert ctx.links.has("difficulty_level", "2") and ctx.missing_names["difficulty_level"] == 0
    level = factions.build(ctx)["difficulty_level"][0]
    assert level["key"] == "2" and level["level"] == 2
    assert level["ai"][0]["application"]["value"] == -100.0 and level["ai"][0]["campaign"] is None
    assert level["ai"][0]["application"]["source"] == {"type": "difficulty_level", "key": "2", "name": None, "missing": False}
    assert level["human"][0]["campaign"] == "main_warhammer"
    schemas.ENTITY_MODELS["difficulty_level"].model_validate(level)


def test_campaign_variables_with_overrides():
    variables = {v["key"]: v for v in factions.build(factions_context())["campaign_variable"]}
    assert variables["base_research_points_per_turn"]["value"] == 100.0
    assert variables["base_research_points_per_turn"]["overrides"] == []
    assert variables["minimum_research_rate"]["overrides"] == [
        {"campaign": "wh3_main_chaos", "difficulty": None, "campaign_type": None, "value": 7.0}]
    for v in variables.values():
        schemas.ENTITY_MODELS["campaign_variable"].model_validate(v)
