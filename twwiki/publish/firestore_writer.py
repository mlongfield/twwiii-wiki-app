"""Write a build's entities to Firestore, verify them, switch the live build, prune old builds.

Order matters: `builds/{id}` is marked "loading" before any entity write, and
`site/current` changes only in go_live, after verify_counts has passed.
"""

from __future__ import annotations

import logging
from pathlib import Path

from . import PublishError
from .documents import entity_document
from .local_model import ENTITY_TYPES, iter_entities
from .stores import EntityStore

log = logging.getLogger(__name__)

CURRENT = "site/current"


def build_path(build_id: str) -> str:
    return f"builds/{build_id}"


def collection_path(build_id: str, entity_type: str) -> str:
    return f"builds/{build_id}/{entity_type}"


def write_entities(store: EntityStore, model_dir: Path, build_id: str, manifest: dict) -> dict[str, int]:
    existing = store.get(build_path(build_id)) or {}
    # A new build has no documents to go stale, so skip listing its ids.
    is_new_build = not existing
    store.set(build_path(build_id), {
        "status": "loading",
        "model_version": manifest["model_version"],
        "generated_at": manifest["generated_at"],
        "published_at": existing.get("published_at"),
        "counts": manifest["counts"],
    })
    written: dict[str, int] = {}
    for entity_type in ENTITY_TYPES:
        collection = collection_path(build_id, entity_type)
        keys: set[str] = set()

        def documents(entity_type: str = entity_type, keys: set[str] = keys):
            for entity in iter_entities(model_dir, entity_type):
                keys.add(entity["key"])
                yield entity["key"], entity_document(entity_type, entity)

        written[entity_type] = store.bulk_set(collection, documents())
        stale = [] if is_new_build else sorted(store.list_ids(collection) - keys)
        if stale:
            store.bulk_delete(collection, stale)
        log.info("firestore: %-18s %6d written, %d stale deleted", entity_type, written[entity_type], len(stale))
    return written


def verify_counts(store: EntityStore, build_id: str, counts: dict[str, int]) -> None:
    mismatches = []
    for entity_type in ENTITY_TYPES:
        expected = counts.get(entity_type, 0)
        actual = store.count(collection_path(build_id, entity_type))
        if actual != expected:
            mismatches.append(f"{entity_type} {actual} (expected {expected})")
    if mismatches:
        raise PublishError(
            f"Firestore document counts for build {build_id} differ from the manifest: "
            f"{', '.join(mismatches)}. site/current was not changed; re-run publish.")


def go_live(store: EntityStore, build_id: str, manifest: dict, now: str) -> None:
    store.set(build_path(build_id), {
        "status": "ready",
        "model_version": manifest["model_version"],
        "generated_at": manifest["generated_at"],
        "published_at": now,
        "counts": manifest["counts"],
    })
    current = store.get(CURRENT) or {}
    if current.get("build_id") not in (None, build_id):
        previous = current["build_id"]
    else:
        previous = current.get("previous_build_id")
    store.set(CURRENT, {
        "build_id": build_id,
        "previous_build_id": previous,
        "model_version": manifest["model_version"],
        "published_at": now,
    })


def prune(store: EntityStore, build_id: str) -> None:
    current = store.get(CURRENT) or {}
    if build_id in (current.get("build_id"), current.get("previous_build_id")):
        raise PublishError(f"refusing to prune {build_id}: it is the current or previous build")
    if store.get(build_path(build_id)) is None:
        raise PublishError(f"no build {build_id} in Firestore")
    store.delete_tree(build_path(build_id))
    log.info("pruned Firestore build %s (Cloud Storage snapshot kept)", build_id)
