import json

import pytest

from tests.publish.fakes import FakeEntityStore
from tests.publish.helpers import make_model
from twwiki.publish import PublishError
from twwiki.publish.firestore_writer import (
    CURRENT, build_path, collection_path, go_live, prune, verify_counts, write_entities)
from twwiki.publish.local_model import ENTITY_TYPES

UNITS = [
    {"key": "u1", "name": "Unit One", "caste": "melee", "category": "inf", "unit_class": "inf_mel",
     "tier": 1, "is_naval": False, "characters": [], "custom_battle_factions": [],
     "recruited_by_buildings": [],
     "abilities": [{"type": "ability", "key": "hold", "name": "Hold", "missing": False}]},
    {"key": "u2", "name": "Unit Two", "caste": "melee", "category": "inf", "unit_class": "inf_mel",
     "tier": 2, "is_naval": False, "abilities": [], "characters": [], "custom_battle_factions": [],
     "recruited_by_buildings": []},
]


def manifest_of(model_dir):
    return json.loads((model_dir / "manifest.json").read_text(encoding="utf-8"))


def test_paths():
    assert CURRENT == "site/current"
    assert build_path("b1") == "builds/b1"
    assert collection_path("b1", "unit") == "builds/b1/unit"


def test_write_entities_marks_loading_first_then_writes_every_type(tmp_path):
    model_dir = make_model(tmp_path, "b1", entities={"unit": UNITS})
    store = FakeEntityStore()
    written = write_entities(store, model_dir, "b1", manifest_of(model_dir))

    assert written == {t: (2 if t == "unit" else 0) for t in ENTITY_TYPES}
    first_bulk = next(i for i, call in enumerate(store.calls) if call[0] == "bulk_set")
    assert ("set", "builds/b1") in store.calls[:first_bulk]
    assert [c[1] for c in store.calls if c[0] == "bulk_set"] == [f"builds/b1/{t}" for t in ENTITY_TYPES]
    build = store.docs["builds/b1"]
    assert build["status"] == "loading" and build["published_at"] is None
    assert build["counts"]["unit"] == 2 and build["model_version"] == 2
    doc = store.docs["builds/b1/unit/u1"]
    assert doc["abilities_keys"] == ["hold"] and doc["tier"] == 1 and doc["entity"] == UNITS[0]


def test_write_entities_keeps_published_at_and_deletes_stale_documents(tmp_path):
    model_dir = make_model(tmp_path, "b1", entities={"unit": UNITS})
    store = FakeEntityStore()
    store.docs["builds/b1"] = {"status": "ready", "published_at": "2026-09-01T00:00:00+00:00"}
    store.docs["builds/b1/unit/gone"] = {"key": "gone"}
    store.docs["builds/b0/unit/gone"] = {"key": "gone"}

    write_entities(store, model_dir, "b1", manifest_of(model_dir))

    assert store.docs["builds/b1"]["published_at"] == "2026-09-01T00:00:00+00:00"
    assert store.docs["builds/b1"]["status"] == "loading"
    assert "builds/b1/unit/gone" not in store.docs
    assert "builds/b0/unit/gone" in store.docs
    assert ("bulk_delete", "builds/b1/unit") in store.calls
    assert ("bulk_delete", "builds/b1/skill") not in store.calls


def test_write_failure_propagates(tmp_path):
    model_dir = make_model(tmp_path, "b1", entities={"unit": UNITS})
    store = FakeEntityStore()
    store.fail_bulk_set_on = "builds/b1/unit"
    with pytest.raises(PublishError, match="writes to builds/b1/unit failed"):
        write_entities(store, model_dir, "b1", manifest_of(model_dir))


def test_verify_counts_passes_and_lists_mismatches(tmp_path):
    model_dir = make_model(tmp_path, "b1", entities={"unit": UNITS})
    store = FakeEntityStore()
    manifest = manifest_of(model_dir)
    write_entities(store, model_dir, "b1", manifest)
    verify_counts(store, "b1", manifest["counts"])

    store.count_override["builds/b1/unit"] = 1
    store.count_override["builds/b1/skill"] = 3
    with pytest.raises(PublishError) as excinfo:
        verify_counts(store, "b1", manifest["counts"])
    assert "skill 3 (expected 0)" in str(excinfo.value)
    assert "unit 1 (expected 2)" in str(excinfo.value)


def test_go_live_first_publish(tmp_path):
    store = FakeEntityStore()
    manifest = {"build_id": "b1", "model_version": 2, "generated_at": "g", "counts": {"unit": 2}}
    go_live(store, "b1", manifest, "2026-09-16T12:00:00+00:00")
    assert store.docs["builds/b1"] == {"status": "ready", "model_version": 2, "generated_at": "g",
                                       "published_at": "2026-09-16T12:00:00+00:00", "counts": {"unit": 2}}
    assert store.docs[CURRENT] == {"build_id": "b1", "previous_build_id": None, "model_version": 2,
                                   "published_at": "2026-09-16T12:00:00+00:00"}


def test_go_live_new_build_records_previous_and_republish_keeps_it():
    store = FakeEntityStore()
    manifest = {"model_version": 2, "generated_at": "g", "counts": {}}
    go_live(store, "b1", manifest, "t1")
    go_live(store, "b2", manifest, "t2")
    assert store.docs[CURRENT]["build_id"] == "b2" and store.docs[CURRENT]["previous_build_id"] == "b1"
    go_live(store, "b2", manifest, "t3")
    assert store.docs[CURRENT]["previous_build_id"] == "b1"
    assert store.docs[CURRENT]["published_at"] == "t3"


def test_prune_refuses_current_and_previous_and_deletes_older_builds():
    store = FakeEntityStore()
    store.docs[CURRENT] = {"build_id": "b3", "previous_build_id": "b2"}
    for build in ("b1", "b2", "b3"):
        store.docs[f"builds/{build}"] = {"status": "ready"}
        store.docs[f"builds/{build}/unit/u1"] = {"key": "u1"}

    for protected in ("b3", "b2"):
        with pytest.raises(PublishError, match=f"refusing to prune {protected}"):
            prune(store, protected)
    with pytest.raises(PublishError, match="no build b9"):
        prune(store, "b9")

    prune(store, "b1")
    assert "builds/b1" not in store.docs and "builds/b1/unit/u1" not in store.docs
    assert "builds/b2/unit/u1" in store.docs and "builds/b3" in store.docs
    assert ("delete_tree", "builds/b1") in store.calls
