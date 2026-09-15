import json
from types import SimpleNamespace

import pytest

from twwiki.model import build
from tests.model.fixtures import make_context


def fake_faction(ctx, **overrides):
    faction = {"key": "reikland", "name": "Reikland", "adjective": None, "subculture": None,
               "culture": ctx.links.link("culture", "empire", source=("faction", "reikland"), relation="culture"),
               "category": None, "is_rebel": False, "is_quest_faction": False, "flags_path": "flags/reikland",
               "primary_colour": None, "units": [], "characters": []}
    faction.update(overrides)
    return faction


def fake_module(**faction_overrides):
    return SimpleNamespace(
        catalog=lambda ctx: {"culture": {"empire": "The Empire"}, "faction": {"reikland": "Reikland"}},
        build=lambda ctx: {
            "culture": [{"key": "empire", "name": "The Empire", "subcultures": [], "factions": []}],
            "faction": [fake_faction(ctx, **faction_overrides)],
        },
    )


def test_build_all_fills_reverse_links_and_validates():
    ctx = make_context({"dummy": [{"a": 1}]})
    entities = build.build_all(ctx, modules=[fake_module()])
    assert entities["culture"][0]["factions"] == [
        {"type": "faction", "key": "reikland", "name": "Reikland", "missing": False}]
    assert entities["faction"][0]["culture"]["name"] == "The Empire"


def test_build_all_reports_invalid_entity():
    ctx = make_context({"dummy": [{"a": 1}]})
    with pytest.raises(build.ModelBuildError, match="faction reikland"):
        build.build_all(ctx, modules=[fake_module(is_rebel="not a bool")])


def test_write_output_layout_and_manifest(tmp_path):
    ctx = make_context({"dummy": [{"a": 1}]}, loc={"s": "{{tr:nowhere}}"})
    ctx.loc.text("s")
    ctx.partial["unit"] = ["land_units"]
    entities = build.build_all(ctx, modules=[fake_module()])
    (tmp_path / "abc123.partial").mkdir()
    (tmp_path / "abc123.partial" / "stale.txt").write_text("old")

    out = build.write_output(ctx, entities, tmp_path, "abc123")

    assert out == tmp_path / "abc123" and not (tmp_path / "abc123.partial").exists()
    lines = (out / "entities" / "faction.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0])["key"] == "reikland"
    assert json.loads((out / "index" / "culture.json").read_text(encoding="utf-8")) == [
        {"key": "empire", "name": "The Empire"}]
    assert (out / "schema" / "unit.schema.json").exists()
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["build_id"] == "abc123" and manifest["model_version"] == build.MODEL_VERSION
    assert manifest["counts"] == {"culture": 1, "faction": 1}
    assert manifest["unresolved_text_targets"] == 1
    assert manifest["partial"] == {"unit": ["land_units"]}
    assert not (out / "stale.txt").exists()


def test_write_output_replaces_previous_model(tmp_path):
    ctx = make_context({"dummy": [{"a": 1}]})
    entities = build.build_all(ctx, modules=[fake_module()])
    (tmp_path / "abc123").mkdir()
    (tmp_path / "abc123" / "old.json").write_text("{}")
    out = build.write_output(ctx, entities, tmp_path, "abc123")
    assert not (out / "old.json").exists() and (out / "manifest.json").exists()
