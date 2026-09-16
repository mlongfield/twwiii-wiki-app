"""Read a model folder written by `python -m twwiki.model`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from twwiki.model.build import MODEL_VERSION
from twwiki.model.schemas import ENTITY_MODELS

from . import PublishError

ENTITY_TYPES: tuple[str, ...] = tuple(sorted(ENTITY_MODELS))


def find_model_dir(model_root: Path, build_id: str | None = None) -> Path:
    """model_root/<build_id>, or the newest model by manifest generated_at."""
    if build_id:
        model_dir = model_root / build_id
        if not (model_dir / "manifest.json").is_file():
            raise PublishError(f"no model for build {build_id} at {model_dir}")
        return model_dir
    best: tuple[str, Path] | None = None
    candidates = sorted(model_root.iterdir()) if model_root.is_dir() else []
    for path in candidates:
        if not path.is_dir() or path.name.endswith((".partial", ".old")):
            continue
        try:
            manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        generated_at = str(manifest.get("generated_at", ""))
        if best is None or generated_at > best[0]:
            best = (generated_at, path)
    if best is None:
        raise PublishError(f"no model found under {model_root}; run `uv run python -m twwiki.model` first")
    return best[1]


def check_model(model_dir: Path) -> dict:
    """Return the manifest after checking the model version and required files."""
    try:
        manifest = json.loads((model_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise PublishError(f"{model_dir}: manifest.json is missing or unreadable ({e})") from e
    if manifest.get("model_version") != MODEL_VERSION:
        raise PublishError(
            f"{model_dir}: model_version {manifest.get('model_version')}, expected {MODEL_VERSION}; "
            f"rebuild the model with `uv run python -m twwiki.model`")
    required = [f"entities/{t}.jsonl" for t in ENTITY_TYPES]
    required += [f"schema/{t}.schema.json" for t in ENTITY_TYPES]
    required.append("images/inline.json")
    missing = [rel for rel in required if not (model_dir / rel).is_file()]
    if missing:
        raise PublishError(f"{model_dir}: missing {', '.join(missing)}")
    return manifest


def iter_entities(model_dir: Path, entity_type: str) -> Iterator[dict]:
    with (model_dir / "entities" / f"{entity_type}.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def model_files(model_dir: Path) -> list[str]:
    return sorted(p.relative_to(model_dir).as_posix() for p in model_dir.rglob("*") if p.is_file())
