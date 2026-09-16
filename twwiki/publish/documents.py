"""Firestore documents for model entities.

A document keeps the full entity under `entity` (exempt from indexing) and
adds top-level fields to query on: `key`, `name`, the type's browse fields
from INDEX_FIELDS, and `<field>_keys` for every top-level link or link-list
field in the entity's Pydantic model.
"""

from __future__ import annotations

import typing
from functools import cache
from typing import Literal

from twwiki.model.build import INDEX_FIELDS
from twwiki.model.schemas import ENTITY_MODELS, Link

RESERVED_FIELDS: tuple[str, ...] = ("key", "name", "entity")
LinkKind = Literal["one", "list"]


def _link_kind(annotation) -> LinkKind | None:
    if annotation is Link:
        return "one"
    args = typing.get_args(annotation)
    if typing.get_origin(annotation) is list and args == (Link,):
        return "list"
    if set(args) == {Link, type(None)}:
        return "one"
    return None


@cache
def link_fields(entity_type: str) -> dict[str, LinkKind]:
    fields = ENTITY_MODELS[entity_type].model_fields
    return {name: kind for name, info in fields.items() if (kind := _link_kind(info.annotation))}


def derived_field_collisions(entity_type: str) -> list[str]:
    """`<field>_keys` names that clash with an entity field, a browse field or a reserved field."""
    taken = set(ENTITY_MODELS[entity_type].model_fields) | set(RESERVED_FIELDS)
    taken |= set(INDEX_FIELDS.get(entity_type, []))
    return sorted(f"{name}_keys" for name in link_fields(entity_type) if f"{name}_keys" in taken)


def entity_document(entity_type: str, entity: dict) -> dict:
    doc: dict = {"key": entity["key"], "name": entity.get("name")}
    for field in INDEX_FIELDS.get(entity_type, []):
        doc[field] = entity.get(field)
    for field, kind in link_fields(entity_type).items():
        value = entity.get(field)
        if kind == "one":
            links = [value] if value else []
        else:
            links = value or []
        doc[f"{field}_keys"] = list(dict.fromkeys(item["key"] for item in links))
    doc["entity"] = entity
    return doc
