import json
from pathlib import Path

from twwiki.publish.indexes import INDEXES_FILE, generate_indexes, render_indexes, write_indexes
from twwiki.publish.local_model import ENTITY_TYPES

ROOT = Path(__file__).resolve().parents[2]


def test_indexes_exempt_entity_in_every_collection_and_add_no_composites():
    indexes = generate_indexes()
    assert indexes["indexes"] == []
    assert indexes["fieldOverrides"] == [
        {"collectionGroup": t, "fieldPath": "entity", "indexes": []} for t in ENTITY_TYPES]
    assert len(indexes["fieldOverrides"]) == 19


def test_render_is_stable_json_with_trailing_newline():
    text = render_indexes()
    assert text.endswith("}\n")
    assert json.loads(text) == generate_indexes()


def test_write_indexes(tmp_path):
    path = write_indexes(tmp_path / "idx.json")
    assert json.loads(path.read_text(encoding="utf-8")) == generate_indexes()


def test_committed_indexes_file_is_up_to_date():
    assert INDEXES_FILE == ROOT / "firestore.indexes.json"
    committed = json.loads(INDEXES_FILE.read_text(encoding="utf-8"))
    assert committed == generate_indexes(), "run `uv run python -m twwiki.publish --write-indexes`"


def test_firebase_json_hosting_and_rule_files():
    config = json.loads((ROOT / "firebase.json").read_text(encoding="utf-8"))
    hosting = config["hosting"]
    assert hosting["public"] == "web/dist"
    assert hosting["trailingSlash"] is True
    cache = {h["source"]: h["headers"][0]["value"] for h in hosting["headers"]}
    assert cache == {
        "/_astro/**": "public, max-age=31536000, immutable",
        "/images/**": "public, max-age=86400",
        "/search-index.json": "public, max-age=300",
        "/data/**": "public, max-age=300",
    }
    assert config["firestore"] == {"rules": "firestore.rules", "indexes": "firestore.indexes.json"}
    assert config["storage"] == {"rules": "storage.rules"}
    for name in ("firestore.rules", "firestore.indexes.json", "storage.rules"):
        assert (ROOT / name).is_file()
    assert config["emulators"]["firestore"]["port"] == 8080
    assert config["emulators"]["storage"]["port"] == 9199


def test_firebaserc_default_project():
    assert json.loads((ROOT / ".firebaserc").read_text(encoding="utf-8")) == {
        "projects": {"default": "twwiii-wiki"}}


def test_rules_never_allow_browser_writes():
    firestore_rules = (ROOT / "firestore.rules").read_text(encoding="utf-8")
    storage_rules = (ROOT / "storage.rules").read_text(encoding="utf-8")
    assert "if true" not in storage_rules
    assert "allow write: if true" not in firestore_rules
    assert "allow read, write: if true" not in firestore_rules
