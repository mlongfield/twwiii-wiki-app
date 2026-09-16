from pathlib import Path

from twwiki.model.images import ImageIndex, inline_targets, normalise
from tests.model.fixtures import make_context

PATHS = [
    "ui/battle ui/ability_icons/hold.png",
    "ui/campaign ui/skills/leader.png",
    "ui/campaign ui/effect_bundles/resource_grain.png",
    "ui/skins/default/icon_turns.png",
    "ui/skins/default/dlc25_nemesis_crown/icon_turns.png",
    "ui/skins/other/icon_unique.png",
    "ui/units/icons/sub/dup.png",
    "ui/skins/default/dup.png",
]


def index():
    return ImageIndex(Path("images"), PATHS)


def test_normalise_lowercases_and_uses_forward_slashes():
    assert normalise(" UI\\Campaign UI\\\\Skills\\X.PNG ") == "ui/campaign ui/skills/x.png"


def test_resolves_full_path_with_backslashes():
    images = index()
    assert images.resolve("resource", "ui\\campaign ui\\effect_bundles\\resource_grain.png") == \
        "ui/campaign ui/effect_bundles/resource_grain.png"


def test_resolves_bare_name_in_folder_adding_png():
    images = index()
    assert images.resolve("ability.icon_image", "hold", ("ui/battle ui/ability_icons",)) == \
        "ui/battle ui/ability_icons/hold.png"
    assert images.resolve("skill.icon_image", "leader.png", ("ui/campaign ui/skills",)) == \
        "ui/campaign ui/skills/leader.png"


def test_folder_match_wins_over_ambiguous_file_name():
    assert index().resolve("inline", "icon_turns", ("ui/skins/default",)) == "ui/skins/default/icon_turns.png"


def test_falls_back_to_unique_file_name():
    assert index().resolve("inline", "icon_unique", ("ui/skins/default",)) == "ui/skins/other/icon_unique.png"


def test_ambiguous_and_missing_are_null_and_counted():
    images = index()
    assert images.resolve("f", "dup") is None
    assert images.resolve("f", "nope.png") is None
    assert images.resolve("f", "hold", ("ui/battle ui/ability_icons",)) is not None
    assert dict(images.stats["f"]) == {"referenced": 3, "ambiguous": 1, "missing": 1, "resolved": 1}
    assert images.used == {"ui/battle ui/ability_icons/hold.png"}


def test_empty_values_are_not_counted():
    images = index()
    assert images.resolve("g", "") is None and images.resolve("g", None) is None
    assert "g" not in images.stats


def test_unavailable_index_resolves_nothing_and_counts_nothing():
    images = ImageIndex.unavailable()
    assert images.available is False
    assert images.resolve("f", "ui/skins/default/dup.png") is None
    assert images.stats == {} and images.used == set()


def test_scan_copy_and_manifest(tmp_path):
    raw = tmp_path / "raw"
    for rel in ["ui/units/icons/gs.png", "ui/units/icons/unused.png"]:
        (raw / rel).parent.mkdir(parents=True, exist_ok=True)
        (raw / rel).write_bytes(b"png")
    assert ImageIndex.scan(tmp_path / "absent").available is False

    images = ImageIndex.scan(raw)
    assert images.available is True
    assert images.resolve("unit.card_image", "gs", ("ui/units/icons",)) == "ui/units/icons/gs.png"
    dest = tmp_path / "out"
    assert images.copy_used(dest) == 1
    assert (dest / "ui/units/icons/gs.png").read_bytes() == b"png"
    assert not (dest / "ui/units/icons/unused.png").exists()
    assert images.manifest(1) == {"available": True, "files_copied": 1, "fields": {
        "unit.card_image": {"referenced": 1, "resolved": 1, "missing": 0, "ambiguous": 0}}}


def test_inline_targets_collects_distinct_sorted_targets_from_nested_values():
    entities = {"unit": [{"key": "a", "description": "[[img:icon_b]] x [[img:icon_a]]",
                          "levels": [{"text": "[[img:icon_b]]"}], "n": 3}],
                "skill": [{"key": "b", "description": None}]}
    assert inline_targets(entities) == ["icon_a", "icon_b"]


def test_context_images_default_to_unavailable():
    assert make_context({"t": [{"a": 1}]}).images.available is False
