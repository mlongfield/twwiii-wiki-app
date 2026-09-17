from twwiki.publish import documents
from twwiki.publish.documents import RESERVED_FIELDS, derived_field_collisions, entity_document, link_fields
from twwiki.publish.local_model import ENTITY_TYPES


def link(key, type_="ability", missing=False):
    return {"type": type_, "key": key, "name": key.title(), "missing": missing}


def test_link_fields_come_from_the_model_schema():
    assert link_fields("unit") == {
        "abilities": "list", "characters": "list", "custom_battle_factions": "list",
        "recruited_by_buildings": "list"}
    assert link_fields("character") == {
        "associated_unit": "one", "factions": "list", "campaigns": "list", "abilities": "list", "items": "list"}
    assert link_fields("item") == {"bodyguard_unit": "one", "agent_subtypes": "list"}
    assert link_fields("campaign_variable") == {}
    assert sum(len(link_fields(t)) for t in ENTITY_TYPES) == 50


def test_no_derived_field_collides_with_the_current_schemas():
    assert {t: derived_field_collisions(t) for t in ENTITY_TYPES} == {t: [] for t in ENTITY_TYPES}


def test_derived_field_collision_is_detected(monkeypatch):
    monkeypatch.setitem(documents.INDEX_FIELDS, "unit", ["abilities_keys"])
    assert derived_field_collisions("unit") == ["abilities_keys"]


def test_reserved_fields():
    assert RESERVED_FIELDS == ("key", "name", "entity")


def test_unit_document_has_browse_fields_link_keys_and_the_entity():
    entity = {
        "key": "wh_main_emp_cha_captain_0", "name": "Empire Captain",
        "caste": "lord", "category": "cha", "unit_class": "com", "tier": 1, "is_naval": False,
        "abilities": [link("hold"), link("charge"), link("hold", missing=True)],
        "characters": [],
        "custom_battle_factions": [link("wh_main_emp_empire", "faction")],
        "recruited_by_buildings": [],
        "base_stats": {"num_men": 1},
    }
    doc = entity_document("unit", entity)
    assert doc == {
        "key": "wh_main_emp_cha_captain_0",
        "name": "Empire Captain",
        "caste": "lord", "category": "cha", "unit_class": "com", "tier": 1, "is_naval": False,
        "abilities_keys": ["hold", "charge"],
        "characters_keys": [],
        "custom_battle_factions_keys": ["wh_main_emp_empire"],
        "recruited_by_buildings_keys": [],
        "entity": entity,
    }


def test_single_links_and_null_links():
    entity = {"key": "k", "name": None, "bodyguard_unit": None,
              "agent_subtypes": [link("a", "character", missing=True)]}
    doc = entity_document("item", entity)
    assert doc["bodyguard_unit_keys"] == [] and doc["agent_subtypes_keys"] == ["a"]
    assert doc["category"] is None and doc["legendary"] is None
    doc = entity_document("item", {**entity, "bodyguard_unit": link("u", "unit")})
    assert doc["bodyguard_unit_keys"] == ["u"]


def test_types_without_links_or_browse_fields():
    entity = {"key": "v", "name": "Variable", "value": 3}
    assert entity_document("faction", {"key": "f", "name": "F", "subculture": None, "culture": None,
                                       "units": [], "characters": []}) == {
        "key": "f", "name": "F", "subculture_keys": [], "culture_keys": [], "units_keys": [],
        "characters_keys": [], "start_campaigns_keys": [], "playable_in_keys": [], "major_in_keys": [],
        "entity": {"key": "f", "name": "F", "subculture": None, "culture": None, "units": [], "characters": []}}
    assert entity_document("campaign_variable", entity) == {"key": "v", "name": "Variable", "value": 3,
                                                            "entity": entity}
