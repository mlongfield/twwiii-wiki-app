import json
from types import SimpleNamespace

import pytest

from twwiki.model import build, schemas
from tests.model.fixtures import make_context


def fake_faction(ctx, **overrides):
    faction = {"key": "reikland", "name": "Reikland", "adjective": None, "subculture": None,
               "culture": ctx.links.link("culture", "empire", source=("faction", "reikland"), relation="culture"),
               "category": None, "is_rebel": False, "is_quest_faction": False, "flags_path": "flags/reikland",
               "primary_colour": None, "flag_image": None, "units": [], "characters": []}
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


def test_write_output_cleans_up_stale_old_directory(tmp_path):
    ctx = make_context({"dummy": [{"a": 1}]})
    entities = build.build_all(ctx, modules=[fake_module()])
    (tmp_path / "abc123").mkdir()
    (tmp_path / "abc123" / "old.json").write_text("{}")
    (tmp_path / "abc123.old").mkdir()
    (tmp_path / "abc123.old" / "stale_from_a_previous_failed_build.json").write_text("{}")

    out = build.write_output(ctx, entities, tmp_path, "abc123")

    assert not (out / "old.json").exists() and (out / "manifest.json").exists()
    assert not (tmp_path / "abc123.old").exists()


def test_write_output_includes_manifest_sections(tmp_path):
    ctx = make_context({"dummy": [{"a": 1}]})
    ctx.manifest_sections["regions"] = {"special_templates_unmatched": 2}
    entities = build.build_all(ctx, modules=[fake_module()])
    out = build.write_output(ctx, entities, tmp_path, "abc123")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["regions"] == {"special_templates_unmatched": 2}


def test_schema_marks_reverse_links_and_conditional_fields_required():
    ability_schema = schemas.ENTITY_MODELS["ability"].model_json_schema(mode="serialization")
    assert "units" in ability_schema["required"]
    assert "characters" in ability_schema["required"]
    assert "modified_by_effects" in ability_schema["required"]

    bundle_schema = schemas.ENTITY_MODELS["effect_bundle"].model_json_schema(mode="serialization")
    app_schema = bundle_schema["$defs"]["EffectApplication"]
    assert "value_damaged" in app_schema["required"]
