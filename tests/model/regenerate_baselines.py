"""Rewrite the missing-link and missing-image baselines from a full build of twwiki.duckdb.

Run deliberately after a model change, then explain every count that rose:
    uv run python -m tests.model.regenerate_baselines
"""

import json
from pathlib import Path

from twwiki.model.build import build_all
from twwiki.model.context import Context
from twwiki.model.images import COUNT_KEYS, ImageIndex

HERE = Path(__file__).parent


def main() -> None:
    assert {"missing", "ambiguous"} <= set(COUNT_KEYS), "images.py renamed its counters"
    ctx = Context.open("twwiki.duckdb")
    build_id = ctx.con.execute("SELECT build_id FROM _build").fetchone()[0]
    ctx.images = ImageIndex.scan(Path("raw") / build_id / "images")
    build_all(ctx)
    (HERE / "missing_links_baseline.json").write_text(
        json.dumps(dict(sorted(ctx.links.missing.items())), indent=2) + "\n", encoding="utf-8")
    if ctx.images.available:
        images = {field: {k: counts[k] for k in ("missing", "ambiguous")} for field, counts in sorted(ctx.images.stats.items())}
        (HERE / "missing_images_baseline.json").write_text(json.dumps(images, indent=2) + "\n", encoding="utf-8")
    ctx.con.close()


if __name__ == "__main__":
    main()
