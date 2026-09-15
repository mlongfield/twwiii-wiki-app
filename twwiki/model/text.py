"""Loc lookups with {{tr:...}} text-replacement substitution.

Game markup ([[col:...]], [[img:...]]) and live-context tokens ({{tt:...}},
{{Cco...}}) are left unchanged; the web app renders them.
"""

from __future__ import annotations

import re

# Where a {{tr:<target>}} token's text is looked up, in order.
TR_PREFIXES = (
    "",
    "ui_text_replacements_localised_text_",
    "campaign_localised_strings_string_",
    "cultures_subcultures_",
    "random_localisation_strings_string_",
)
TR_TOKEN = re.compile(r"\{\{tr:([^}]+)\}\}")
MAX_DEPTH = 5


class LocResolver:
    def __init__(self, entries: dict[str, str]):
        self._entries = entries
        self.unresolved_targets: set[str] = set()

    @classmethod
    def from_duckdb(cls, con) -> "LocResolver":
        return cls(dict(con.execute("SELECT key, text FROM loc").fetchall()))

    def raw(self, key: str) -> str | None:
        """Loc text without substitution; empty text counts as missing."""
        text = self._entries.get(key)
        return text if text else None

    def text(self, key: str) -> str | None:
        raw = self.raw(key)
        return None if raw is None else self.substitute(raw)

    def substitute(self, text: str) -> str:
        for _ in range(MAX_DEPTH):
            changed = False

            def replace(match: re.Match) -> str:
                nonlocal changed
                target = match.group(1)
                for prefix in TR_PREFIXES:
                    value = self._entries.get(prefix + target)
                    if value is not None:
                        changed = True
                        return value
                self.unresolved_targets.add(target)
                return match.group(0)

            text = TR_TOKEN.sub(replace, text)
            if not changed:
                break
        return text
