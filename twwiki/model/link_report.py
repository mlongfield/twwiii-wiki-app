"""Compare the schema's table references with the tables the model reads.

RPFM's schema marks columns that reference another table; extraction keeps
those marks in `_columns`. Every reference touching a table the model read
gets a status:

- both_read: the model reads both tables. Values in the source column that
  match nothing in the target column are counted (empty values mean "none").
- source_not_read: an unread table points at a table the model uses; a
  possible missed link.
- target_not_read: a table the model uses points at one it never reads.

"Read" means a builder queried the table, not that it follows this column.
The report is informational and never fails a build.
"""

from __future__ import annotations

import duckdb

MAX_EXAMPLES = 5


def link_report(con: duckdb.DuckDBPyConnection, tables_read: set[str]) -> dict:
    if not con.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = '_columns'"
    ).fetchone():
        return {"available": False, "summary": {}, "references": []}

    loaded = {row[0] for row in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}
    refs = con.execute("""
        SELECT DISTINCT table_name, column_name, ref_table, ref_column FROM _columns
        WHERE coalesce(ref_table, '') <> '' AND coalesce(ref_column, '') <> ''
        ORDER BY ref_table, ref_column, table_name, column_name
    """).fetchall()

    references = []
    for source, column, target, target_column in refs:
        if source not in tables_read and target not in tables_read:
            continue
        ref = {"source_table": source, "source_column": column,
               "target_table": target, "target_column": target_column}
        if source not in tables_read:
            ref["status"] = "source_not_read"
        elif target not in tables_read or target not in loaded:
            ref["status"] = "target_not_read"
        else:
            ref["status"] = "both_read"
            ref.update(_broken_values(con, source, column, target, target_column))
        references.append(ref)

    summary = {"tables_read": len(tables_read)}
    for status in ("both_read", "source_not_read", "target_not_read"):
        summary[status] = sum(1 for r in references if r["status"] == status)
    summary["with_broken_values"] = sum(1 for r in references if r.get("broken_rows"))
    return {"available": True, "summary": summary, "references": references}


def _broken_values(con, source: str, column: str, target: str, target_column: str) -> dict:
    values = f"""
        SELECT CAST("{column}" AS VARCHAR) AS v FROM "{source}"
        WHERE "{column}" IS NOT NULL AND CAST("{column}" AS VARCHAR) <> ''
    """
    broken = f"""
        SELECT s.v FROM ({values}) s
        ANTI JOIN (SELECT DISTINCT CAST("{target_column}" AS VARCHAR) AS v FROM "{target}") t ON s.v = t.v
    """
    rows_with_value = con.execute(f"SELECT count(*) FROM ({values})").fetchone()[0]
    broken_rows, broken_values = con.execute(f"SELECT count(*), count(DISTINCT v) FROM ({broken})").fetchone()
    examples = [r[0] for r in con.execute(
        f"SELECT DISTINCT v FROM ({broken}) ORDER BY v LIMIT {MAX_EXAMPLES}").fetchall()]
    return {"rows_with_value": rows_with_value, "broken_rows": broken_rows,
            "broken_values": broken_values, "examples": examples}
