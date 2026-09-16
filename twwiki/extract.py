"""Stage 1: dump every DB table and loc file out of RPFM. Transforms nothing.

Data comes from RPFM's vanilla dependency cache rather than from individual
packs. The cache exposes the game's data as one file set (each table path
appears once), so there is no pack load order to maintain here.

Output layout mirrors the in-game paths:

    raw/<build_id>/
        manifest.json
        files/db/main_units_tables/data__.jsonl
        files/text/db/land_units__.loc.jsonl
        images/ui/units/icons/wh_main_emp_greatswords.png

Each .jsonl file has a header line followed by one line per row:

    {"kind": "DB", "table": "main_units_tables", "version": 7, "path": ...,
     "container": "db.pack", "altered": false,
     "fields": [{"name": "unit", "type": "StringU8", "is_key": true,
                 "reference": null}, ...]}
    ["lord", 1, false, ...]

Row values are in `fields` order with RPFM's type tags stripped; the types
live in the header.
"""

from __future__ import annotations

import argparse
import asyncio
import fnmatch
import hashlib
import json
import logging
import shutil
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .config import load_config
from .rpfm_client import CMD, RpfmClient, RpfmError
from .extract_images import column_values, extract_images, image_containers
from .model.images import normalise

log = logging.getLogger(__name__)

EXTRACTED_FILE_TYPES = {"DB", "Loc"}


def build_id(game_dir: Path, packs: list[str]) -> tuple[str, dict]:
    """Identify a game build by the size+mtime of the packs the data came from.

    Cheap and good enough: any patch that changes data changes a pack. Hashing
    the packs to get a prettier id is not worth the minutes.
    """
    h = hashlib.sha256()
    stats = {}
    for name in sorted(packs):
        p = game_dir / "data" / name
        if not p.exists():
            raise FileNotFoundError(
                f"{p} missing, but RPFM's dependency cache lists files from it. "
                f"Regenerate the cache in RPFM (Game Selected -> Generate "
                f"Dependencies Cache) and check paths.game_dir."
            )
        st = p.stat()
        stats[name] = {"size": st.st_size, "mtime": int(st.st_mtime)}
        h.update(f"{name}:{st.st_size}:{int(st.st_mtime)}".encode())
    return h.hexdigest()[:12], stats


def _skipped(table: str, cfg) -> bool:
    if cfg.tables:
        return table not in cfg.tables
    return any(fnmatch.fnmatch(table, pat) for pat in cfg.skip_tables)


async def select_game(client: RpfmClient, game: str) -> dict:
    """Select the game for this session and load its dependency cache.

    Game selection, schema and dependency cache are per-session on the server,
    so every new connection has to do this, even with RPFM's UI already open.
    """
    _, deps = await client.call(CMD["select_game"], [game, True])
    if not deps or not deps.get("vanilla_packed_files"):
        raise RpfmError(
            f"no dependency cache loaded for {game}. In RPFM run "
            f"Game Selected -> Generate Dependencies Cache (again after every patch)."
        )
    if not await client.call(CMD["schema_loaded"]):
        raise RpfmError(
            f"no schema loaded for {game}. In RPFM run About -> Check Updates "
            f"and download schemas."
        )
    return deps


async def extract(cfg) -> Path:
    game_dir = Path(cfg.paths.game_dir)

    async with RpfmClient(cfg.server.url, cfg.server.timeout_s) as client:
        deps = await select_game(client, cfg.game)
        files = sorted(
            (f for f in deps["vanilla_packed_files"]
             if f["file_type"] in EXTRACTED_FILE_TYPES),
            key=lambda f: f["path"],
        )
        images_cfg = getattr(cfg, "images", None)
        image_folders = list(getattr(images_cfg, "folders", None) or [])
        packs = sorted({f["container_name"] for f in files}
                       | image_containers(deps["vanilla_packed_files"], image_folders))
        bid, pack_stats = build_id(game_dir, packs)
        out = Path(cfg.paths.raw_dir) / bid

        if (out / "manifest.json").exists():
            log.info("build %s already extracted at %s -- nothing to do", bid, out)
            return out

        staging = out.with_name(out.name + ".partial")
        if staging.exists():
            shutil.rmtree(staging)  # leftovers from an interrupted run

        manifest = {
            "build_id": bid,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "game": cfg.game,
            "source": "rpfm dependency cache (DataSource GameFiles)",
            "rpfm_server_version": _server_version(cfg.server.url),
            "packs": pack_stats,
            "tables": {},
            "undecodable": [],
            "altered": [],
            "skipped": [],
        }
        log.info("build %s: %d DB/loc files from %s", bid, len(files), ", ".join(packs))

        fields_cache: dict[tuple, list] = {}
        for i, f in enumerate(files, 1):
            path = f["path"]
            if f["file_type"] == "DB" and _skipped(path.split("/")[1], cfg):
                manifest["skipped"].append(path)
                continue
            try:
                header, rows = await _read_file(client, f, fields_cache)
            except (RpfmError, ValueError, asyncio.TimeoutError) as e:
                # Decode failure is usually schema drift after a patch.
                # Record it loudly; do NOT let it vanish.
                log.error("undecodable: %s (%s)", path, e)
                manifest["undecodable"].append({"path": path, "error": str(e)})
                continue

            dest = staging / "files" / f"{path}.jsonl"
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("w", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(header, ensure_ascii=False) + "\n")
                for row in rows:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            manifest["tables"].setdefault(header["table"], []).append(
                dest.relative_to(staging).as_posix()
            )
            if header["altered"]:
                manifest["altered"].append(path)
            if i % 250 == 0:
                log.info("%d/%d files", i, len(files))

        table_paths, column_problems = _image_paths_from_tables(
            staging, manifest["tables"], getattr(images_cfg, "path_columns", None))
        manifest["images"] = await extract_images(
            client, image_folders, staging / "images", deps["vanilla_packed_files"], table_paths)
        manifest["images"]["failed_folders"].extend(column_problems)
        if table_paths:
            # The build id was fixed before the tables were read, so it cannot
            # cover packs that only these images come from. Say so if any do.
            wanted = {normalise(p) for p in table_paths if p}
            outside = sorted({f["container_name"] for f in deps["vanilla_packed_files"]
                              if f["container_name"] and normalise(f["path"]) in wanted} - set(packs))
            manifest["images"]["from_tables"]["packs_outside_build_id"] = outside
            if outside:
                log.warning("images named in tables come from packs outside the build id: %s",
                            ", ".join(outside))

    staging.mkdir(parents=True, exist_ok=True)
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    staging.rename(out)  # atomic-ish: a build dir either exists complete or not
    log.info(
        "extracted build %s: %d tables, %d undecodable, %d skipped, %d image files, %d failed image folders",
        bid, len(manifest["tables"]), len(manifest["undecodable"]), len(manifest["skipped"]),
        sum(manifest["images"]["folders"].values())
        + manifest["images"].get("from_tables", {}).get("exported", 0),
        len(manifest["images"]["failed_folders"]),
    )
    return out


