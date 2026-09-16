"""Publish against the Firebase emulators. Optional; skipped unless they run.

From the repository root (needs Java 21 or newer):

    npx --yes firebase-tools@15.30.1 emulators:exec --project demo-twwiki --only firestore,storage "uv run pytest tests/publish/test_emulator.py -q"
"""

import json
import os
import shutil
from pathlib import Path

import pytest

from tests.publish.fakes import FakePost
from twwiki.publish import PublishError
from twwiki.publish.firestore_writer import prune
from twwiki.publish.local_model import ENTITY_TYPES
from twwiki.publish.pipeline import Services, Settings, publish
from twwiki.publish.snapshot import upload_snapshot

pytestmark = pytest.mark.skipif(
    not (os.getenv("FIRESTORE_EMULATOR_HOST") and os.getenv("STORAGE_EMULATOR_HOST")),
    reason="Firebase emulators are not running; see this module's docstring")

PROJECT = "demo-twwiki"
BUCKET = "demo-twwiki.appspot.com"
FIXTURE = Path("web/test/fixtures/model")
BUILD = "1eb25ce70f3a"


def settings(root: Path) -> Settings:
    return Settings(PROJECT, BUCKET, "o/r", "deploy.yml", "main", root)


@pytest.fixture
def model_root(tmp_path):
    shutil.copytree(FIXTURE, tmp_path / BUILD)
    return tmp_path


@pytest.fixture
def services():
    from google.api_core.exceptions import GoogleAPIError
    from google.auth.credentials import AnonymousCredentials
    from google.cloud import storage

    from twwiki.publish.cloud import FirestoreEntityStore, GcsSnapshotStore

    try:
        storage.Client(project=PROJECT, credentials=AnonymousCredentials()).create_bucket(BUCKET)
    except GoogleAPIError:
        pass  # the bucket already exists
    entities = FirestoreEntityStore(PROJECT)
    for path in ("site/current", f"builds/{BUILD}", "builds/older"):
        entities.delete_tree(path)
    return Services(entities=entities, snapshots=GcsSnapshotStore(PROJECT, BUCKET), post=FakePost(), token=None)


def test_publish_writes_snapshot_documents_and_pointer(model_root, services):
    assert publish(settings(model_root), services, deploy=False) == BUILD
    manifest = json.loads((model_root / BUILD / "manifest.json").read_text(encoding="utf-8"))
    for entity_type in ENTITY_TYPES:
        assert services.entities.count(f"builds/{BUILD}/{entity_type}") == manifest["counts"][entity_type]
    assert services.entities.get(f"builds/{BUILD}")["status"] == "ready"
    assert services.entities.get("site/current")["build_id"] == BUILD
    first_unit = (model_root / BUILD / "entities" / "unit.jsonl").read_text(encoding="utf-8").splitlines()[0]
    unit_key = json.loads(first_unit)["key"]
    doc = services.entities.get(f"builds/{BUILD}/unit/{unit_key}")
    assert doc["entity"]["key"] == unit_key and "abilities_keys" in doc
    assert f"builds/{BUILD}/manifest.json" in services.snapshots.list_md5(f"builds/{BUILD}/")


def test_republish_uploads_nothing_new(model_root, services):
    publish(settings(model_root), services, deploy=False)
    uploaded, unchanged = upload_snapshot(services.snapshots, model_root / BUILD, BUILD)
    assert uploaded == 0 and unchanged > 0
    assert publish(settings(model_root), services, deploy=False) == BUILD


def test_prune_refuses_current_and_removes_an_older_build(model_root, services):
    publish(settings(model_root), services, deploy=False)
    services.entities.set("builds/older", {"status": "ready"})
    services.entities.bulk_set("builds/older/unit", [("u1", {"key": "u1"})])
    with pytest.raises(PublishError, match="refusing to prune"):
        prune(services.entities, BUILD)
    prune(services.entities, "older")
    assert services.entities.get("builds/older") is None
    assert services.entities.count("builds/older/unit") == 0
