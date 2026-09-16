"""Interfaces the publish steps use for Firestore, Cloud Storage and HTTP.

`cloud.py` implements them for real; tests use the fakes in tests/publish/fakes.py.
Paths are Firestore paths such as "builds/b1/unit" (a collection) or
"builds/b1/unit/some_key" (a document).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, Protocol

HttpPost = Callable[[str, dict[str, str], bytes], int]
"""POST url with headers and body; returns the HTTP status (errors included)."""


class SnapshotStore(Protocol):
    def exists(self) -> bool:
        """Whether the bucket exists and is readable."""

    def list_md5(self, prefix: str) -> dict[str, str]:
        """Object name -> base64 MD5 for every object under prefix."""

    def upload(self, local_path: Path, name: str) -> None:
        """Upload one file to the object `name`, replacing it."""


class EntityStore(Protocol):
    def get(self, path: str) -> dict | None:
        """A document's data, or None when it does not exist."""

    def set(self, path: str, data: dict) -> None:
        """Replace a document."""

    def bulk_set(self, collection: str, docs: Iterable[tuple[str, dict]]) -> int:
        """Replace documents by id; returns how many. Raises PublishError if any finally fails."""

    def list_ids(self, collection: str) -> set[str]:
        """Ids of every document in a collection."""

    def bulk_delete(self, collection: str, ids: Iterable[str]) -> int:
        """Delete documents by id; returns how many. Raises PublishError if any finally fails."""

    def count(self, collection: str) -> int:
        """Number of documents in a collection."""

    def delete_tree(self, path: str) -> None:
        """Delete a document and every subcollection under it."""
