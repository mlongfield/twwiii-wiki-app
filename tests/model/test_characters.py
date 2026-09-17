from twwiki.model import characters, schemas
from tests.model.fixtures import make_context


def subtype(**o):
    row = {"key": "kf", "associated_unit_override": "kf_unit", "magic_lore": "", "is_caster": False,
           "can_equip_ancillaries": True, "recruitable": True, "can_gain_xp": True, "cost": 1100, "cap": -1}
    row.update(o)
    return row


def skill_node(key, skill, tier, indent, **o):
    row = {"key": key, "character_skill_key": skill, "tier": tier, "indent": indent, "points_on_creation": 0,
           "required_num_parents": 0, "visible_in_ui": True, "faction_key": "", "subculture": "", "campaign_key": ""}
    row.update(o)
    return row


def character_context(extra_items=None, extra_links=None):
    items = [{"set": "kf_tree", "item": "n_leader"}, {"set": "kf_tree", "item": "n_mentor"}]
    if extra_items:
        items.extend(extra_items)
    node_links = [{"parent_key": "n_leader", "child_key": "n_mentor", "link_type": "REQUIRED",
                   "initial_descent_tiers": 0}]
    if extra_links:
        node_links.extend(extra_links)
    ctx = make_context({
        "agent_subtypes": [subtype(), subtype(key="wizard", associated_unit_override="wiz_unit",
                                             magic_lore="lore_fire", is_caster=True)],
        "main_units": [{"unit": "kf_unit", "land_unit": "kf_land"}, {"unit": "wiz_unit", "land_unit": "wiz_land"}],
        "land_units_to_unit_abilites_junctions": [{"ability": "hold", "land_unit": "kf_land"}],
        "faction_agent_permitted_subtypes": [
            {"agent": "general", "faction": "reikland", "subtype": "kf"},
            {"agent": "general", "faction": "golden_order", "subtype": "kf"},
            {"agent": "wizard", "faction": "reikland", "subtype": "wizard"},
        ],
        "special_ability_groups": [{"ability_group": "lore_fire"}],
        "character_skill_node_sets": [
            {"key": "kf_tree", "agent_subtype_key": "kf", "agent_key": "general", "faction_key": "", "subculture": "",
             "campaign_key": "", "for_army": False, "for_navy": False},
            {"key": "orphan_tree", "agent_subtype_key": "", "agent_key": "champion", "faction_key": "", "subculture": "",
             "campaign_key": "", "for_army": False, "for_navy": False},
        ],
        "character_skill_node_set_items": items,
        "character_skill_nodes": [skill_node("n_leader", "leader_of_men", 7, 0),
                                  skill_node("n_mentor", "mentor", 30, 0, subculture="wh_main_sc_emp_empire"),
                                  skill_node("n_other", "leader_of_men", 7, 0)],
        "character_skill_node_links": node_links,
        "character_skill_nodes_skill_locks": [{"character_skill": "mentor", "character_skill_node": "n_mentor", "level": 2}],
        "character_skills": [
            {"key": "leader_of_men", "image_path": "leader.png", "unlocked_at_rank": 7, "is_background_skill": False},
            {"key": "mentor", "image_path": "mentor.png", "unlocked_at_rank": 0, "is_background_skill": False},
        ],
        "character_skill_level_to_effects_junctions": [
            {"character_skill_key": "leader_of_men", "effect_key": "e_aura", "effect_scope": "character_to_character_own", "level": 1, "value": 50.0},
            {"character_skill_key": "mentor", "effect_key": "e_xp", "effect_scope": "character_to_character_own", "level": 1, "value": 15.0},
            {"character_skill_key": "mentor", "effect_key": "e_xp", "effect_scope": "character_to_character_own", "level": 2, "value": 30.0},
        ],
        "character_skill_level_details": [{"skill_key": "mentor", "level": 2, "unlocked_at_rank": 12,
                                           "faction_key": "", "subculture_key": "", "campaign_key": "", "image_path": "x"}],
    }, loc={
        "land_units_onscreen_name_kf_land": "Emperor Karl Franz",
        "agent_subtypes_onscreen_name_override_kf": "Legendary Lord",
        "agent_subtypes_onscreen_name_override_wizard": "Bright Wizard",
        "special_ability_groups_name_lore_fire": "Lore of Fire",
        "character_skills_localised_name_leader_of_men": "Leader of Men",
        "agent_culture_details_onscreen_name_11": "General of the Empire",
        "agent_culture_details_onscreen_name_12": "Lord",
        "agent_culture_details_onscreen_name_13": "Lord",
        "agent_culture_details_onscreen_name_14": "Damsel",
        "agent_culture_details_onscreen_name_15": "Runesmith",
    })
    for entity_type, names in characters.catalog(ctx).items():
        ctx.links.register(entity_type, names)
    ctx.links.register("unit", {"kf_unit": "Emperor Karl Franz", "wiz_unit": None})
    ctx.links.register("ability", {"hold": "Hold the Line!"})
    ctx.links.register("faction", {"reikland": "Reikland", "golden_order": "Golden Order"})
    ctx.links.register("effect", {"e_aura": "Leadership aura size: %+n%", "e_xp": "XP"})
    return ctx


