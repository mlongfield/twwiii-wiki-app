"""Upload a model folder to Cloud Storage as builds/{build_id}/…

Files whose MD5 already matches the stored object are skipped, so a re-run
after a failure only uploads what is missing or changed. Nothing is deleted.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .local_model import model_files
from .stores import SnapshotStore

log = logging.getLogger(__name__)

WORKERS = 16


def snapshot_prefix(build_id: str) -> str:
    return f"builds/{build_id}/"


def local_md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return base64.b64encode(digest.digest()).decode("ascii")


def plan_upload(model_dir: Path, remote_md5: dict[str, str], prefix: str) -> tuple[list[str], int]:
    to_upload: list[str] = []
    unchanged = 0
    for rel in model_files(model_dir):
        if remote_md5.get(prefix + rel) == local_md5(model_dir / rel):
            unchanged += 1
        else:
            to_upload.append(rel)
    return to_upload, unchanged


def upload_snapshot(store: SnapshotStore, model_dir: Path, build_id: str) -> tuple[int, int]:
    prefix = snapshot_prefix(build_id)
    to_upload, unchanged = plan_upload(model_dir, store.list_md5(prefix), prefix)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        # list() re-raises the first upload error.
        list(pool.map(lambda rel: store.upload(model_dir / rel, prefix + rel), to_upload))
    log.info("snapshot: %d uploaded, %d unchanged under %s", len(to_upload), unchanged, prefix)
    return len(to_upload), unchanged
