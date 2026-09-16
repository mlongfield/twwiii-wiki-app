import json
from pathlib import Path

import pytest

from tests.publish.helpers import make_model
from twwiki.publish import PublishError
from twwiki.publish.local_model import ENTITY_TYPES, check_model, find_model_dir, iter_entities, model_files

FIXTURE_MODEL = Path("web/test/fixtures/model")


def test_entity_types_are_the_nineteen_model_types_sorted():
    assert len(ENTITY_TYPES) == 19
    assert list(ENTITY_TYPES) == sorted(ENTITY_TYPES)
    assert "unit" in ENTITY_TYPES and "province" in ENTITY_TYPES


def test_find_model_dir_picks_newest_by_generated_at_and_skips_staging(tmp_path):
    make_model(tmp_path, "old", generated_at="2026-01-01T00:00:00+00:00")
    newest = make_model(tmp_path, "new", generated_at="2026-09-16T00:00:00+00:00")
    make_model(tmp_path, "newer.partial", generated_at="2026-12-01T00:00:00+00:00")
    make_model(tmp_path, "newest.old", generated_at="2026-12-02T00:00:00+00:00")
    (tmp_path / "broken").mkdir()
    assert find_model_dir(tmp_path) == newest


def test_find_model_dir_by_build_id(tmp_path):
    chosen = make_model(tmp_path, "abc")
    make_model(tmp_path, "later", generated_at="2027-01-01T00:00:00+00:00")
    assert find_model_dir(tmp_path, "abc") == chosen
    with pytest.raises(PublishError, match="no model for build nope"):
        find_model_dir(tmp_path, "nope")


def test_find_model_dir_without_models_fails_clearly(tmp_path):
    with pytest.raises(PublishError, match="no model found"):
        find_model_dir(tmp_path / "missing")


def test_check_model_returns_manifest(tmp_path):
    model_dir = make_model(tmp_path, "abc")
    assert check_model(model_dir)["build_id"] == "abc"


def test_check_model_passes_for_the_web_fixture_model():
    assert check_model(FIXTURE_MODEL)["build_id"] == "1eb25ce70f3a"


def test_check_model_rejects_other_model_versions(tmp_path):
    model_dir = make_model(tmp_path, model_version=1)
    with pytest.raises(PublishError, match="model_version 1, expected 2"):
        check_model(model_dir)


def test_check_model_lists_missing_files(tmp_path):
    model_dir = make_model(tmp_path)
    (model_dir / "entities" / "unit.jsonl").unlink()
    (model_dir / "schema" / "region.schema.json").unlink()
    (model_dir / "images" / "inline.json").unlink()
    with pytest.raises(PublishError) as excinfo:
        check_model(model_dir)
    message = str(excinfo.value)
    assert "entities/unit.jsonl" in message
    assert "schema/region.schema.json" in message
    assert "images/inline.json" in message


def test_check_model_without_manifest_fails(tmp_path):
    model_dir = make_model(tmp_path)
    (model_dir / "manifest.json").unlink()
    with pytest.raises(PublishError, match="manifest.json is missing or unreadable"):
        check_model(model_dir)


def test_iter_entities_reads_jsonl_and_skips_blank_lines(tmp_path):
    model_dir = make_model(tmp_path, entities={"unit": [{"key": "a"}, {"key": "b"}]})
    path = model_dir / "entities" / "unit.jsonl"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert [e["key"] for e in iter_entities(model_dir, "unit")] == ["a", "b"]


def test_model_files_are_sorted_posix_paths(tmp_path):
    model_dir = make_model(tmp_path)
    files = model_files(model_dir)
    assert files == sorted(files)
    assert "manifest.json" in files and "images/ui/icon.png" in files and "entities/unit.jsonl" in files
    assert all("\\" not in f for f in files)
    assert json.loads((model_dir / "manifest.json").read_text())["build_id"] == "b1"
