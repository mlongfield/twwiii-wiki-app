"""Shared state for one model build."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from .links import LinkRegistry
from .text import LocResolver


def opt(value):
    """RPFM optional strings arrive as ''. Treat them as absent."""
    return None if value == "" or value is None else value


@dataclass
class Context:
    con: duckdb.DuckDBPyConnection
    loc: LocResolver
    links: LinkRegistry = field(default_factory=LinkRegistry)
    missing_names: Counter = field(default_factory=Counter)
    partial: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def open(cls, db_path: str | Path) -> "Context":
        con = duckdb.connect(str(db_path), read_only=True)
        return cls(con=con, loc=LocResolver.from_duckdb(con))

    def rows(self, sql: str, params: list | None = None) -> list[dict]:
        cur = self.con.execute(sql, params or [])
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def table_exists(self, name: str) -> bool:
        return bool(self.con.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = ?", [name]
        ).fetchone())

    def require(self, entity_type: str, *tables: str) -> bool:
        missing = [t for t in tables if not self.table_exists(t)]
        if missing:
            self.partial.setdefault(entity_type, []).extend(missing)
        return not missing

    def catalog_name(self, entity_type: str, loc_key: str) -> str | None:
        """Resolve an entity's display name. Call from catalog() only."""
        text = self.loc.text(loc_key)
        if text is None:
            self.missing_names[entity_type] += 1
        return text
