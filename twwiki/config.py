from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import yaml


def _ns(obj):
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _ns(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_ns(v) for v in obj]
    return obj


def load_config(path: str | Path = "config.yaml") -> SimpleNamespace:
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not cfg.get("game"):
        raise ValueError("config is missing `game` (RPFM game key, e.g. warhammer_3)")
    return _ns(cfg)
