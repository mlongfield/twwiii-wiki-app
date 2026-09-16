"""Export game image folders from RPFM's dependency cache.

Images are copied as they are (PNG for everything the wiki uses) to
raw/<build_id>/images/<in-game path>. A folder that fails to export is
recorded in the manifest and extraction carries on.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from .rpfm_client import CMD, RpfmError

log = logging.getLogger(__name__)


def image_containers(vanilla_files: list[dict], folders: list[str]) -> set[str]:
    """Packs that hold files under any of the folders (they feed the build id)."""
    prefixes = tuple(folder.lower().rstrip("/") + "/" for folder in folders)
    if not prefixes:
        return set()
    return {f["container_name"] for f in vanilla_files if f["path"].lower().startswith(prefixes)}


async def extract_images(client, folders: list[str], dest: Path) -> dict:
    section: dict = {"folders": {}, "failed_folders": []}
    if not folders:
        return section
    dest.mkdir(parents=True, exist_ok=True)
    for folder in folders:
        try:
            await client.call(CMD["extract_files"],
                              ["", {"GameFiles": [{"Folder": folder}]}, str(dest.resolve()), False])
        except (RpfmError, asyncio.TimeoutError) as e:
            log.error("image folder failed: %s (%s)", folder, e)
            section["failed_folders"].append({"folder": folder, "error": str(e)})
            continue
        folder_dir = dest / folder
        count = sum(1 for p in folder_dir.rglob("*") if p.is_file()) if folder_dir.is_dir() else 0
        if count == 0:
            log.error("image folder exported no files: %s", folder)
            section["failed_folders"].append({"folder": folder, "error": "no files exported"})
            continue
        section["folders"][folder] = count
        log.info("images: %s (%d files)", folder, count)
    return section
