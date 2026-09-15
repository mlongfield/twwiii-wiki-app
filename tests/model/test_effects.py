from twwiki.model import effects, schemas
from tests.model.fixtures import make_context, register_catalogs


def columns(table, *cols_and_refs):
    return [{"table_name": table, "column_name": c, "ref_table": r} for c, r in cols_and_refs]


def effects_context(**overrides):
    tables = {
        "effects": [
            {"effect": "e_attack", "icon": "a.png", "priority": 1, "icon_negative": "", "category": "battle", "is_positive_value_good": True},
            {"effect": "e_research", "icon": "", "priority": 2, "icon_negative": "", "category": "campaign", "is_positive_value_good": True},
        ],
        "effect_bundles": [{"key": "b1", "localised_description": "", "localised_title": "", "bundle_target": "faction",
                            "priority": 0, "ui_icon": "b.png", "is_global_effect": False, "show_in_3d_space": False, "owner_only": False}],
        "effect_bundles_to_effects_junctions": [{"effect_bundle_key": "b1", "effect_key": "e_research",
                                                 "effect_scope": "faction_to_faction_own", "value": 5.0, "advancement_stage": "start_turn_completed"}],
        "unit_abilities": [{"key": "hold"}],
        "effect_bonus_value_basic_junction": [{"effect": "e_research", "bonus_value_id": "research_points"}],
        "effect_bonus_value_ids_unit_sets": [{"bonus_value_id": "melee_attack_mod", "effect": "e_attack", "unit_set": "giants"}],
        "effect_bonus_value_unit_ability_junctions": [{"effect": "e_attack", "bonus_value_id": "enable", "unit_ability": "hold"}],
        "effect_bonus_value_unit_set_unit_ability_junctions": [{"bonus_value_id": "enable", "effect": "e_attack", "unit_set_ability": "combo"}],
        "unit_set_unit_ability_junctions": [{"key": "combo", "unit_ability": "hold", "unit_set": "engineers"}],
        "_columns": (
            columns("effect_bonus_value_basic_junction", ("effect", "effects"), ("bonus_value_id", "campaign_bonus_value_ids_basic"))
            + columns("effect_bonus_value_ids_unit_sets", ("bonus_value_id", "x"), ("effect", "effects"), ("unit_set", "unit_sets"))
            + columns("effect_bonus_value_unit_ability_junctions", ("effect", "effects"), ("bonus_value_id", "x"), ("unit_ability", "unit_abilities"))
            + columns("effect_bonus_value_unit_set_unit_ability_junctions", ("bonus_value_id", "x"), ("effect", "effects"),
                      ("unit_set_ability", "unit_set_unit_ability_junctions"))
        ),
    }
    tables.update(overrides)
    loc = {
        "effects_description_e_attack": "Melee attack: %+n",
        "effects_description_e_research": "{{tr:research}}: %+n",
        "ui_text_replacements_localised_text_research": "Research rate",
        "effect_bundles_localised_title_b1": "First Book",
    }
    ctx = make_context(tables, loc)
    register_catalogs(ctx, effects)
    ctx.links.register("ability", {"hold": "Hold the Line!"})
    return ctx


def test_catalog_uses_description_and_title():
    ctx = effects_context()
    assert ctx.links.name("effect", "e_research") == "Research rate: %+n"
    assert ctx.links.name("effect_bundle", "b1") == "First Book"


def test_bonus_targets_cover_each_table_shape():
    ctx = effects_context()
    built = {e["key"]: e for e in effects.build(ctx)["effect"]}

    assert built["e_research"]["bonus_targets"] == [{
        "bonus_value_id": "research_points", "source_table": "effect_bonus_value_basic_junction",
        "target_table": None, "target_key": None, "target": None,
        "unit_set": None, "ability": None, "attribute": None, "phase": None}]

    attack = {t["source_table"]: t for t in built["e_attack"]["bonus_targets"]}
    assert attack["effect_bonus_value_ids_unit_sets"]["unit_set"] == "giants"
    assert attack["effect_bonus_value_ids_unit_sets"]["target"] is None
    assert attack["effect_bonus_value_unit_ability_junctions"]["target"] == {
        "type": "ability", "key": "hold", "name": "Hold the Line!", "missing": False}
    combo = attack["effect_bonus_value_unit_set_unit_ability_junctions"]
    assert combo["unit_set"] == "engineers" and combo["ability"]["key"] == "hold"
    assert combo["target_table"] == "unit_set_unit_ability_junctions" and combo["target_key"] == "combo"

    assert [l["key"] for l in ctx.links.referrers("ability", "hold", "bonus_target")] == ["e_attack"]
    for entity in built.values():
        schemas.ENTITY_MODELS["effect"].model_validate(entity)


def test_bundle_effect_applications_link_effect_and_source():
    ctx = effects_context()
    bundle = effects.build(ctx)["effect_bundle"][0]
    assert bundle["title"] == "First Book"
    app = bundle["effects"][0]
    assert app["effect"]["key"] == "e_research" and app["value"] == 5.0
    assert app["source"] == {"type": "effect_bundle", "key": "b1", "name": "First Book", "missing": False}
    assert app["advancement_stage"] == "start_turn_completed"
    assert [l["key"] for l in ctx.links.referrers("effect", "e_research", "effect")] == ["b1"]
    schemas.ENTITY_MODELS["effect_bundle"].model_validate(bundle)


