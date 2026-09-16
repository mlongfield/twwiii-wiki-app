"""Game images for the model build.

The extract stage exports whole icon folders to raw/<build_id>/images/<in-game
path>. Data tables refer to images inconsistently (bare names, names with
.png, full paths with backslashes), so every reference goes through
ImageIndex.resolve, which records what it found and what it did not.
"""

from __future__ import annotations

import posixpath
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Sequence

ABILITY_ICONS = ("ui/battle ui/ability_icons",)
TECHNOLOGY_ICONS = ("ui/campaign ui/technologies",)
SKILL_ICONS = ("ui/campaign ui/skills",)
EFFECT_ICONS = ("ui/campaign ui/effect_bundles",)
UNIT_CARDS = ("ui/units/icons",)
BUILDING_ICONS = ("ui/buildings/icons",)
INLINE_ICONS = ("ui/skins/default",)

COUNT_KEYS = ("referenced", "resolved", "missing", "ambiguous")
IMG_TOKEN = re.compile(r"\[\[img:([^\]]+)\]\]")


def normalise(path: str) -> str:
    return re.sub(r"/+", "/", path.strip().replace("\\", "/")).lstrip("/").lower()


class ImageIndex:
    def __init__(self, root: Path | None, paths: Iterable[str]):
        self.root = root
        self._files: dict[str, str] = {}
        self._by_name: dict[str, list[str]] = defaultdict(list)
        for path in paths:
            key = normalise(path)
            self._files[key] = path.replace("\\", "/")
            self._by_name[posixpath.basename(key)].append(key)
        self.used: set[str] = set()
        self.stats: dict[str, Counter] = defaultdict(Counter)

    @property
    def available(self) -> bool:
        return self.root is not None

    @classmethod
    def unavailable(cls) -> "ImageIndex":
        return cls(None, [])

    @classmethod
    def scan(cls, root: Path) -> "ImageIndex":
        if not root.is_dir():
            return cls.unavailable()
        return cls(root, [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()])

    def resolve(self, field: str, value: str | None, folders: Sequence[str] = ()) -> str | None:
        """Find the image a table value refers to; null when absent or ambiguous.

        Tries the value as a path, then inside each folder, then both with .png
        added, then a file name that occurs exactly once anywhere.
        """
        if not self.available or value is None or not value.strip():
            return None
        counts = self.stats[field]
        counts["referenced"] += 1
        v = normalise(value)
        has_extension = bool(posixpath.splitext(v)[1])
        candidates = [v, *(f"{folder}/{v}" for folder in folders)]
        if not has_extension:
            candidates += [f"{c}.png" for c in candidates]
        for candidate in candidates:
            if candidate in self._files:
                return self._hit(counts, candidate)
        matches = self._by_name.get(posixpath.basename(v) + ("" if has_extension else ".png"), [])
        if len(matches) == 1:
            return self._hit(counts, matches[0])
        counts["ambiguous" if matches else "missing"] += 1
        return None

    def _hit(self, counts: Counter, key: str) -> str:
        counts["resolved"] += 1
        self.used.add(key)
        return key

    def copy_used(self, dest: Path) -> int:
        """Copy every resolved image to dest/<path>. Errors propagate."""
        for key in sorted(self.used):
            target = dest / key
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.root / self._files[key], target)
        return len(self.used)

    def manifest(self, files_copied: int) -> dict:
        return {
            "available": self.available,
            "files_copied": files_copied,
            "fields": {f: {k: c[k] for k in COUNT_KEYS} for f, c in sorted(self.stats.items())},
        }


def inline_targets(entities: dict[str, list[dict]]) -> list[str]:
    """Every distinct [[img:<target>]] target in any entity string."""
    found: set[str] = set()

    def walk(value) -> None:
        if isinstance(value, str):
            if "[[img:" in value:
                found.update(IMG_TOKEN.findall(value))
        elif isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)

    for rows in entities.values():
        for row in rows:
            walk(row)
    return sorted(found)
