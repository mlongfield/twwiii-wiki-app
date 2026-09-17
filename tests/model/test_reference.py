import pytest

from twwiki.model import reference
from tests.model.fixtures import make_context


@pytest.mark.parametrize("value, expected", [
    ("#999999", "#999999"),   # lightness exactly 60%: unchanged
    ("#989898", "#999999"),   # just under 60%: raised
    ("#000080", "#3333FF"),   # navy: same hue and saturation, lightness 60%
    ("#41E1E1", "#41E1E1"),   # already light
])
def test_dark_hex_raises_lightness_to_sixty_percent(value, expected):
    assert reference.dark_hex(value) == expected


def test_build_reference_documents():
    ctx = make_context({
        "ui_colours": [
            {"key": "magic", "description": "Magic text", "unnamed colour group_1": "41e1e1"},
            {"key": "dark_red", "description": "", "unnamed colour group_1": "800000"},
            {"key": "blank", "description": "No colour", "unnamed colour group_1": ""},
        ],
        "ui_colour_profile_colour_overrides": [
            {"colour": "magic", "colour_profile": "deuteranopia", "colour_hex": "364099"},
        ],
    }, loc={
        reference.UI_LABEL_KEYS["duration"]: "Duration:",
        reference.UI_LABEL_KEYS["effects"]: " Effects ",
    })
    campaign = {"key": "wh3_main_combi", "name": "Immortal Empires", "map": "wh3_main_combi_map_5",
                "script_folder": None, "factions": [], "regions": [],
                "playable_factions": [{"type": "faction", "key": "a", "name": None, "missing": False}],
                "major_factions": []}
    docs = reference.build_reference(ctx, {"campaign": [campaign]})

    assert docs["campaigns"] == [{"key": "wh3_main_combi", "name": "Immortal Empires", "map": "wh3_main_combi_map_5",
                                  "playable_factions": 1, "major_factions": 0}]
    assert docs["colours"] == [
        {"key": "dark_red", "description": "", "hex": "#800000", "dark_hex": "#FF3333",
         "profiles": {"deuteranopia": None, "protanopia": None, "tritanopia": None}},
        {"key": "magic", "description": "Magic text", "hex": "#41E1E1", "dark_hex": "#41E1E1",
         "profiles": {"deuteranopia": "#364099", "protanopia": None, "tritanopia": None}},
    ]
    assert docs["ui_labels"]["duration"] == "Duration" and docs["ui_labels"]["effects"] == "Effects"
    assert docs["ui_labels"]["cooldown"] is None
    assert set(docs["ui_labels"]) == set(reference.UI_LABEL_KEYS)
    assert ctx.tally["ui_labels_without_text"] == len(reference.UI_LABEL_KEYS) - 2


def test_reference_documents_are_empty_without_tables():
    ctx = make_context({"dummy": [{"a": 1}]})
    docs = reference.build_reference(ctx, {})
    assert docs["campaigns"] == [] and docs["colours"] == []
