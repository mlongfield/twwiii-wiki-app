"""In-memory stand-ins for Cloud Storage, Firestore and HTTP."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path


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
