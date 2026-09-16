"""In-memory stand-ins for Cloud Storage, Firestore and HTTP."""

from __future__ import annotations

import base64
import copy
import hashlib
from pathlib import Path

from twwiki.publish import PublishError


def md5_b64(data: bytes) -> str:
    return base64.b64encode(hashlib.md5(data).digest()).decode("ascii")


class FakeSnapshotStore:
    def __init__(self, objects: dict[str, bytes] | None = None, exists: bool = True,
                 fail_on: str | None = None):
        self.objects: dict[str, bytes] = dict(objects or {})
        self._exists = exists
        self.fail_on = fail_on
        self.uploads: list[str] = []

    def exists(self) -> bool:
        return self._exists

    def list_md5(self, prefix: str) -> dict[str, str]:
        return {name: md5_b64(data) for name, data in self.objects.items() if name.startswith(prefix)}

    def upload(self, local_path: Path, name: str) -> None:
        if name == self.fail_on:
            raise OSError(f"upload failed: {name}")
        self.objects[name] = local_path.read_bytes()
        self.uploads.append(name)


class FakeEntityStore:
    """Firestore as a dict of document path -> data, recording every call."""

    def __init__(self):
        self.docs: dict[str, dict] = {}
        self.calls: list[tuple[str, str]] = []
        self.count_override: dict[str, int] = {}
        self.fail_get: Exception | None = None
        self.fail_bulk_set_on: str | None = None

    def get(self, path: str) -> dict | None:
        self.calls.append(("get", path))
        if self.fail_get is not None:
            raise self.fail_get
        data = self.docs.get(path)
        return copy.deepcopy(data) if data is not None else None

    def set(self, path: str, data: dict) -> None:
        self.calls.append(("set", path))
        self.docs[path] = copy.deepcopy(data)

    def bulk_set(self, collection, docs) -> int:
        self.calls.append(("bulk_set", collection))
        written = 0
        for doc_id, data in docs:
            if collection == self.fail_bulk_set_on:
                raise PublishError(f"1 writes to {collection} failed")
            self.docs[f"{collection}/{doc_id}"] = data
            written += 1
        return written

    def _ids(self, collection: str) -> set[str]:
        prefix = collection + "/"
        return {p[len(prefix):] for p in self.docs if p.startswith(prefix) and "/" not in p[len(prefix):]}

    def list_ids(self, collection: str) -> set[str]:
        self.calls.append(("list_ids", collection))
        return self._ids(collection)

    def bulk_delete(self, collection, ids) -> int:
        self.calls.append(("bulk_delete", collection))
        ids = list(ids)
        for doc_id in ids:
            self.docs.pop(f"{collection}/{doc_id}", None)
        return len(ids)

    def count(self, collection: str) -> int:
        self.calls.append(("count", collection))
        return self.count_override.get(collection, len(self._ids(collection)))

    def delete_tree(self, path: str) -> None:
        self.calls.append(("delete_tree", path))
        for doc_path in [p for p in self.docs if p == path or p.startswith(path + "/")]:
            del self.docs[doc_path]
