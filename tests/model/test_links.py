from twwiki.model.links import LinkRegistry


def make_registry():
    reg = LinkRegistry()
    reg.register("ability", {"hold": "Hold the Line!", "unnamed": None})
    reg.register("unit", {"gs": "Greatswords", "hb": "Halberdiers"})
    return reg


def test_link_to_known_entity():
    reg = make_registry()
    link = reg.link("ability", "hold", source=("unit", "gs"), relation="abilities")
    assert link == {"type": "ability", "key": "hold", "name": "Hold the Line!", "missing": False}
    assert reg.missing == {}


def test_link_to_known_entity_without_name():
    reg = make_registry()
    assert reg.link("ability", "unnamed", source=("unit", "gs"), relation="abilities")["name"] is None


def test_link_to_unknown_entity_is_marked_and_counted():
    reg = make_registry()
    link = reg.link("ability", "nope", source=("unit", "gs"), relation="abilities")
    assert link == {"type": "ability", "key": "nope", "name": None, "missing": True}
    assert reg.missing["unit.abilities->ability"] == 1


def test_empty_key_gives_no_link():
    reg = make_registry()
    assert reg.link("ability", "", source=("unit", "gs"), relation="abilities") is None
    assert reg.link("ability", None, source=("unit", "gs"), relation="abilities") is None
    assert reg.missing == {}


def test_referrers_are_deduplicated_sorted_and_filtered():
    reg = make_registry()
    reg.register("character", {"kf": "Karl Franz"})
    reg.link("ability", "hold", source=("unit", "hb"), relation="abilities")
    reg.link("ability", "hold", source=("unit", "gs"), relation="abilities")
    reg.link("ability", "hold", source=("unit", "gs"), relation="abilities")
    reg.link("ability", "hold", source=("character", "kf"), relation="abilities")
    reg.link("ability", "hold", source=("unit", "gs"), relation="other")

    assert [l["key"] for l in reg.referrers("ability", "hold", "abilities")] == ["kf", "gs", "hb"]
    assert [l["key"] for l in reg.referrers("ability", "hold", "abilities", source_type="unit")] == ["gs", "hb"]
    assert reg.referrers("ability", "hold", "abilities")[1] == {
        "type": "unit", "key": "gs", "name": "Greatswords", "missing": False}


def test_register_merges_and_keys_lists_registered():
    reg = make_registry()
    reg.register("unit", {"new": None})
    assert sorted(reg.keys("unit")) == ["gs", "hb", "new"]
    assert reg.has("unit", "new") and not reg.has("unit", "zzz")
    assert reg.keys("faction") == []
