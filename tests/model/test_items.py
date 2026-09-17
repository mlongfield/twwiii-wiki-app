from twwiki.model import items, schemas
from tests.model.fixtures import make_context


def ancillary(**o):
    row = {"key": "blue_khepra", "type": "wh_main_anc_arcane_item", "applies_to": "character", "transferrable": True,
           "unique_to_world": True, "unique_to_faction": False, "legendary_item": False, "category": "arcane_item",
           "subcategory": "", "provided_bodyguard_unit": "", "uniqueness_score": 80}
    row.update(o)
    return row


def trait_level(key, trait, level, points=0):
    return {"key": key, "trait": trait, "level": level, "threshold_points": points}


def items_context():
    ctx = make_context({
        "ancillaries": [ancillary(), ancillary(key="banner", provided_bodyguard_unit="gs", legendary_item=True,
                                               subcategory="banner", uniqueness_score=999)],
        "ancillary_to_effects": [{"ancillary": "blue_khepra", "effect": "e_power", "effect_scope": "character_to_character_own", "value": 10.0}],
        "ancillary_to_included_agents": [{"ancillary": "blue_khepra", "agent": "wizard"}, {"ancillary": "blue_khepra", "agent": "general"}],
        "ancillaries_included_agent_subtypes": [{"ancillary": "blue_khepra", "agent_subtype": "liche_priest"}],
        "ancillaries_required_skills": [{"ancillary": "banner", "required_skill": "bearer", "required_skill_level": 1}],
        "ancillary_uniqueness_groupings": [
            {"group_key": "uncommon", "uniqueness_min": 80, "uniqueness_max": 100, "col_hex": "5DADE2"},
            {"group_key": "common", "uniqueness_min": 35, "uniqueness_max": 50, "col_hex": ""},
        ],
        "character_traits": [
            {"key": "brave", "no_going_back_level": 0, "hidden": False, "precedence": 1, "icon": "personality"},
            {"key": "coward", "no_going_back_level": 0, "hidden": True, "precedence": 2, "icon": "personality"},
        ],
        "character_trait_levels": [trait_level("brave_2", "brave", 2, 10), trait_level("brave", "brave", 1, 5),
                                   trait_level("coward_1", "coward", 1)],
        "trait_level_effects": [{"trait_level": "brave", "effect": "e_morale", "effect_scope": "character_to_force_own", "value": 2.0}],
        "trait_to_antitraits": [{"trait": "brave", "antitrait": "coward"}],
    }, loc={
        "ancillaries_onscreen_name_blue_khepra": "Blue Khepra",
        "ancillaries_colour_text_blue_khepra": "Sapphires.",
        "character_trait_levels_onscreen_name_brave": "Brave",
        "character_trait_levels_onscreen_name_brave_2": "Fearless",
        "character_trait_levels_onscreen_name_coward_1": "Coward",
        "ancillaries_categories_onscreen_name_arcane_item": "{{tr:arcane_item_title}}",
        "arcane_item_title": "Arcane Item",
        "ancillary_uniqueness_groupings_onscreen_name_uncommon": "[[col:ancillary_uncommon]]Uncommon[[/col]]",
    })
    for entity_type, names in items.catalog(ctx).items():
        ctx.links.register(entity_type, names)
    ctx.links.register("effect", {"e_power": "Power", "e_morale": "Morale"})
    ctx.links.register("character", {"liche_priest": "Liche Priest"})
    ctx.links.register("skill", {"bearer": "Battle Standard Bearer"})
    ctx.links.register("unit", {"gs": "Greatswords"})
    return ctx


def test_item_fields_and_links():
    ctx = items_context()
    built = {i["key"]: i for i in items.build(ctx)["item"]}
    khepra = built["blue_khepra"]
    assert khepra["name"] == "Blue Khepra" and khepra["description"] == "Sapphires."
    assert khepra["agent_types"] == [{"key": "general", "name": None}, {"key": "wizard", "name": None}]
    assert khepra["category"] == {"key": "arcane_item", "name": "Arcane Item"}
    assert khepra["rarity"] == {"key": "uncommon", "name": "[[col:ancillary_uncommon]]Uncommon[[/col]]", "colour": "#5DADE2"}
    assert "applies_to" not in khepra
    assert [s["key"] for s in khepra["agent_subtypes"]] == ["liche_priest"]
    assert khepra["effects"][0]["value"] == 10.0
    assert [l["key"] for l in ctx.links.referrers("character", "liche_priest", "agent_subtypes")] == ["blue_khepra"]
    banner = built["banner"]
    assert banner["legendary"] is True and banner["subcategory"] == "banner"
    assert banner["bodyguard_unit"]["key"] == "gs"
    assert banner["required_skills"] == [{"skill": {"type": "skill", "key": "bearer", "name": "Battle Standard Bearer", "missing": False}, "level": 1}]
    assert banner["rarity"] is None and ctx.tally["unmatched_rarity_scores"] == 1
    for item in built.values():
        schemas.ENTITY_MODELS["item"].model_validate(item)


def test_trait_names_levels_and_antitraits():
    ctx = items_context()
    assert ctx.links.name("trait", "brave") == "Brave"
    assert ctx.links.name("trait", "coward") == "Coward"
    traits = {t["key"]: t for t in items.build(ctx)["trait"]}
    brave = traits["brave"]
    assert [(l["key"], l["level"], l["name"]) for l in brave["levels"]] == [("brave", 1, "Brave"), ("brave_2", 2, "Fearless")]
    assert brave["levels"][0]["effects"][0]["value"] == 2.0
    assert [a["key"] for a in brave["antitraits"]] == ["coward"]
    for trait in traits.values():
        schemas.ENTITY_MODELS["trait"].model_validate(trait)
