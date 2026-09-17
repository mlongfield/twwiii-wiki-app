import pytest

from twwiki.model.text import LocResolver, loc_prefix, round_float, split_title_body


def test_raw_returns_none_for_missing_or_empty():
    loc = LocResolver({"a": "", "b": "Bee"})
    assert loc.raw("a") is None
    assert loc.raw("missing") is None
    assert loc.raw("b") == "Bee"


def test_placeholder_text_counts_as_missing_and_is_recorded_once_per_key():
    loc = LocResolver({
        "building_chains_encyclopedia_name_a": "placeholder",
        "building_chains_encyclopedia_name_b": "  PlaceHolder ",
        "cultures_name_*": "%PLACEHOLDER%",
        "cultures_name_x": "Real",
    })
    assert loc.text("building_chains_encyclopedia_name_a") is None
    assert loc.text("building_chains_encyclopedia_name_a") is None
    assert loc.raw("building_chains_encyclopedia_name_b") is None
    assert loc.text("cultures_name_*") is None
    assert loc.text("cultures_name_x") == "Real"
    assert loc.text_report()["placeholders_by_prefix"] == {"building_chains_encyclopedia": 2, "cultures_name_*": 1}


def test_loc_prefix_is_first_three_words():
    assert loc_prefix("building_chains_encyclopedia_name_wh_main_x") == "building_chains_encyclopedia"
    assert loc_prefix("p") == "p"


def test_text_substitutes_ui_text_replacement():
    loc = LocResolver({
        "effects_description_x": "{{tr:effect_technology_research_points_description}}: %+n",
        "ui_text_replacements_localised_text_effect_technology_research_points_description": "Research rate",
    })
    assert loc.text("effects_description_x") == "Research rate: %+n"
    assert loc.unresolved_targets == set()


def test_exact_key_wins_over_prefixed_key():
    loc = LocResolver({
        "s": "{{tr:rank7}}",
        "rank7": "exact",
        "ui_text_replacements_localised_text_rank7": "prefixed",
    })
    assert loc.text("s") == "exact"


def test_nested_tokens_resolve_up_to_depth():
    loc = LocResolver({"s": "{{tr:a}}", "a": "{{tr:b}}!", "b": "done"})
    assert loc.text("s") == "done!"


def test_unresolved_tr_token_is_dropped_and_recorded():
    loc = LocResolver({"s": "Pay {{tr:nothing_here}} now"})
    assert loc.text("s") == "Pay  now"
    assert loc.unresolved_targets == {"nothing_here"}
    assert loc.text_report()["dropped_tr_tokens"] == 1


def test_self_referencing_token_is_dropped_after_max_depth():
    loc = LocResolver({"s": "a{{tr:loop}}b", "loop": "{{tr:loop}}"})
    assert loc.text("s") == "ab"
    assert loc.unresolved_targets == {"loop"}


def test_tooltip_and_cco_tokens_are_dropped_and_markup_is_kept():
    loc = LocResolver({"s": "[[tooltip:{{tt:x}}]]word[[/tooltip]] {{CcoCampaignFaction:Name}}! [[col:red]]%n[[/col]]"})
    assert loc.text("s") == "[[tooltip:]]word[[/tooltip]] ! [[col:red]]%n[[/col]]"
    assert loc.text_report() == {"placeholders_by_prefix": {}, "dropped_tt_tokens": 1,
                                 "dropped_cco_tokens": 1, "dropped_tr_tokens": 0}


@pytest.mark.parametrize("text, expected", [
    ("Just a body", (None, "Just a body")),
    ("Title||Body", ("Title", "Body")),
    (" Title || Body||more ", ("Title", "Body||more")),
    ("||Body", (None, "Body")),
    ("Title||", ("Title", None)),
    ("[[col:yellow]]Rampage[[/col]]||[[b]]Charges[[/b]]", ("[[col:yellow]]Rampage[[/col]]", "[[b]]Charges[[/b]]")),
    (None, (None, None)),
])
def test_split_title_body(text, expected):
    assert split_title_body(text) == expected


@pytest.mark.parametrize("value, expected", [
    (0.90000004, 0.9), (1.0000001, 1.0), (-0.30000001, -0.3), (3.0, 3.0), (123456789.0, 123456789.0), (1e-7, 1e-7),
])
def test_round_float(value, expected):
    assert round_float(value) == expected
