import json
from types import SimpleNamespace

import duckdb
import pytest

from twwiki.model import build, schemas
from twwiki.model.images import ImageIndex
from tests.model.fixtures import make_context


def fake_faction(ctx, **overrides):
    faction = {"key": "reikland", "name": "Reikland", "adjective": None, "subculture": None,
               "culture": ctx.links.link("culture", "empire", source=("faction", "reikland"), relation="culture"),
               "category": None, "is_rebel": False, "is_quest_faction": False, "flags_path": "flags/reikland",
               "primary_colour": None, "flag_image": None, "start_campaigns": [], "playable_in": [], "major_in": [],
               "units": [], "characters": []}
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


def test_write_output_writes_link_report_for_tables_read(tmp_path):
    ctx = make_context({"units": [{"ability": "hold"}, {"ability": "gone"}], "abilities": [{"key": "hold"}]})
    ctx.con.execute("""CREATE TABLE _columns AS SELECT 'units' AS table_name, 0 AS position,
                       'ability' AS column_name, 'StringU8' AS rpfm_type, false AS is_key,
                       'abilities' AS ref_table, 'key' AS ref_column""")
    ctx.rows("SELECT * FROM units JOIN abilities ON true")
    entities = build.build_all(ctx, modules=[fake_module()])

    out = build.write_output(ctx, entities, tmp_path, "abc123")

    report = json.loads((out / "link_report.json").read_text(encoding="utf-8"))
    assert report["summary"]["both_read"] == 1 and report["summary"]["with_broken_values"] == 1
    assert report["references"][0]["examples"] == ["gone"]


def test_write_output_without_column_metadata_writes_unavailable_link_report(tmp_path):
    ctx = make_context({"dummy": [{"a": 1}]})
    entities = build.build_all(ctx, modules=[fake_module()])
    out = build.write_output(ctx, entities, tmp_path, "abc123")
    assert json.loads((out / "link_report.json").read_text(encoding="utf-8"))["available"] is False


def test_schema_marks_reverse_links_and_conditional_fields_required():
    ability_schema = schemas.ENTITY_MODELS["ability"].model_json_schema(mode="serialization")
    assert "units" in ability_schema["required"]
    assert "characters" in ability_schema["required"]
    assert "modified_by_effects" in ability_schema["required"]

    bundle_schema = schemas.ENTITY_MODELS["effect_bundle"].model_json_schema(mode="serialization")
    app_schema = bundle_schema["$defs"]["EffectApplication"]
    assert "value_damaged" in app_schema["required"]


def write_images(root, *paths):
    for rel in paths:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(b"png")


def test_write_output_copies_used_images_and_writes_inline_map(tmp_path):
    raw = tmp_path / "raw_images"
    write_images(raw, "ui/units/icons/gs.png", "ui/units/icons/unused.png", "ui/skins/default/icon_agent_small.png",
                 "ui/battle ui/ability_icons/causes_fear.png")
    ctx = make_context({"dummy": [{"a": 1}], "ui_tagged_images": [
        {"key": "icon_hero", "image_path": "UI\\Skins\\default\\icon_agent_small.png"}]})
    ctx.images = ImageIndex.scan(raw)
    assert ctx.images.resolve("unit.card_image", "gs", ("ui/units/icons",)) == "ui/units/icons/gs.png"
    entities = build.build_all(ctx, modules=[fake_module(
        flags_path="[[img:icon_hero]] [[img:icon_gone]] [[img:ui/Battle UI/ability_icons/causes_fear.png]]")])

    out = build.write_output(ctx, entities, tmp_path / "model", "abc123")

    assert (out / "images" / "ui/units/icons/gs.png").read_bytes() == b"png"
    assert (out / "images" / "ui/skins/default/icon_agent_small.png").exists()
    assert not (out / "images" / "ui/units/icons/unused.png").exists()
    assert json.loads((out / "images" / "inline.json").read_text(encoding="utf-8")) == {
        "icon_gone": None,
        "icon_hero": "ui/skins/default/icon_agent_small.png",
        "ui/Battle UI/ability_icons/causes_fear.png": "ui/battle ui/ability_icons/causes_fear.png",
    }
    images = json.loads((out / "manifest.json").read_text(encoding="utf-8"))["images"]
    assert images["available"] is True and images["files_copied"] == 3
    assert images["fields"]["unit.card_image"] == {"referenced": 1, "resolved": 1, "missing": 0, "ambiguous": 0}
    assert images["fields"]["inline"] == {"referenced": 3, "resolved": 2, "missing": 1, "ambiguous": 0}