def test_missing_effects_table_is_partial():
    ctx = make_context({"_columns": columns("x", ("a", None))})
    assert effects.catalog(ctx) == {"effect": {}, "effect_bundle": {}}
    assert effects.build(ctx) == {"effect": [], "effect_bundle": []}
    assert ctx.partial == {"effect": ["effects"], "effect_bundle": ["effect_bundles", "effect_bundles_to_effects_junctions"]}


def test_missing_columns_table_is_reported_and_bonus_targets_stay_empty():
    ctx = make_context({
        "effects": [{"effect": "e_attack", "icon": "a.png", "priority": 1, "icon_negative": "",
                    "category": "battle", "is_positive_value_good": True}],
    })
    register_catalogs(ctx, effects)
    built = effects.build(ctx)
    assert built["effect"][0]["bonus_targets"] == []
    assert ctx.partial["effect"] == ["_columns"]
    schemas.ENTITY_MODELS["effect"].model_validate(built["effect"][0])


def test_direct_unit_attribute_and_phase_targets_fill_attribute_and_phase():
    ctx = effects_context(
        effect_bonus_value_unit_attribute_junctions=[
            {"effect": "e_attack", "bonus_value_id": "toughen", "unit_attribute": "unbreakable"}
        ],
        _columns=(
            columns("effect_bonus_value_basic_junction", ("effect", "effects"), ("bonus_value_id", "campaign_bonus_value_ids_basic"))
            + columns("effect_bonus_value_ids_unit_sets", ("bonus_value_id", "x"), ("effect", "effects"), ("unit_set", "unit_sets"))
            + columns("effect_bonus_value_unit_ability_junctions", ("effect", "effects"), ("bonus_value_id", "x"), ("unit_ability", "unit_abilities"))
            + columns("effect_bonus_value_unit_set_unit_ability_junctions", ("bonus_value_id", "x"), ("effect", "effects"),
                      ("unit_set_ability", "unit_set_unit_ability_junctions"))
            + columns("effect_bonus_value_unit_attribute_junctions", ("effect", "effects"), ("bonus_value_id", "x"),
                      ("unit_attribute", "unit_attributes"))
        )
    )
    built = {e["key"]: e for e in effects.build(ctx)["effect"]}
    attack = {t["source_table"]: t for t in built["e_attack"]["bonus_targets"]}
    direct = attack["effect_bonus_value_unit_attribute_junctions"]
    assert direct["attribute"] == "unbreakable"
    assert direct["target_key"] == "unbreakable" and direct["target"] is None
    schemas.ENTITY_MODELS["effect"].model_validate(built["e_attack"])


def test_unrecognised_bonus_table_is_skipped_and_recorded():
    ctx = effects_context(
        effect_bonus_value_weird_junction=[
            {"thing": "e_attack", "other": "x"}
        ],
        _columns=(
            columns("effect_bonus_value_basic_junction", ("effect", "effects"), ("bonus_value_id", "campaign_bonus_value_ids_basic"))
            + columns("effect_bonus_value_ids_unit_sets", ("bonus_value_id", "x"), ("effect", "effects"), ("unit_set", "unit_sets"))
            + columns("effect_bonus_value_unit_ability_junctions", ("effect", "effects"), ("bonus_value_id", "x"), ("unit_ability", "unit_abilities"))
            + columns("effect_bonus_value_unit_set_unit_ability_junctions", ("bonus_value_id", "x"), ("effect", "effects"),
                      ("unit_set_ability", "unit_set_unit_ability_junctions"))
            + columns("effect_bonus_value_weird_junction", ("thing", None), ("other", None))
        )
    )
    built = effects.build(ctx)
    assert "effect_bonus_value_weird_junction (unrecognised columns)" in ctx.partial["effect"]
    # e_attack's bonus_targets should not include the weird junction
    attack_targets = {e["key"]: e for e in built["effect"]}["e_attack"]["bonus_targets"]
    assert not any(t["source_table"] == "effect_bonus_value_weird_junction" for t in attack_targets)


def test_bonus_table_with_two_target_columns_is_skipped_and_recorded():
    ctx = effects_context(
        effect_bonus_value_double_junction=[
            {"effect": "e_attack", "bonus_value_id": "b", "first": "x", "second": "y"}
        ],
        _columns=(
            columns("effect_bonus_value_basic_junction", ("effect", "effects"), ("bonus_value_id", "campaign_bonus_value_ids_basic"))
            + columns("effect_bonus_value_ids_unit_sets", ("bonus_value_id", "x"), ("effect", "effects"), ("unit_set", "unit_sets"))
            + columns("effect_bonus_value_unit_ability_junctions", ("effect", "effects"), ("bonus_value_id", "x"), ("unit_ability", "unit_abilities"))
            + columns("effect_bonus_value_unit_set_unit_ability_junctions", ("bonus_value_id", "x"), ("effect", "effects"),
                      ("unit_set_ability", "unit_set_unit_ability_junctions"))
            + columns("effect_bonus_value_double_junction", ("effect", "effects"), ("bonus_value_id", "x"), ("first", None), ("second", None))
        )
    )
    built = effects.build(ctx)
    assert "effect_bonus_value_double_junction (unrecognised columns)" in ctx.partial["effect"]
    # e_attack's bonus_targets should not include the double junction
    attack_targets = {e["key"]: e for e in built["effect"]}["e_attack"]["bonus_targets"]
    assert not any(t["source_table"] == "effect_bonus_value_double_junction" for t in attack_targets)