def test_catalog_names_characters_from_their_unit():
    ctx = character_context()
    assert ctx.links.name("character", "kf") == "Emperor Karl Franz"
    assert ctx.links.name("character", "wizard") == "Bright Wizard"


def test_karl_franz_character_and_tree():
    ctx = character_context()
    built = characters.build(ctx)
    kf = {c["key"]: c for c in built["character"]}["kf"]
    assert kf["name"] == "Emperor Karl Franz" and kf["title"] == "Legendary Lord"
    assert kf["agent_types"] == [{"key": "general", "name": None}]
    assert kf["associated_unit"]["key"] == "kf_unit"
    assert [f["key"] for f in kf["factions"]] == ["golden_order", "reikland"]
    assert [a["key"] for a in kf["abilities"]] == ["hold"]
    assert len(kf["skill_trees"]) == 1
    tree = kf["skill_trees"][0]
    assert [n["key"] for n in tree["nodes"]] == ["n_leader", "n_mentor"]
    assert tree["nodes"][1]["subculture"] == "wh_main_sc_emp_empire"
    assert tree["links"] == [{"parent": "n_leader", "child": "n_mentor", "link_type": "REQUIRED", "initial_descent_tiers": 0}]
    assert tree["locks"][0]["skill"]["key"] == "mentor" and tree["locks"][0]["level"] == 2
    assert ctx.links.missing["skill_tree.no_agent_subtype"] == 1
    assert [l["key"] for l in ctx.links.referrers("skill", "mentor", "skill_tree")] == ["kf"]
    schemas.ENTITY_MODELS["character"].model_validate(kf)


def test_wizard_lore_of_magic():
    wizard = {c["key"]: c for c in characters.build(character_context())["character"]}["wizard"]
    assert wizard["lore_of_magic"] == {"key": "lore_fire", "name": "Lore of Fire"}
    assert wizard["skill_trees"] == []
    schemas.ENTITY_MODELS["character"].model_validate(wizard)


def test_skill_levels_and_effects():
    ctx = character_context()
    skills = {s["key"]: s for s in characters.build(ctx)["skill"]}
    leader = skills["leader_of_men"]
    assert leader["name"] == "Leader of Men"
    assert leader["levels"] == [{"level": 1, "unlocked_at_rank": None, "effects": [leader["levels"][0]["effects"][0]]}]
    assert leader["levels"][0]["effects"][0]["value"] == 50.0
    mentor = skills["mentor"]
    assert [(l["level"], l["unlocked_at_rank"]) for l in mentor["levels"]] == [(1, None), (2, 12)]
    for skill in skills.values():
        schemas.ENTITY_MODELS["skill"].model_validate(skill)