def test_write_output_without_images_marks_them_unavailable(tmp_path):
    ctx = make_context({"dummy": [{"a": 1}]})
    entities = build.build_all(ctx, modules=[fake_module(flags_path="[[img:icon_hero]]")])
    out = build.write_output(ctx, entities, tmp_path, "abc123")
    assert json.loads((out / "images" / "inline.json").read_text(encoding="utf-8")) == {"icon_hero": None}
    assert json.loads((out / "manifest.json").read_text(encoding="utf-8"))["images"] == {
        "available": False, "files_copied": 0, "fields": {}}


def test_image_copy_failure_fails_the_build_and_publishes_nothing(tmp_path):
    raw = tmp_path / "raw_images"
    write_images(raw, "ui/units/icons/gs.png")
    ctx = make_context({"dummy": [{"a": 1}]})
    ctx.images = ImageIndex.scan(raw)
    ctx.images.resolve("unit.card_image", "ui/units/icons/gs.png")
    (raw / "ui/units/icons/gs.png").unlink()
    entities = build.build_all(ctx, modules=[fake_module()])
    with pytest.raises(OSError):
        build.write_output(ctx, entities, tmp_path / "model", "abc123")
    assert not (tmp_path / "model" / "abc123").exists()


def test_run_reads_images_from_the_raw_build(tmp_path):
    db = tmp_path / "t.duckdb"
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE loc (key VARCHAR, text VARCHAR)")
    con.execute("CREATE TABLE _build AS SELECT 'abc123' AS build_id")
    con.close()
    write_images(tmp_path / "raw" / "abc123" / "images", "ui/skins/default/x.png")

    out = build.run(db, tmp_path / "model", tmp_path / "raw")

    assert out == tmp_path / "model" / "abc123"
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["images"]["available"] is True and manifest["model_version"] == build.MODEL_VERSION


def test_round_floats_rounds_nested_floats_only():
    data = {"a": 0.90000004, "b": [1.0000001, {"c": 2}], "d": True, "e": "0.90000004", "f": None}
    assert build.round_floats(data) == {"a": 0.9, "b": [1.0, {"c": 2}], "d": True, "e": "0.90000004", "f": None}
    assert type(build.round_floats({"c": 2})["c"]) is int


def test_write_output_rounds_floats_and_reports_text_and_quality_counts(tmp_path):
    ctx = make_context({"dummy": [{"a": 1}]}, loc={"s": "{{tt:x}} text", "p": "placeholder"})
    ctx.loc.text("s")
    ctx.loc.text("p")
    ctx.tally["unmatched_rarity_scores"] = 2
    module = SimpleNamespace(
        catalog=lambda ctx: {"campaign_variable": {"v": "v"}, "culture": {"nameless": None}},
        build=lambda ctx: {
            "campaign_variable": [{"key": "v", "value": 0.90000004, "overrides": []}],
            "culture": [{"key": "nameless", "name": None, "subcultures": [], "factions": []}],
        },
    )
    out = build.write_output(ctx, build.build_all(ctx, modules=[module]), tmp_path, "abc123")

    row = json.loads((out / "entities" / "campaign_variable.jsonl").read_text(encoding="utf-8"))
    assert row["value"] == 0.9
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["model_version"] == 3
    assert manifest["text"] == {"placeholders_by_prefix": {"p": 1}, "dropped_tt_tokens": 1,
                                "dropped_cco_tokens": 0, "dropped_tr_tokens": 0}
    assert manifest["unnamed_by_type"] == {"culture": 1}
    assert manifest["unmatched_rarity_scores"] == 2
    assert all(isinstance(manifest[name], int) for name in build.QUALITY_COUNTS)


def test_write_output_writes_reference_documents(tmp_path):
    ctx = make_context({"dummy": [{"a": 1}]})
    out = build.write_output(ctx, build.build_all(ctx, modules=[fake_module()]), tmp_path, "abc123")
    for name in ("campaigns", "colours", "ui_labels"):
        assert (out / "reference" / f"{name}.json").exists()
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["reference"] == {"campaigns": 0, "colours": 0, "ui_labels": 8}
    assert manifest["ui_labels_without_text"] == 8
