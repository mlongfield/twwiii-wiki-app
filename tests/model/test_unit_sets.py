from twwiki.model.unit_sets import evaluate_membership, resolve_unit_sets
from tests.model.fixtures import make_context

UNITS = [
    {"unit": "gs", "caste": "melee_infantry", "category": "inf_melee", "class": "inf_mel"},
    {"unit": "kf", "caste": "lord", "category": "inf_melee", "class": "com"},
    {"unit": "hag", "caste": "hero", "category": "inf_melee", "class": "com"},
    {"unit": "ship", "caste": "warship", "category": None, "class": None},
]


def rule(unit_set, exclude=False, record="", caste="", category="", cls=""):
    return {"unit_set": unit_set, "exclude": exclude, "unit_record": record,
            "unit_caste": caste, "unit_category": category, "unit_class": cls}


def test_single_filter_rules():
    members = evaluate_membership(UNITS, [
        rule("by_record", record="gs"),
        rule("by_caste", caste="lord"),
        rule("by_category", category="inf_melee"),
        rule("by_class", cls="com"),
    ])
    assert members["by_record"] == {"gs"}
    assert members["by_caste"] == {"kf"}
    assert members["by_category"] == {"gs", "kf", "hag"}
    assert members["by_class"] == {"kf", "hag"}


def test_row_with_two_filters_needs_both():
    members = evaluate_membership(UNITS, [rule("both", record="hag", caste="hero"),
                                          rule("wrong", record="hag", caste="lord")])
    assert members["both"] == {"hag"}
    assert members["wrong"] == set()


def test_exclude_rows_remove_members():
    members = evaluate_membership(UNITS, [
        rule("no_characters", cls="inf_mel"),
        rule("no_characters", cls="com"),
        rule("no_characters", exclude=True, caste="hero"),
        rule("no_characters", exclude=True, caste="lord"),
    ])
    assert members["no_characters"] == {"gs"}


def test_units_without_land_unit_only_match_record_or_caste():
    members = evaluate_membership(UNITS, [rule("naval", caste="warship"), rule("cls", cls="com")])
    assert members["naval"] == {"ship"}
    assert "ship" not in members["cls"]


def test_resolve_unit_sets_marks_conditional_sets():
    ctx = make_context({
        "main_units": [{"unit": "gs", "caste": "melee_infantry", "land_unit": "gs_land"},
                       {"unit": "ship", "caste": "warship", "land_unit": ""}],
        "land_units": [{"key": "gs_land", "category": "inf_melee", "class": "inf_mel"}],
        "unit_sets": [
            {"key": "all_inf", "use_unit_exp_level_range": False, "min_unit_exp_level_inclusive": 0, "max_unit_exp_level_inclusive": 0},
            {"key": "vet_inf", "use_unit_exp_level_range": True, "min_unit_exp_level_inclusive": 3, "max_unit_exp_level_inclusive": 9},
        ],
        "unit_set_to_unit_junctions": [
            {"unit_set": "all_inf", "exclude": False, "unit_record": "", "unit_caste": "", "unit_category": "inf_melee", "unit_class": ""},
            {"unit_set": "vet_inf", "exclude": False, "unit_record": "gs", "unit_caste": "", "unit_category": "", "unit_class": ""},
        ],
    })
    result = resolve_unit_sets(ctx)
    assert result["gs"] == [
        {"key": "all_inf", "conditional": False, "min_exp_level": None, "max_exp_level": None},
        {"key": "vet_inf", "conditional": True, "min_exp_level": 3, "max_exp_level": 9},
    ]
    assert "ship" not in result


def test_resolve_unit_sets_missing_table_is_partial():
    ctx = make_context({"main_units": [{"unit": "gs", "caste": "x", "land_unit": ""}]})
    assert resolve_unit_sets(ctx) == {}
    assert ctx.partial["unit"] == ["land_units", "unit_sets", "unit_set_to_unit_junctions"]
