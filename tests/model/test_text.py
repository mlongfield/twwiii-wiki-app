from twwiki.model.text import LocResolver


def test_raw_returns_none_for_missing_or_empty():
    loc = LocResolver({"a": "", "b": "Bee"})
    assert loc.raw("a") is None
    assert loc.raw("missing") is None
    assert loc.raw("b") == "Bee"


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


def test_unresolved_token_is_kept_and_recorded():
    loc = LocResolver({"s": "Pay {{tr:nothing_here}} now"})
    assert loc.text("s") == "Pay {{tr:nothing_here}} now"
    assert loc.unresolved_targets == {"nothing_here"}


def test_self_referencing_token_stops_after_max_depth():
    loc = LocResolver({"s": "{{tr:loop}}", "loop": "{{tr:loop}}"})
    assert loc.text("s") == "{{tr:loop}}"


def test_markup_and_context_tokens_are_untouched():
    text = "[[col:red]]%n[[/col]] {{tt:tip}} {{CcoCampaignFaction:x}}"
    loc = LocResolver({"s": text})
    assert loc.text("s") == text
    assert loc.unresolved_targets == set()
