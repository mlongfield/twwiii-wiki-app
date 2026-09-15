"""Stage 3: DuckDB -> markdown pages, one per entity, plus an index.

Rendering is deliberately dumb. Everything interesting -- joins, loc
resolution, derived stats -- happens in the SQL in config.yaml, so you can
iterate on the model without touching this file.
"""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path

import duckdb

from .config import load_config

log = logging.getLogger(__name__)


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", str(value).lower()).strip("-") or "unnamed"


def render_entity(row: dict, slug_col: str) -> str:
    title = row.get("name") or row.get(slug_col)
    lines = [f"# {title}", ""]
    for col, val in row.items():
        if col == "name" or val is None or val == "":
            continue
        lines.append(f"- **{col.replace('_', ' ')}**: {val}")
    return "\n".join(lines) + "\n"


def render(cfg) -> None:
    con = duckdb.connect(str(cfg.paths.db_path), read_only=True)
    build = con.execute("SELECT build_id FROM _build").fetchone()[0]
    site = Path(cfg.paths.site_dir)
    site.mkdir(parents=True, exist_ok=True)

    index: list[str] = [f"# TWW3 data — build `{build}`", ""]

    for name, spec in vars(cfg.pages).items():
        try:
            # Plain tuples rather than a DataFrame: pandas would turn NULLs in
            # integer columns into NaN, which then renders as "nan".
            cur = con.execute(spec.query)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        except duckdb.Error as e:
            # A failed page query usually means a column moved in a patch.
            log.error("page '%s' query failed: %s", name, e)
            continue

        out_dir = site / name
        out_dir.mkdir(parents=True, exist_ok=True)
        for f in out_dir.glob("*.md"):
            f.unlink()  # stale pages from removed content must not linger

        index.append(f"## {name} ({len(rows)})")
        for row in rows:
            slug = slugify(row[spec.slug])
            (out_dir / f"{slug}.md").write_text(
                render_entity(row, spec.slug), encoding="utf-8"
            )
            label = row.get("name") or row[spec.slug]
            index.append(f"- [{label}]({name}/{slug}.md)")
        index.append("")
        log.info("%-12s %5d pages", name, len(rows))

    (site / "index.md").write_text("\n".join(index), encoding="utf-8")
    con.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    render(load_config(args.config))


if __name__ == "__main__":
    main()
