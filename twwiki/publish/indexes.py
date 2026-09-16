"""Generate firestore.indexes.json.

No composite indexes yet (query screens add them). Every entity collection
exempts the `entity` field from indexing: nested entities could otherwise
exceed Firestore's 40,000 index entries per document, and only the top-level
query fields need indexes.
"""

from __future__ import annotations

import json
from pathlib import Path

from .local_model import ENTITY_TYPES

INDEXES_FILE = Path(__file__).resolve().parents[2] / "firestore.indexes.json"


def generate_indexes() -> dict:
    return {
        "indexes": [],
        "fieldOverrides": [
            {"collectionGroup": entity_type, "fieldPath": "entity", "indexes": []}
            for entity_type in ENTITY_TYPES
        ],
    }


def render_indexes() -> str:
    return json.dumps(generate_indexes(), indent=2) + "\n"


def write_indexes(path: Path = INDEXES_FILE) -> Path:
    path.write_text(render_indexes(), encoding="utf-8", newline="\n")
    return path
