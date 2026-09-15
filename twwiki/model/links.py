"""Every reference between entities goes through here.

Catalogs register each entity type's keys and names before any entity is
built, so a link can say whether its target exists. Links to existing targets
are recorded as edges; build.py turns those into reverse-link fields.
"""

from __future__ import annotations

from collections import Counter, defaultdict


class LinkRegistry:
    def __init__(self) -> None:
        self._names: dict[str, dict[str, str | None]] = {}
        self._edges: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)
        self.missing: Counter[str] = Counter()

    def register(self, entity_type: str, names: dict[str, str | None]) -> None:
        self._names.setdefault(entity_type, {}).update(names)

    def has(self, entity_type: str, key: str) -> bool:
        return key in self._names.get(entity_type, {})

    def name(self, entity_type: str, key: str) -> str | None:
        return self._names.get(entity_type, {}).get(key)

    def keys(self, entity_type: str) -> list[str]:
        return list(self._names.get(entity_type, {}))

    def link(self, entity_type: str, key: str | None, *,
             source: tuple[str, str] | None, relation: str) -> dict | None:
        if not key:
            return None
        names = self._names.get(entity_type, {})
        if key in names:
            if source is not None:
                self._edges[(entity_type, key)].append((source[0], source[1], relation))
            return {"type": entity_type, "key": key, "name": names[key], "missing": False}
        source_type = source[0] if source else "-"
        self.missing[f"{source_type}.{relation}->{entity_type}"] += 1
        return {"type": entity_type, "key": key, "name": None, "missing": True}

    def referrers(self, entity_type: str, key: str, relation: str,
                  source_type: str | None = None) -> list[dict]:
        seen: set[tuple[str, str]] = set()
        out = []
        for s_type, s_key, rel in self._edges.get((entity_type, key), []):
            if rel != relation or (source_type and s_type != source_type):
                continue
            if (s_type, s_key) in seen:
                continue
            seen.add((s_type, s_key))
            out.append({"type": s_type, "key": s_key,
                        "name": self.name(s_type, s_key), "missing": False})
        return sorted(out, key=lambda link: (link["type"], link["key"]))
