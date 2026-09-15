"""Stage 2: raw JSONL -> DuckDB, typed from the schema.

extract.py receives one already-resolved file per table from RPFM's
dependency cache, so there is no pack merge here. What this stage does:

- types every column from the schema, so numbers are numbers, not strings
- records each column's key and reference flags in `_columns`
- counts duplicate keys per table in `_tables` and warns, rather than
  silently dropping rows
- concatenates every loc file into one `loc` table behind `resolve_loc()`

DB tables are named without the `_tables` suffix (`main_units_tables` ->
`main_units`). Every table gets a `_src` column with the in-game file path.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import duckdb
import pandas as pd

from .config import load_config

log = logging.getLogger(__name__)

# Anything not listed (strings, optional strings, colours) becomes VARCHAR.
DUCK_TYPES = {
    "Boolean": "BOOLEAN",
    "F32": "DOUBLE",
    "F64": "DOUBLE",
    "I16": "BIGINT",
    "I32": "BIGINT",
    "I64": "BIGINT",
    "OptionalI16": "BIGINT",
    "OptionalI32": "BIGINT",
    "OptionalI64": "BIGINT",
}
# Nested sequences arrive as raw byte lists; they are stored as JSON text.
SEQUENCE_TYPES = {"SequenceU16", "SequenceU32"}


def latest_build(raw_dir: Path) -> Path:
    builds = [d for d in raw_dir.iterdir() if (d / "manifest.json").exists()]
    if not builds:
        raise FileNotFoundError(f"no completed builds in {raw_dir}")
    return max(builds, key=lambda d: json.loads(
        (d / "manifest.json").read_text(encoding="utf-8"))["extracted_at"])


def read_raw(path: Path) -> tuple[dict, list[list]]:
    with path.open(encoding="utf-8") as fh:
        header = json.loads(fh.readline())
        rows = [json.loads(line) for line in fh]
    return header, rows


def db_table_name(rpfm_table: str) -> str:
    return "loc" if rpfm_table == "Loc" else rpfm_table.removesuffix("_tables")


def load_table(con, name: str, files: list[Path]) -> dict:
    """Create one typed table from its raw files and report on its keys."""
    fields = None
    rows: list[list] = []
    for path in files:
        header, file_rows = read_raw(path)
        if fields is None:
            fields = header["fields"]
        elif header["fields"] != fields:
            raise ValueError(f"{path} has different columns from {files[0]}")
        rows.extend(row + [header["path"]] for row in file_rows)

    names = [f["name"] for f in fields]
    seq_idx = [i for i, f in enumerate(fields) if f["type"] in SEQUENCE_TYPES]
    for row in rows:
        for i in seq_idx:
            row[i] = json.dumps(row[i])

    df = pd.DataFrame(rows, columns=names + ["_src"], dtype=object)
    select = ", ".join(
        f'CAST("{n}" AS {DUCK_TYPES.get(f["type"], "VARCHAR")}) AS "{n}"'
        for n, f in zip(names, fields)
    )
    con.register("_stage", df)
    try:
        con.execute(f'CREATE TABLE "{name}" AS SELECT {select}, CAST("_src" AS VARCHAR) AS "_src" FROM _stage')
    finally:
        con.unregister("_stage")

    keys = [f["name"] for f in fields if f["is_key"]]
    duplicate_keys = 0
    if keys:
        k = ", ".join(f'"{c}"' for c in keys)
        duplicate_keys = con.execute(
            f'SELECT count(*) FROM (SELECT {k} FROM "{name}" GROUP BY {k} HAVING count(*) > 1)'
        ).fetchone()[0]
    if duplicate_keys:
        log.warning("%s: %d key value(s) appear on more than one row (key: %s)",
                    name, duplicate_keys, keys)

    return {"fields": fields, "rows": len(rows), "keys": keys,
            "duplicate_keys": duplicate_keys, "files": len(files)}


def build(cfg) -> None:
    raw = latest_build(Path(cfg.paths.raw_dir))
    manifest = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))

    if manifest["undecodable"]:
        log.warning(
            "%d file(s) failed to decode in this build -- likely schema drift. "
            "See manifest.json.", len(manifest["undecodable"])
        )

    db_path = Path(cfg.paths.db_path)
    db_path.unlink(missing_ok=True)  # rebuild is always from raw, never in place
    con = duckdb.connect(str(db_path))

    tables_report, columns_report = [], []
    for rpfm_table, rel_paths in sorted(manifest["tables"].items()):
        name = db_table_name(rpfm_table)
        try:
            info = load_table(con, name, [raw / p for p in rel_paths])
        except (duckdb.Error, ValueError) as e:
            log.error("failed to load %s: %s", name, e)
            continue
        tables_report.append((name, rpfm_table, info["rows"], info["keys"],
                              info["duplicate_keys"], info["files"]))
        for pos, f in enumerate(info["fields"]):
            ref = f["reference"] or [None, None]
            columns_report.append((name, pos, f["name"], f["type"], f["is_key"], ref[0], ref[1]))
        log.debug("%-45s %7d rows key=%s", name, info["rows"], info["keys"])

    con.execute("""CREATE TABLE _tables (name VARCHAR, rpfm_table VARCHAR, rows BIGINT,
                   key_columns VARCHAR[], duplicate_keys BIGINT, files BIGINT)""")
    con.executemany("INSERT INTO _tables VALUES (?, ?, ?, ?, ?, ?)", tables_report)
    con.execute("""CREATE TABLE _columns (table_name VARCHAR, position INTEGER, column_name VARCHAR,
                   rpfm_type VARCHAR, is_key BOOLEAN, ref_table VARCHAR, ref_column VARCHAR)""")
    con.executemany("INSERT INTO _columns VALUES (?, ?, ?, ?, ?, ?, ?)", columns_report)

    _build_loc(con)
    con.execute(
        "CREATE TABLE _build AS SELECT ? AS build_id, ? AS extracted_at, ? AS rpfm_server_version",
        [manifest["build_id"], manifest["extracted_at"], manifest.get("rpfm_server_version")],
    )
    con.close()
    log.info("built %s from %s: %d tables loaded, %d with duplicate keys",
             db_path, raw.name, len(tables_report),
             sum(1 for t in tables_report if t[4]))


def _build_loc(con) -> None:
    """Single flat key->text lookup plus a macro for use in page queries."""
    tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    if "loc" not in tables:
        log.warning("no loc data -- pages will show raw keys")
        return
    con.execute("""
        CREATE OR REPLACE VIEW loc_lookup AS
        SELECT key, text FROM loc WHERE key IS NOT NULL
    """)
    # Falls back to the raw key when there is no loc entry or its text is
    # empty, so a missing translation shows up as a visible key rather than a
    # blank page.
    con.execute("""
        CREATE OR REPLACE MACRO resolve_loc(k) AS
            coalesce(nullif((SELECT text FROM loc_lookup WHERE key = k LIMIT 1), ''), k)
    """)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    build(load_config(args.config))


if __name__ == "__main__":
    main()
