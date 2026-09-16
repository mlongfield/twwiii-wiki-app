"""Export game images from RPFM's dependency cache.

Images are copied as they are (PNG for everything the wiki uses) to
raw/<build_id>/images/<in-game path>. Each `images.folders` entry is either a
folder, exported whole, or a pattern whose `*` matches one path segment
(`ui/flags/*/mon_64.png`), exported file by file. `images.path_columns` names
table columns whose values are exact image paths (`ui_tagged_images.image_path`);
those files are exported too. An entry that fails to export is recorded in the
manifest and extraction carries on.
"""

from __future__ import annotations

import asyncio
import json
import logging
from fnmatch import fnmatchcase
from pathlib import Path

from .model.images import normalise
from .rpfm_client import CMD, RpfmError

log = logging.getLogger(__name__)

FILE_BATCH = 500
PATH_COLUMNS_ENTRY = "path_columns"


def matches_entry(path: str, entry: str) -> bool:
    """Whether a game file path falls under a folder entry or matches a pattern entry."""
    path, entry = path.lower(), entry.lower().rstrip("/")
    if "*" not in entry:
        return path.startswith(entry + "/")
    path_parts, entry_parts = path.split("/"), entry.split("/")
    return len(path_parts) == len(entry_parts) and all(
        fnmatchcase(p, e) for p, e in zip(path_parts, entry_parts))


def _matching(game_files: list[dict], entry: str) -> list[dict]:
    prefix = entry.lower().split("*", 1)[0].rsplit("/", 1)[0] + "/"
    return [f for f in game_files if f["path"].lower().startswith(prefix) and matches_entry(f["path"], entry)]


def image_containers(game_files: list[dict], entries: list[str]) -> set[str]:
    """Packs that hold files selected by any entry (they feed the build id)."""
    return {f["container_name"] for entry in entries for f in _matching(game_files, entry)
            if f["container_name"]}


def column_values(staging: Path, rel_paths: list[str], column: str) -> list:
    """One column's values from table files staged earlier in the run.

    Raises ValueError when a file has no such column.
    """
    values = []
    for rel in rel_paths:
        with (staging / rel).open(encoding="utf-8") as fh:
            names = [f["name"] for f in json.loads(fh.readline())["fields"]]
            if column not in names:
                raise ValueError(f"{rel} has no column {column}")
            index = names.index(column)
            values.extend(json.loads(line)[index] for line in fh if line.strip())
    return values


async def _export_files(client, paths: list[str], dest: Path) -> int:
    """Export files in batches; returns how many are on disk. RPFM errors propagate."""
    for start in range(0, len(paths), FILE_BATCH):
        batch = [{"File": p} for p in paths[start:start + FILE_BATCH]]
        await client.call(CMD["extract_files"], ["", {"GameFiles": batch}, str(dest.resolve()), False])
    return sum(1 for p in paths if (dest / p).is_file())


async def extract_images(client, entries: list[str], dest: Path, game_files: list[dict],
                         table_paths: list[str] | None = None) -> dict:
    """Export folder and pattern entries, then the exact paths read from tables.

    `table_paths` None means no path columns are configured; the section then
    has no `from_tables` counts.
    """
    section: dict = {"folders": {}, "failed_folders": []}
    if table_paths is not None:
        section["from_tables"] = {"listed": 0, "not_in_game": 0, "already_covered": 0, "exported": 0}
    if not entries and not table_paths:
        return section
    dest.mkdir(parents=True, exist_ok=True)

    def failed(entry: str, error: str) -> None:
        log.error("images failed: %s (%s)", entry, error)
        section["failed_folders"].append({"folder": entry, "error": error})

    for entry in entries:
        try:
            if "*" in entry:
                paths = sorted(f["path"] for f in _matching(game_files, entry))
                if not paths:
                    failed(entry, "no files matched")
                    continue
                count = await _export_files(client, paths, dest)
            else:
                await client.call(CMD["extract_files"],
                                  ["", {"GameFiles": [{"Folder": entry}]}, str(dest.resolve()), False])
                folder_dir = dest / entry
                count = sum(1 for p in folder_dir.rglob("*") if p.is_file()) if folder_dir.is_dir() else 0
        except (RpfmError, asyncio.TimeoutError) as e:
            failed(entry, str(e))
            continue
        if count == 0:
            failed(entry, "no files exported")
            continue
        section["folders"][entry] = count
        log.info("images: %s (%d files)", entry, count)

    if table_paths:
        await _export_table_paths(client, entries, dest, game_files, table_paths, section, failed)
    return section


async def _export_table_paths(client, entries, dest, game_files, table_paths, section, failed) -> None:
    counts = section["from_tables"]
    wanted = {normalise(p) for p in table_paths if p and p.strip()}
    by_path = {normalise(f["path"]): f["path"] for f in game_files}
    counts["listed"] = len(wanted)
    to_export = []
    for key in sorted(wanted):
        path = by_path.get(key)
        if path is None:
            counts["not_in_game"] += 1
        elif any(matches_entry(path, entry) for entry in entries):
            counts["already_covered"] += 1
        else:
            to_export.append(path)
    try:
        counts["exported"] = await _export_files(client, sorted(to_export), dest)
    except (RpfmError, asyncio.TimeoutError) as e:
        failed(PATH_COLUMNS_ENTRY, str(e))
    log.info("images: from tables %s", counts)
