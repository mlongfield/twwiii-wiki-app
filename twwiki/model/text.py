"""Loc lookups with {{tr:...}} text-replacement substitution and text cleanup.

Placeholder text counts as missing. {{tt:...}} tokens (tooltip targets that
don't exist), {{Cco...}} live UI expressions and {{tr:...}} tokens that never
resolve are removed and recorded for the manifest. Game markup ([[col:...]],
[[img:...]]) is left unchanged; the web app renders it.
"""

from __future__ import annotations

import re
from collections import Counter

# Where a {{tr:<target>}} token's text is looked up, in order.
TR_PREFIXES = (
    "",
    "ui_text_replacements_localised_text_",
    "campaign_localised_strings_string_",
    "cultures_subcultures_",
    "random_localisation_strings_string_",
)
TR_TOKEN = re.compile(r"\{\{tr:([^}]+)\}\}")
TT_TOKEN = re.compile(r"\{\{tt:([^}]*)\}\}")
CCO_TOKEN = re.compile(r"\{\{Cco[^:}]*:[^}]*\}\}")
# An unclosed `{{` with no later `}}`: a broken token that never got a closing brace.
UNCLOSED_TOKEN = re.compile(r"\{\{(?:(?!\}\}).)*$", re.DOTALL)
MAX_DEPTH = 5


def is_placeholder(text: str) -> bool:
    return text.strip().lower() == "placeholder" or "%PLACEHOLDER%" in text


def loc_prefix(key: str) -> str:
    """A loc key's table-and-field part, for reporting. Keys don't mark where the
    record starts, so this is the first three underscore-separated words."""
    return "_".join(key.split("_")[:3])


def split_title_body(text: str | None) -> tuple[str | None, str | None]:
    """Split game text on its first || into a trimmed title and body; empty parts become None."""
    if text is None:
        return None, None
    if "||" not in text:
        return None, text
    title, body = text.split("||", 1)
    return title.strip() or None, body.strip() or None


def round_float(value: float) -> float:
    """Six significant digits, which hides float32 artefacts such as 0.90000004.
    Whole numbers are returned unchanged so large values keep every digit."""
    if value.is_integer():
        return value
    return float(f"{value:.6g}")


class LocResolver:
    def __init__(self, entries: dict[str, str]):
        self._entries = entries
        self.unresolved_targets: set[str] = set()
        self.placeholder_keys: set[str] = set()
        self.dropped_tt_targets: set[str] = set()
        self.dropped_cco_tokens: set[str] = set()

    @classmethod
    def from_duckdb(cls, con) -> "LocResolver":
        return cls(dict(con.execute("SELECT key, text FROM loc").fetchall()))

    def raw(self, key: str) -> str | None:
        """Loc text without substitution; empty and placeholder text count as missing."""
        text = self._entries.get(key)
        if not text:
            return None
        if is_placeholder(text):
            self.placeholder_keys.add(key)
            return None
        return text

    def text(self, key: str) -> str | None:
        raw = self.raw(key)
        if raw is None:
            return None
        substituted = self.substitute(raw)
        return substituted if substituted.strip() else None

    def substitute(self, text: str) -> str:
        for _ in range(MAX_DEPTH):
            changed = False

            def replace(match: re.Match) -> str:
                nonlocal changed
                for prefix in TR_PREFIXES:
                    value = self._entries.get(prefix + match.group(1))
                    if value is not None:
                        changed = True
                        return value
                return match.group(0)

            text = TR_TOKEN.sub(replace, text)
            if not changed:
                break
        text = TR_TOKEN.sub(self._drop_tr, text)
        text = TT_TOKEN.sub(self._drop_tt, text)
        text = CCO_TOKEN.sub(self._drop_cco, text)
        return UNCLOSED_TOKEN.sub(self._drop_unclosed, text)

    def _drop_unclosed(self, match: re.Match) -> str:
        tail = match.group(0)
        prefix = "{{tr:"
        target = tail[len(prefix):] if tail.startswith(prefix) else tail
        self.unresolved_targets.add(target)
        return ""

    def _drop_tr(self, match: re.Match) -> str:
        self.unresolved_targets.add(match.group(1))
        return ""

    def _drop_tt(self, match: re.Match) -> str:
        self.dropped_tt_targets.add(match.group(1))
        return ""

    def _drop_cco(self, match: re.Match) -> str:
        self.dropped_cco_tokens.add(match.group(0))
        return ""

    def text_report(self) -> dict:
        return {
            "placeholders_by_prefix": dict(sorted(Counter(loc_prefix(k) for k in self.placeholder_keys).items())),
            "dropped_tt_tokens": len(self.dropped_tt_targets),
            "dropped_cco_tokens": len(self.dropped_cco_tokens),
            "dropped_tr_tokens": len(self.unresolved_targets),
        }
