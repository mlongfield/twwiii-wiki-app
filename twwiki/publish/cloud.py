"""Real Firestore, Cloud Storage and HTTP implementations of the publish stores.

Credentials are Application Default Credentials (`gcloud auth
application-default login`). When FIRESTORE_EMULATOR_HOST or
STORAGE_EMULATOR_HOST is set, the clients use the Firebase emulators with
anonymous credentials instead.
"""

from __future__ import annotations

import mimetypes
import os
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable

from google.api_core.exceptions import NotFound
from google.auth.credentials import AnonymousCredentials
from google.cloud import firestore, storage
from google.cloud.firestore_v1.bulk_writer import BulkWriter
from google.cloud.firestore_v1.types.firestore import BatchWriteResponse
from google.cloud.firestore_v1.types.write import WriteResult
from google.rpc import code_pb2, status_pb2

from . import PublishError

MAX_WRITE_ATTEMPTS = 15


class SafeBulkWriter(BulkWriter):
    """A BulkWriter whose failures all reach its write-error callback.

    The library loses an exception raised by a batch commit inside an executor
    future and never releases that batch's in-flight count, so enough failed
    batches make it wait forever. Here a failed commit reports every write in
    the batch as UNAVAILABLE instead, to be retried or given up on like any
    other failed write.

    close() marks the writer closed before its final flush, so a retry still
    pending then is rejected with a bare Exception. Flushing first sends those
    retries while the writer is open; recursive_delete calls close() itself.
    """

    def _send(self, batch):
        try:
            return super()._send(batch)
        except Exception as e:
            writes = len(batch)
            return BatchWriteResponse(
                write_results=[WriteResult() for _ in range(writes)],
                status=[status_pb2.Status(code=code_pb2.UNAVAILABLE, message=str(e)) for _ in range(writes)])

    def close(self):
        self.flush()
        super().close()


class FirestoreEntityStore:
    def __init__(self, project: str):
        self._project = project
        self._db = None

    def _client(self) -> firestore.Client:
        """Lazily create and cache the Firestore client.

        The client picks up FIRESTORE_EMULATOR_HOST itself.
        Credentials are validated only on first use, allowing preflight
        to catch DefaultCredentialsError with a helpful error message.
        """
        if self._db is None:
            self._db = firestore.Client(project=self._project)
        return self._db

    def get(self, path: str) -> dict | None:
        snapshot = self._client().document(path).get()
        return snapshot.to_dict() if snapshot.exists else None

    def set(self, path: str, data: dict) -> None:
        self._client().document(path).set(data)

    def bulk_set(self, collection: str, docs: Iterable[tuple[str, dict]]) -> int:
        return self._bulk(collection, ((doc_id, data) for doc_id, data in docs))

    def bulk_delete(self, collection: str, ids: Iterable[str]) -> int:
        return self._bulk(collection, ((doc_id, None) for doc_id in ids))

    def _writer(self) -> tuple[SafeBulkWriter, list[str]]:
        """A bulk writer and the list it fills with the writes it gave up on.

        The writer retries a failed write up to MAX_WRITE_ATTEMPTS times and
        then drops it without raising, so callers raise PublishError when the
        list is not empty after close().
        """
        failures: list[str] = []

        def on_error(failure, _writer) -> bool:
            if failure.attempts < MAX_WRITE_ATTEMPTS:
                return True
            failures.append(f"{failure.operation.reference.path}: {failure.message}")
            return False

        writer = SafeBulkWriter(client=self._client())
        writer.on_write_error(on_error)
        return writer, failures

    def _bulk(self, collection: str, operations: Iterable[tuple[str, dict | None]]) -> int:
        writer, failures = self._writer()
        target = self._client().collection(collection)
        done = 0
        try:
            for doc_id, data in operations:
                ref = target.document(doc_id)
                if data is None:
                    writer.delete(ref)
                else:
                    writer.set(ref, data)
                done += 1
        finally:
            # Send retries still pending from the last batches while the
            # writer accepts operations; a closed writer rejects them.
            writer.flush()
            writer.close()
        if failures:
            raise PublishError(f"{len(failures)} of {done} writes to {collection} failed; first: {failures[0]}")
        return done

    def list_ids(self, collection: str) -> set[str]:
        return {snapshot.id for snapshot in self._client().collection(collection).select(["__name__"]).stream()}

    def count(self, collection: str) -> int:
        result = self._client().collection(collection).count().get()
        return int(result[0][0].value)

    def delete_tree(self, path: str) -> None:
        writer, failures = self._writer()
        self._client().recursive_delete(self._client().document(path), bulk_writer=writer)
        if failures:
            raise PublishError(f"{len(failures)} deletes under {path} failed; first: {failures[0]}")


class GcsSnapshotStore:
    """Cloud Storage bucket; one client per thread for parallel uploads."""

    def __init__(self, project: str, bucket: str):
        self._project = project
        self._bucket = bucket
        self._local = threading.local()

    def _client(self) -> storage.Client:
        client = getattr(self._local, "client", None)
        if client is None:
            credentials = AnonymousCredentials() if os.getenv("STORAGE_EMULATOR_HOST") else None
            client = storage.Client(project=self._project, credentials=credentials)
            self._local.client = client
        return client

    def exists(self) -> bool:
        try:
            list(self._client().list_blobs(self._bucket, max_results=1))
        except NotFound:
            return False
        return True

    def list_md5(self, prefix: str) -> dict[str, str]:
        return {blob.name: blob.md5_hash for blob in self._client().list_blobs(self._bucket, prefix=prefix)}

    def upload(self, local_path: Path, name: str) -> None:
        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        blob = self._client().bucket(self._bucket).blob(name)
        blob.upload_from_filename(str(local_path), content_type=content_type)


def urllib_post(url: str, headers: dict[str, str], body: bytes) -> int:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status
    except urllib.error.HTTPError as e:
        return e.code