async def _read_file(client: RpfmClient, f: dict, fields_cache: dict) -> tuple[dict, list]:
    decoded = await client.call(CMD["decode"], ["", f["path"], "GameFiles"])
    if not (isinstance(decoded, list) and len(decoded) == 2
            and isinstance(decoded[0], dict) and "table" in decoded[0]):
        raise ValueError(f"unexpected decode response: {str(decoded)[:200]}")
    table = decoded[0]["table"]
    definition = table["definition"]

    # Row cells follow the *processed* field list (bitwise columns expanded,
    # colours merged), not the raw definition order.
    cache_key = (table["table_name"], definition["version"])
    if cache_key not in fields_cache:
        fields_cache[cache_key] = await client.call(CMD["fields_processed"], definition)
    fields = fields_cache[cache_key]

    rows = []
    for n, row in enumerate(table["table_data"]):
        if len(row) != len(fields):
            raise ValueError(
                f"row {n} has {len(row)} cells but the definition has {len(fields)} fields"
            )
        rows.append([_cell(c) for c in row])

    header = {
        "kind": f["file_type"],
        "table": table["table_name"],
        "version": definition["version"],
        "path": f["path"],
        "container": f["container_name"],
        "altered": table.get("altered", False),
        "fields": [
            {
                "name": x["name"],
                "type": x["field_type"] if isinstance(x["field_type"], str)
                else next(iter(x["field_type"])),
                "is_key": x["is_key"],
                "reference": x.get("is_reference"),
            }
            for x in fields
        ],
    }
    return header, rows


def _image_paths_from_tables(staging: Path, tables: dict, specs: list[str] | None) -> tuple[list | None, list]:
    """Values of each `table.column` in `images.path_columns`, plus any problems.

    Returns None for the paths when no columns are configured.
    """
    if not specs:
        return None, []
    paths, problems = [], []
    for spec in specs:
        table, _, column = spec.partition(".")
        try:
            staged = tables.get(f"{table}_tables")
            if not staged:
                raise ValueError(f"table {table} was not extracted")
            paths.extend(column_values(staging, staged, column))
        except ValueError as e:
            log.error("image path column failed: %s (%s)", spec, e)
            problems.append({"folder": spec, "error": str(e)})
    return paths, problems


def _cell(cell):
    """{"I32": 700} -> 700."""
    if isinstance(cell, dict) and len(cell) == 1:
        return next(iter(cell.values()))
    return cell


def _server_version(ws_url: str) -> str | None:
    base = ws_url.replace("ws://", "http://", 1).replace("wss://", "https://", 1)
    url = base.rsplit("/ws", 1)[0] + "/version"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.load(resp).get("version")
    except (OSError, ValueError) as e:
        log.warning("could not read rpfm_server version from %s: %s", url, e)
        return None


async def discover(cfg) -> None:
    """Select the game, then print read-only probe responses.

    Nothing here opens, modifies or saves a pack. Long responses are truncated
    so the output stays readable.
    """
    probes = [
        ("GetGameSelected", None),
        ("IsSchemaLoaded", None),
        ("IsThereADependencyDatabase", False),
        ("ListOpenPacks", None),
        ("GetTableListFromDependencyPackFile", None),
    ]
    async with RpfmClient(cfg.server.url, cfg.server.timeout_s) as client:
        print(f"session_id: {client.session_id}")
        print(f"rpfm_server version: {_server_version(cfg.server.url)}")
        try:
            deps = await select_game(client, cfg.game)
            vanilla = deps["vanilla_packed_files"]
            print(f"\n== dependency cache: {len(vanilla)} files")
            wanted = [f for f in vanilla if f["file_type"] in EXTRACTED_FILE_TYPES]
            print("DB/loc files by pack:",
                  Counter((f["file_type"], f["container_name"]) for f in wanted).most_common())
        except RpfmError as e:
            print(f"\n== select game failed: {e}")
        results = await client.probe(probes)
    for label, value in results.items():
        text = json.dumps(value, default=str)
        size = f" ({len(value)} items)" if isinstance(value, list) else ""
        if len(text) > 1500:
            text = text[:1500] + f"... [{len(text)} chars total]"
        print(f"\n== {label}{size}\n{text}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--discover", action="store_true",
                    help="probe the server surface instead of extracting")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cfg = load_config(args.config)
    asyncio.run(discover(cfg) if args.discover else extract(cfg))


if __name__ == "__main__":
    main()
