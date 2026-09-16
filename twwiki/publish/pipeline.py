"""Publish steps in order, with the preflight that guards them.

publish: preflight -> snapshot upload -> entity writes -> count check ->
go live (site/current) -> deploy dispatch. Any failure before go-live leaves
the live build untouched, and every step is safe to repeat.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import GoogleAuthError

from . import PublishError
from .deploy import dispatch_deploy
from .documents import derived_field_collisions
from .firestore_writer import CURRENT, build_path, go_live, prune, verify_counts, write_entities
from .local_model import ENTITY_TYPES, check_model, find_model_dir
from .snapshot import upload_snapshot
from .stores import EntityStore, HttpPost, SnapshotStore

log = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Settings:
    project_id: str
    storage_bucket: str
    repo: str
    workflow: str
    ref: str
    model_root: Path

    @classmethod
    def from_config(cls, cfg) -> "Settings":
        firebase = getattr(cfg, "firebase", None)
        if firebase is None:
            raise PublishError("config.yaml has no `firebase` section; see README 'Publishing and hosting'")
        workflow = firebase.deploy_workflow
        return cls(
            project_id=firebase.project_id,
            storage_bucket=firebase.storage_bucket,
            repo=workflow.repo,
            workflow=workflow.workflow,
            ref=workflow.ref,
            model_root=Path(getattr(cfg.paths, "model_dir", "./model")),
        )


@dataclass
class Services:
    entities: EntityStore
    snapshots: SnapshotStore
    post: HttpPost
    token: str | None
    now: Callable[[], str] = field(default=_utc_now)


def preflight(settings: Settings, services: Services, model_dir: Path, *, deploy: bool) -> dict:
    manifest = check_model(model_dir)
    collisions = {t: names for t in ENTITY_TYPES if (names := derived_field_collisions(t))}
    if collisions:
        raise PublishError(f"derived Firestore fields clash with entity fields: {collisions}")
    try:
        services.entities.get(CURRENT)
    except (GoogleAPIError, GoogleAuthError) as e:
        raise PublishError(
            f"cannot read Firestore in project {settings.project_id} ({e}); "
            f"run `gcloud auth application-default login`") from e
    try:
        bucket_found = services.snapshots.exists()
    except (GoogleAPIError, GoogleAuthError) as e:
        raise PublishError(f"cannot read bucket {settings.storage_bucket} ({e})") from e
    if not bucket_found:
        raise PublishError(
            f"bucket {settings.storage_bucket} not found; check firebase.storage_bucket in config.yaml")
    if deploy and not services.token:
        raise PublishError("TWWIKI_GITHUB_TOKEN is not set; set it, or pass --no-deploy")
    return manifest


def _dispatch(settings: Settings, services: Services, build_id: str) -> str:
    return dispatch_deploy(services.post, repo=settings.repo, workflow=settings.workflow, ref=settings.ref,
                           build_id=build_id, token=services.token or "")


def publish(settings: Settings, services: Services, *, build_id: str | None = None, deploy: bool = True) -> str:
    model_dir = find_model_dir(settings.model_root, build_id)
    manifest = preflight(settings, services, model_dir, deploy=deploy)
    published = manifest["build_id"]
    log.info("publishing build %s from %s", published, model_dir)
    upload_snapshot(services.snapshots, model_dir, published)
    write_entities(services.entities, model_dir, published, manifest)
    verify_counts(services.entities, published, manifest["counts"])
    go_live(services.entities, published, manifest, services.now())
    log.info("build %s is live: site/current updated", published)
    if deploy:
        log.info("deploy started: %s", _dispatch(settings, services, published))
    return published


def deploy_only(settings: Settings, services: Services, *, build_id: str | None = None) -> str:
    if not services.token:
        raise PublishError("TWWIKI_GITHUB_TOKEN is not set")
    if build_id is None:
        build_id = (services.entities.get(CURRENT) or {}).get("build_id")
        if not build_id:
            raise PublishError("site/current names no build; publish one first")
    status = (services.entities.get(build_path(build_id)) or {}).get("status", "missing")
    if status != "ready":
        raise PublishError(f"build {build_id} is not ready (status: {status})")
    return _dispatch(settings, services, build_id)


def prune_build(settings: Settings, services: Services, build_id: str) -> None:
    prune(services.entities, build_id)
