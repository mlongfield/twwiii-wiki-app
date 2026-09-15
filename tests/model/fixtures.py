"""Tiny in-memory databases for model unit tests."""

from __future__ import annotations

import duckdb
import pandas as pd

from twwiki.model.context import Context
from twwiki.model.text import LocResolver


def make_context(tables: dict[str, list[dict]], loc: dict[str, str] | None = None) -> Context:
    con = duckdb.connect(":memory:")
    for name, rows in tables.items():
        if not rows:
            raise ValueError(f"fixture table {name} needs at least one row")
        con.register("_fixture", pd.DataFrame(rows))
        con.execute(f'CREATE TABLE "{name}" AS SELECT * FROM _fixture')
        con.unregister("_fixture")
    loc = loc or {}
    con.execute("CREATE TABLE loc (key VARCHAR, text VARCHAR)")
    if loc:
        con.executemany("INSERT INTO loc VALUES (?, ?)", list(loc.items()))
    return Context(con=con, loc=LocResolver(dict(loc)))
