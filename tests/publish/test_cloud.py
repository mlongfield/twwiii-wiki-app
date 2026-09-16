"""Tests for real cloud clients (Firestore, Cloud Storage, HTTP)."""

from __future__ import annotations

import pytest
from google.auth.exceptions import DefaultCredentialsError

from tests.publish.fakes import FakePost, FakeSnapshotStore
from tests.publish.helpers import make_model
from twwiki.publish import PublishError
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
