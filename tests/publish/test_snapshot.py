import base64
import hashlib

import pytest

from tests.publish.fakes import FakeSnapshotStore
from tests.publish.helpers import make_model
from twwiki.publish.local_model import model_files
from twwiki.publish.snapshot import WORKERS, local_md5, plan_upload, snapshot_prefix, upload_snapshot


def test_prefix_and_workers():
    assert snapshot_prefix("abc") == "builds/abc/"
    assert WORKERS == 16


def test_local_md5_matches_cloud_storage_format(tmp_path):
    path = tmp_path / "f.bin"
    path.write_bytes(b"hello")
    assert local_md5(path) == base64.b64encode(hashlib.md5(b"hello").digest()).decode("ascii")


def test_first_upload_sends_every_file_under_the_build_prefix(tmp_path):
    model_dir = make_model(tmp_path, "b1")
    store = FakeSnapshotStore()
    uploaded, unchanged = upload_snapshot(store, model_dir, "b1")
    files = model_files(model_dir)
    assert (uploaded, unchanged) == (len(files), 0)
    assert sorted(store.objects) == sorted(f"builds/b1/{rel}" for rel in files)
    assert store.objects["builds/b1/images/ui/icon.png"] == b"png"


def test_second_upload_skips_unchanged_files_and_resends_changed_ones(tmp_path):
    model_dir = make_model(tmp_path, "b1")
    store = FakeSnapshotStore()
    upload_snapshot(store, model_dir, "b1")
    store.uploads.clear()
    assert upload_snapshot(store, model_dir, "b1") == (0, len(model_files(model_dir)))
    (model_dir / "images" / "inline.json").write_text('{"x": null}', encoding="utf-8")
    assert upload_snapshot(store, model_dir, "b1") == (1, len(model_files(model_dir)) - 1)
    assert store.uploads == ["builds/b1/images/inline.json"]


def test_plan_upload_ignores_objects_of_other_builds_and_never_deletes(tmp_path):
    model_dir = make_model(tmp_path, "b1")
    remote = {"builds/b0/manifest.json": "x", "builds/b1/extra.json": "y"}
    to_upload, unchanged = plan_upload(model_dir, remote, "builds/b1/")
    assert to_upload == model_files(model_dir) and unchanged == 0
    store = FakeSnapshotStore({"builds/b1/extra.json": b"keep"})
    upload_snapshot(store, model_dir, "b1")
    assert store.objects["builds/b1/extra.json"] == b"keep"


def test_upload_failure_propagates(tmp_path):
    model_dir = make_model(tmp_path, "b1")
    store = FakeSnapshotStore(fail_on="builds/b1/manifest.json")
    with pytest.raises(OSError, match="upload failed"):
        upload_snapshot(store, model_dir, "b1")
