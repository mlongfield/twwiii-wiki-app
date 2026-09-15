from twwiki.model import abilities, schemas
from tests.model.fixtures import make_context, register_catalogs


def special(**overrides):
    row = {
        "key": "hold", "active_time": -1.0, "recharge_time": -1.0, "num_uses": -1, "effect_range": 35.0,
        "affect_self": True, "num_effected_friendly_units": -1, "num_effected_enemy_units": 0,
        "initial_recharge": 0.0, "activated_projectile": "", "target_friends": False, "target_enemies": False,
        "target_ground": False, "wind_up_time": 0.0, "passive": True, "bombardment": "", "spawned_unit": "",
        "mana_cost": 0.0, "min_range": 0.0, "vortex": "", "miscast_chance": 0.0, "target_self": False,
    }
    row.update(overrides)
    return row


def phase_row(**overrides):
    row = {
        "id": "hold_phase", "duration": -1.0, "effect_type": "positive", "cant_move": False,
        "fatigue_change_ratio": 0.0, "ability_recharge_change": 0.0, "hp_change_frequency": 0.0,
        "damage_amount": 0, "max_damaged_entities": 0, "resurrect": False, "mana_regen_mod": 0.0,
        "imbue_magical": False, "imbue_ignition": 0, "is_hidden_in_ui": False, "replenish_ammo": 0.0,
        "heal_amount": 0.0, "execute_ratio": 0.0,
    }
    row.update(overrides)
    return row


def ability_context():
    ctx = make_context({
        "unit_abilities": [
            {"key": "hold", "requires_effect_enabling": False, "icon_name": "hold.png", "type": "wh_type_augment",
             "is_unit_upgrade": False, "is_hidden_in_ui": False, "source_type": "lord"},
            {"key": "plain", "requires_effect_enabling": False, "icon_name": "p.png", "type": "wh_type_augment",
             "is_unit_upgrade": False, "is_hidden_in_ui": True, "source_type": "unit"},
        ],
        "unit_special_abilities": [special()],
        "special_ability_to_special_ability_phase_junctions": [
            {"order": 0, "phase": "hold_phase", "special_ability": "hold",
             "target_self": True, "target_friends": True, "target_enemies": False},
            {"order": 1, "phase": "gone_phase", "special_ability": "hold",
             "target_self": True, "target_friends": False, "target_enemies": False},
        ],
        "special_ability_phases": [phase_row()],
        "special_ability_phase_stat_effects": [
            {"phase": "hold_phase", "value": 5.0, "stat": "stat_melee_defence", "how": "add"},
            {"phase": "hold_phase", "value": 4.0, "stat": "stat_morale", "how": "add"},
        ],
        "special_ability_phase_attribute_effects": [
            {"attribute": "unbreakable", "phase": "hold_phase", "attribute_type": "positive"}],
        "modifiable_unit_stats": [{"stat_key": "stat_melee_defence", "localisation": "stat_melee_defence"},
                                  {"stat_key": "stat_morale", "localisation": "stat_morale"}],
    }, loc={
        "unit_abilities_onscreen_name_hold": "Hold the Line!",
        "unit_abilities_tooltip_text_hold": "Stand firm.",
        "unit_ability_source_types_name_lord": "Lord Ability",
        "unit_stat_localisations_onscreen_name_stat_melee_defence": "Melee Defence",
        "unit_stat_localisations_onscreen_name_stat_morale": "Leadership",
    })
    register_catalogs(ctx, abilities)
    return ctx


def test_hold_the_line_activation_and_phases():
    ctx = ability_context()
    built = {a["key"]: a for a in abilities.build(ctx)["ability"]}
    hold = built["hold"]
    assert hold["name"] == "Hold the Line!" and hold["description"] == "Stand firm."
    assert hold["source_type_name"] == "Lord Ability"
    assert hold["activation"]["passive"] is True and hold["activation"]["effect_range"] == 35.0
    assert len(hold["phases"]) == 1
    phase = hold["phases"][0]
    assert phase["order"] == 0 and phase["target_friends"] is True
    assert phase["stat_effects"] == [
        {"stat": "stat_melee_defence", "stat_name": "Melee Defence", "value": 5.0, "how": "add"},
        {"stat": "stat_morale", "stat_name": "Leadership", "value": 4.0, "how": "add"},
    ]
    assert phase["attribute_effects"] == [{"attribute": "unbreakable", "attribute_type": "positive"}]
    assert ctx.links.missing["ability.phase->special_ability_phase"] == 1
    schemas.ENTITY_MODELS["ability"].model_validate(hold)


def test_ability_without_special_row_has_no_activation():
    plain = {a["key"]: a for a in abilities.build(ability_context())["ability"]}["plain"]
    assert plain["name"] is None and plain["activation"] is None and plain["phases"] == []
    assert plain["units"] == [] and plain["modified_by_effects"] == []
    schemas.ENTITY_MODELS["ability"].model_validate(plain)