def test_skill_tree_links_to_a_node_outside_the_tree_are_dropped_and_counted():
    ctx = character_context(extra_links=[{"parent_key": "n_leader", "child_key": "n_other",
                                          "link_type": "REQUIRED", "initial_descent_tiers": 0}])
    built = characters.build(ctx)
    kf = {c["key"]: c for c in built["character"]}["kf"]
    tree = kf["skill_trees"][0]
    assert tree["links"] == [{"parent": "n_leader", "child": "n_mentor", "link_type": "REQUIRED",
                              "initial_descent_tiers": 0}]
    assert ctx.links.missing["skill_tree.link_outside_tree"] == 1
    schemas.ENTITY_MODELS["character"].model_validate(kf)


def test_skill_tree_items_pointing_at_missing_nodes_are_counted():
    ctx = character_context(extra_items=[{"set": "kf_tree", "item": "n_gone"}])
    built = characters.build(ctx)
    kf = {c["key"]: c for c in built["character"]}["kf"]
    assert [n["key"] for n in kf["skill_trees"][0]["nodes"]] == ["n_leader", "n_mentor"]
    assert ctx.links.missing["skill_tree.missing_node"] == 1
    schemas.ENTITY_MODELS["character"].model_validate(kf)


def test_character_campaigns_and_skill_node_campaign_links():
    ctx = character_context()
    ctx.con.execute("CREATE TABLE campaign_to_agent_subtypes AS SELECT * FROM (VALUES "
                    "('kf', 'wh3_main_combi'), ('kf', 'wh3_main_chaos')) t(agent_subtype, campaign_type)")
    ctx.con.execute("UPDATE character_skill_nodes SET campaign_key = 'wh3_main_combi' WHERE key = 'n_mentor'")
    ctx.links.register("campaign", {"wh3_main_combi": "Immortal Empires", "wh3_main_chaos": "The Realm of Chaos"})
    built = {c["key"]: c for c in characters.build(ctx)["character"]}
    kf = built["kf"]
    assert [c["key"] for c in kf["campaigns"]] == ["wh3_main_chaos", "wh3_main_combi"]
    assert built["wizard"]["campaigns"] == []
    tree = kf["skill_trees"][0]
    assert tree["campaign"] is None
    assert tree["nodes"][0]["campaign"] is None and tree["nodes"][1]["campaign"]["name"] == "Immortal Empires"
    schemas.ENTITY_MODELS["character"].model_validate(kf)


def test_agent_type_names_use_the_character_culture_then_the_common_name():
    ctx = character_context()
    ctx.con.execute("CREATE TABLE agent_culture_details AS SELECT * FROM (VALUES "
                    "('general', 'wh_main_emp_empire', 11, 0), ('general', 'wh_main_brt_bretonnia', 12, 0), "
                    "('general', 'wh_main_dwf_dwarfs', 13, 0), ('wizard', 'wh_main_brt_bretonnia', 14, 0), "
                    "('wizard', 'wh_main_dwf_dwarfs', 15, 0)) t(agent, culture, key, level)")
    ctx.con.execute("CREATE TABLE factions AS SELECT * FROM (VALUES ('reikland', 'sc_empire'), "
                    "('golden_order', 'sc_empire')) t(key, subculture)")
    ctx.con.execute("CREATE TABLE cultures_subcultures AS SELECT * FROM (VALUES ('sc_empire', 'wh_main_emp_empire')) "
                    "t(subculture, culture)")
    built = {c["key"]: c for c in characters.build(ctx)["character"]}
    assert built["kf"]["agent_types"] == [{"key": "general", "name": "General of the Empire"}]
    # No Empire wizard label: Damsel and Runesmith tie, and Bretonnia's culture key sorts first.
    assert built["wizard"]["agent_types"] == [{"key": "wizard", "name": "Damsel"}]
    labels = characters.agent_type_labels(ctx)
    assert characters.agent_type(ctx, labels, "general", None) == {"key": "general", "name": "Lord"}
    assert characters.agent_type(ctx, labels, "spy", None) == {"key": "spy", "name": None}
    assert ctx.tally["unresolved_agent_type_names"] == 1
    schemas.ENTITY_MODELS["character"].model_validate(built["kf"])
