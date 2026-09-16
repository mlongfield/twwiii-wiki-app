"""Tests for real cloud clients (Firestore, Cloud Storage, HTTP)."""

from __future__ import annotations

import threading

import pytest
from google.api_core.exceptions import ServiceUnavailable
from google.auth.credentials import AnonymousCredentials
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import firestore
from google.cloud.firestore_v1.bulk_batch import BulkWriteBatch
from google.cloud.firestore_v1.document import DocumentReference
from google.cloud.firestore_v1.types.firestore import BatchWriteResponse
from google.cloud.firestore_v1.types.write import WriteResult
from google.rpc import status_pb2

from tests.publish.fakes import FakePost, FakeSnapshotStore
from tests.publish.helpers import make_model
from twwiki.publish import PublishError, cloud
from twwiki.publish.cloud import FirestoreEntityStore
from twwiki.publish.pipeline import Services, Settings, publish


def test_firestore_store_defers_credentials_to_preflight(tmp_path, monkeypatch):
    """FirestoreEntityStore does not validate credentials until first use,
    allowing preflight to catch and report them with a helpful message."""
    def fake_client(*args, **kwargs):
        raise DefaultCredentialsError("no application default credentials")

    monkeypatch.setattr("twwiki.publish.cloud.firestore.Client", fake_client)

    # Constructing the store should not raise
    store = FirestoreEntityStore("p")

    # But building services and trying to publish should fail with a clear message
    make_model(tmp_path, "b1")
    services = Services(entities=store, snapshots=FakeSnapshotStore(), post=FakePost(), token="tok")
    settings = Settings("p", "bkt", "o/r", "deploy.yml", "main", tmp_path)

    with pytest.raises(PublishError, match="gcloud auth application-default login"):
        publish(settings, services)


def _offline_store(monkeypatch, commit) -> FirestoreEntityStore:
    """A store whose Firestore client never reaches the network: every batch
    commit goes through `commit`, and retries give up after two attempts."""
    real_client = firestore.Client
    monkeypatch.setattr("twwiki.publish.cloud.firestore.Client",
                        lambda project: real_client(project=project, credentials=AnonymousCredentials()))
    monkeypatch.setattr(BulkWriteBatch, "commit", commit)
    monkeypatch.setattr(cloud, "MAX_WRITE_ATTEMPTS", 1)
    return FirestoreEntityStore("demo")


def _within(seconds: float, call):
    """Run `call` in a thread so a hang fails the test instead of the suite."""
    outcome: dict = {}

    def target():
        try:
            outcome["result"] = call()
        except BaseException as e:  # noqa: BLE001 - handed back to the test
            outcome["error"] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(seconds)
    assert not thread.is_alive(), f"did not finish within {seconds} s"
    return outcome


def _response(codes: list[int]) -> BatchWriteResponse:
    return BatchWriteResponse(write_results=[WriteResult() for _ in codes],
                              status=[status_pb2.Status(code=code, message="aborted") for code in codes])


def test_bulk_set_raises_publish_error_when_batch_commits_fail(monkeypatch):
    def commit(batch, *args, **kwargs):
        raise ServiceUnavailable("firestore is down")

    store = _offline_store(monkeypatch, commit)
    docs = ((f"d{i}", {"k": i}) for i in range(600))

    outcome = _within(10, lambda: store.bulk_set("builds/b1/unit", docs))

    assert isinstance(outcome.get("error"), PublishError), outcome
    assert "600 of 600 writes to builds/b1/unit failed" in str(outcome["error"])
    assert "firestore is down" in str(outcome["error"])


def test_bulk_set_retries_a_failed_write_that_is_retried_after_the_last_batch(monkeypatch):
    attempts: dict[str, int] = {}

    def commit(batch, *args, **kwargs):
        codes = []
        for reference in batch._document_references.values():
            attempts[reference.path] = attempts.get(reference.path, 0) + 1
            codes.append(10 if reference.id == "d24" and attempts[reference.path] == 1 else 0)
        return _response(codes)

    store = _offline_store(monkeypatch, commit)
    docs = ((f"d{i}", {"k": i}) for i in range(25))

    outcome = _within(10, lambda: store.bulk_set("builds/b1/unit", docs))

    assert outcome == {"result": 25}
    assert attempts["builds/b1/unit/d24"] == 2


def test_delete_tree_raises_publish_error_when_deletes_fail(monkeypatch):
    def commit(batch, *args, **kwargs):
        raise ServiceUnavailable("firestore is down")

    store = _offline_store(monkeypatch, commit)
    monkeypatch.setattr(DocumentReference, "collections", lambda self, *args, **kwargs: iter(()))

    outcome = _within(10, lambda: store.delete_tree("builds/b1"))

    assert isinstance(outcome.get("error"), PublishError), outcome
    assert "1 deletes under builds/b1 failed" in str(outcome["error"])
    assert "firestore is down" in str(outcome["error"])
