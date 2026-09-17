"""Temporary model folders shaped like model/<build_id>/."""

from __future__ import annotations

import json
from pathlib import Path

from twwiki.model.build import MODEL_VERSION
from twwiki.publish.local_model import ENTITY_TYPES


def make_model(root: Path, build_id: str = "b1", *, generated_at: str = "2026-09-16T00:00:00+00:00",
               entities: dict[str, list[dict]] | None = None, model_version: int = MODEL_VERSION) -> Path:
    """Write a complete minimal model folder and return its path."""
    entities = entities or {}
    model_dir = root / build_id
    (model_dir / "entities").mkdir(parents=True)
    (model_dir / "schema").mkdir()
    (model_dir / "images" / "ui").mkdir(parents=True)
    for entity_type in ENTITY_TYPES:
        rows = entities.get(entity_type, [])
        (model_dir / "entities" / f"{entity_type}.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        (model_dir / "schema" / f"{entity_type}.schema.json").write_text("{}", encoding="utf-8")
    (model_dir / "images" / "inline.json").write_text("{}", encoding="utf-8")
    (model_dir / "images" / "ui" / "icon.png").write_bytes(b"png")
    manifest = {
        "build_id": build_id,
        "model_version": model_version,
        "generated_at": generated_at,
        "counts": {t: len(entities.get(t, [])) for t in ENTITY_TYPES},
    }
    (model_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return model_dir
