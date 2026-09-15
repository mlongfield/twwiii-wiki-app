# Wiki Data: Regions and Images Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the pipeline so `model/<build_id>/` also contains campaign regions and provinces, building-chain availability, and the game images the wiki needs, resolved onto entities and copied next to the model.

**Architecture:** The extract stage additionally exports configured icon folders from RPFM's dependency cache into `raw/<build_id>/images/`. The model stage scans that folder once (`ImageIndex`), resolves every image reference while building entities, builds the new `region` and `province` entities from the start-position tables, and copies only the referenced images into the model output. Load is unchanged.

**Tech Stack:** Python 3.13 (uv), DuckDB, Pydantic v2, pytest, rpfm_server 5.0.6 WebSocket API.

**Spec:** `docs/superpowers/specs/2026-09-15-wiki-data-regions-images-design.md`

## Global Constraints

- No new dependencies; run everything through `uv run`.
- Test command: `uv run pytest` (whole suite must stay green after every task). Real-data tests skip when `twwiki.duckdb` is absent.
- Entity models are `Strict` Pydantic models (`extra="forbid"`); every field a builder emits must exist in `twwiki/model/schemas.py` and vice versa.
- Every image field name ends in `_image` and holds a path relative to `model/<build_id>/images/` (lower-case, forward slashes) or null.
- Gaps in game data are counted (manifest or `ctx.links.missing`), never silently dropped. Only schema validation failures and image copy failures stop a model build.
- `raw/` is append-only per build; never delete or overwrite a previous build's directory.
- Do not change RPFM settings (in particular do not enable the ESF editor). Out of scope: `startpos.esf`, lord portraits, 3D art, DDS/TGA conversion, per-faction unit cards, the web app.
- Code style: match the surrounding modules (module docstring, `from __future__ import annotations`, `opt()` for RPFM empty strings, `by_key`/`grouped` helpers, links only via `ctx.links.link`).
- Commit with a heredoc message ending in the trailer line `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Work on branch `feature/wiki-data-regions-images`. Do not push.

---

## File Structure

| File | Responsibility |
|---|---|
| `twwiki/model/images.py` (new) | `ImageIndex` (scan, resolve, counts, copy) and `inline_targets` |
| `twwiki/extract_images.py` (new) | Export image folders through RPFM; find the packs they come from |
| `twwiki/model/regions.py` (new) | `region` and `province` entities; slot-template matching; chain-set resolution |
| `twwiki/model/context.py` | `Context.images`, `Context.manifest_sections` |
| `twwiki/model/schemas.py` | New `*_image` fields, `ChainAvailability`, `SlotResource`, `SlotTemplate`, `Region`, `Province` |
| `twwiki/model/{abilities,characters,technologies,effects,items,units,buildings}.py` | Resolve their image fields; buildings also availability |
| `twwiki/model/build.py` | Register `regions`; copy images; `images/inline.json`; manifest sections; `run(..., raw_root)` |
| `twwiki/model/__main__.py` | Pass `paths.raw_dir` to `run` |
| `twwiki/extract.py`, `twwiki/rpfm_client.py`, `config.yaml` | Image export wired into extraction |
| `tests/model/test_images.py`, `tests/test_extract_images.py`, `tests/model/test_image_fields.py`, `tests/model/test_regions.py` (new) | Unit tests |
| `tests/model/test_buildings.py`, `tests/model/test_build.py`, `tests/model/test_real_build.py` | Extended tests |
| `tests/model/missing_images_baseline.json` (new) | Image gap baseline from the first real build |
| `README.md` | Document images and regions |

---

### Task 1: ImageIndex

**Files:**
- Create: `twwiki/model/images.py`
- Modify: `twwiki/model/context.py`
- Test: `tests/model/test_images.py`

**Interfaces:**
- Produces:
  - `normalise(path: str) -> str`
  - `class ImageIndex(root: Path | None, paths: Iterable[str])` with `available: bool` (property), `used: set[str]`, `stats: dict[str, Counter]`, `ImageIndex.unavailable() -> ImageIndex`, `ImageIndex.scan(root: Path) -> ImageIndex`, `resolve(field: str, value: str | None, folders: Sequence[str] = ()) -> str | None`, `copy_used(dest: Path) -> int`, `manifest(files_copied: int) -> dict`
  - Folder constants `ABILITY_ICONS`, `TECHNOLOGY_ICONS`, `SKILL_ICONS`, `EFFECT_ICONS`, `UNIT_CARDS`, `BUILDING_ICONS`, `INLINE_ICONS` (tuples of str)
  - `inline_targets(entities: dict[str, list[dict]]) -> list[str]`
  - `Context.images: ImageIndex` (defaults to `ImageIndex.unavailable()`)

- [ ] **Step 1: Write the failing tests**

Create `tests/model/test_images.py`:

```python
from pathlib import Path

from twwiki.model.images import ImageIndex, inline_targets, normalise
from tests.model.fixtures import make_context

PATHS = [
    "ui/battle ui/ability_icons/hold.png",
    "ui/campaign ui/skills/leader.png",
    "ui/campaign ui/effect_bundles/resource_grain.png",
    "ui/skins/default/icon_turns.png",
    "ui/skins/default/dlc25_nemesis_crown/icon_turns.png",
    "ui/skins/other/icon_unique.png",
    "ui/units/icons/sub/dup.png",
    "ui/skins/default/dup.png",
]


def index():
    return ImageIndex(Path("images"), PATHS)


def test_normalise_lowercases_and_uses_forward_slashes():
    assert normalise(" UI\\Campaign UI\\Skills\\X.PNG ") == "ui/campaign ui/skills/x.png"


def test_resolves_full_path_with_backslashes():
    images = index()
    assert images.resolve("resource", "ui\\campaign ui\\effect_bundles\\resource_grain.png") == \
        "ui/campaign ui/effect_bundles/resource_grain.png"


def test_resolves_bare_name_in_folder_adding_png():
    images = index()
    assert images.resolve("ability.icon_image", "hold", ("ui/battle ui/ability_icons",)) == \
        "ui/battle ui/ability_icons/hold.png"
    assert images.resolve("skill.icon_image", "leader.png", ("ui/campaign ui/skills",)) == \
        "ui/campaign ui/skills/leader.png"


def test_folder_match_wins_over_ambiguous_file_name():
    assert index().resolve("inline", "icon_turns", ("ui/skins/default",)) == "ui/skins/default/icon_turns.png"


def test_falls_back_to_unique_file_name():
    assert index().resolve("inline", "icon_unique", ("ui/skins/default",)) == "ui/skins/other/icon_unique.png"


def test_ambiguous_and_missing_are_null_and_counted():
    images = index()
    assert images.resolve("f", "dup") is None
    assert images.resolve("f", "nope.png") is None
    assert images.resolve("f", "hold", ("ui/battle ui/ability_icons",)) is not None
    assert dict(images.stats["f"]) == {"referenced": 3, "ambiguous": 1, "missing": 1, "resolved": 1}
    assert images.used == {"ui/battle ui/ability_icons/hold.png"}


def test_empty_values_are_not_counted():
    images = index()
    assert images.resolve("g", "") is None and images.resolve("g", None) is None
    assert "g" not in images.stats


def test_unavailable_index_resolves_nothing_and_counts_nothing():
    images = ImageIndex.unavailable()
    assert images.available is False
    assert images.resolve("f", "ui/skins/default/dup.png") is None
    assert images.stats == {} and images.used == set()


def test_scan_copy_and_manifest(tmp_path):
    raw = tmp_path / "raw"
    for rel in ["ui/units/icons/gs.png", "ui/units/icons/unused.png"]:
        (raw / rel).parent.mkdir(parents=True, exist_ok=True)
        (raw / rel).write_bytes(b"png")
    assert ImageIndex.scan(tmp_path / "absent").available is False

    images = ImageIndex.scan(raw)
    assert images.available is True
    assert images.resolve("unit.card_image", "gs", ("ui/units/icons",)) == "ui/units/icons/gs.png"
    dest = tmp_path / "out"
    assert images.copy_used(dest) == 1
    assert (dest / "ui/units/icons/gs.png").read_bytes() == b"png"
    assert not (dest / "ui/units/icons/unused.png").exists()
    assert images.manifest(1) == {"available": True, "files_copied": 1, "fields": {
        "unit.card_image": {"referenced": 1, "resolved": 1, "missing": 0, "ambiguous": 0}}}


def test_inline_targets_collects_distinct_sorted_targets_from_nested_values():
    entities = {"unit": [{"key": "a", "description": "[[img:icon_b]] x [[img:icon_a]]",
                          "levels": [{"text": "[[img:icon_b]]"}], "n": 3}],
                "skill": [{"key": "b", "description": None}]}
    assert inline_targets(entities) == ["icon_a", "icon_b"]


def test_context_images_default_to_unavailable():
    assert make_context({"t": [{"a": 1}]}).images.available is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/model/test_images.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'twwiki.model.images'`

- [ ] **Step 3: Implement `twwiki/model/images.py`**

```python
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
    return path.strip().replace("\\", "/").lstrip("/").lower()


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
```

- [ ] **Step 4: Add `images` to `Context`**

In `twwiki/model/context.py`, add the import after `from .links import LinkRegistry`:

```python
from .images import ImageIndex
```

and add this field to the `Context` dataclass directly after `partial`:

```python
    images: ImageIndex = field(default_factory=ImageIndex.unavailable)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/model/test_images.py -v`
Expected: PASS (11 tests)

Run: `uv run pytest`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add twwiki/model/images.py twwiki/model/context.py tests/model/test_images.py
git commit -F - <<'EOF'
feat(model): add ImageIndex for resolving game image references

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 2: Export image folders during extraction

**Files:**
- Create: `twwiki/extract_images.py`
- Modify: `twwiki/rpfm_client.py:34-47` (the `CMD` dict), `twwiki/extract.py` (module docstring, imports, `extract()`), `config.yaml`
- Test: `tests/test_extract_images.py`

**Interfaces:**
- Consumes: `RpfmClient.call(command, args)`, `RpfmError` from `twwiki/rpfm_client.py`.
- Produces:
  - `CMD["extract_files"] == "ExtractPackedFiles"`
  - `image_containers(vanilla_files: list[dict], folders: list[str]) -> set[str]`
  - `async extract_images(client, folders: list[str], dest: Path) -> dict` returning `{"folders": {<folder>: <file count>}, "failed_folders": [{"folder", "error"}]}`
  - Extract manifest key `images` with that dict; files at `raw/<build_id>/images/<in-game path>`.

RPFM reference (docs/server `ExtractPackedFiles`): arguments `[pack_key, {DataSource: [ContainerPath, ...]}, dest_path, as_tsv]`, response `{"StringVecPathBuf": [string, [path, ...]]}`. With DataSource `GameFiles` the pack key is unused. A folder is `{"Folder": "<in-game folder>"}`. The server resolves `dest_path` itself, so always send an absolute path. Files land at `<dest_path>/<in-game path>`. Counts are taken from disk rather than the response.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_extract_images.py`:

```python
import asyncio
from pathlib import Path

from twwiki.extract_images import extract_images, image_containers
from twwiki.rpfm_client import RpfmError


class FakeClient:
    def __init__(self, files_by_folder: dict[str, list[str]], failing: tuple[str, ...] = ()):
        self.files_by_folder = files_by_folder
        self.failing = failing
        self.calls: list[tuple[str, list]] = []

    async def call(self, command, args=None):
        self.calls.append((command, args))
        _, sources, dest, _ = args
        folder = sources["GameFiles"][0]["Folder"]
        if folder in self.failing:
            raise RpfmError(f"{command} failed: boom")
        written = []
        for name in self.files_by_folder.get(folder, []):
            path = Path(dest) / folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"png")
            written.append(str(path))
        return ["", written]


def test_exports_each_folder_with_game_files_source_and_counts_files(tmp_path):
    client = FakeClient({"ui/units/icons": ["a.png", "b.png"], "ui/skins": ["default/x.png"]})
    dest = tmp_path / "images"
    section = asyncio.run(extract_images(client, ["ui/units/icons", "ui/skins"], dest))
    assert client.calls == [
        ("ExtractPackedFiles", ["", {"GameFiles": [{"Folder": "ui/units/icons"}]}, str(dest.resolve()), False]),
        ("ExtractPackedFiles", ["", {"GameFiles": [{"Folder": "ui/skins"}]}, str(dest.resolve()), False]),
    ]
    assert section == {"folders": {"ui/units/icons": 2, "ui/skins": 1}, "failed_folders": []}
    assert (dest / "ui/skins/default/x.png").exists()


def test_failed_and_empty_folders_are_listed_and_others_still_run(tmp_path):
    client = FakeClient({"ui/units/icons": ["a.png"]}, failing=("ui/broken",))
    section = asyncio.run(extract_images(client, ["ui/broken", "ui/empty", "ui/units/icons"], tmp_path / "images"))
    assert section["folders"] == {"ui/units/icons": 1}
    assert section["failed_folders"] == [
        {"folder": "ui/broken", "error": "ExtractPackedFiles failed: boom"},
        {"folder": "ui/empty", "error": "no files exported"},
    ]


def test_no_folders_exports_nothing(tmp_path):
    client = FakeClient({})
    section = asyncio.run(extract_images(client, [], tmp_path / "images"))
    assert section == {"folders": {}, "failed_folders": []}
    assert client.calls == [] and not (tmp_path / "images").exists()


def test_image_containers_match_folder_prefixes_only():
    files = [
        {"path": "ui/units/icons/a.png", "container_name": "ui.pack"},
        {"path": "UI/Skins/default/b.png", "container_name": "ui2.pack"},
        {"path": "ui/units/icons_old/c.png", "container_name": "old.pack"},
        {"path": "db/main_units_tables/data__", "container_name": "db.pack"},
    ]
    assert image_containers(files, ["ui/units/icons", "ui/skins"]) == {"ui.pack", "ui2.pack"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_extract_images.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'twwiki.extract_images'`

- [ ] **Step 3: Add the command to `CMD`**

In `twwiki/rpfm_client.py`, add inside the `CMD` dict after the `fields_processed` entry:

```python
    # [pack_key, {DataSource: [{"File"|"Folder": path}, ...]}, dest_path, as_tsv]
    #   -> {StringVecPathBuf: [string, [path, ...]]}. With DataSource
    #   "GameFiles" the pack_key is unused; files land at dest_path/<path>.
    "extract_files": "ExtractPackedFiles",
```

- [ ] **Step 4: Implement `twwiki/extract_images.py`**

```python
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
```

- [ ] **Step 5: Run the new tests**

Run: `uv run pytest tests/test_extract_images.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Wire it into `extract()`**

In `twwiki/extract.py`:

1. In the module docstring layout block, add a line after `files/text/db/land_units__.loc.jsonl`:

```
        images/ui/units/icons/wh_main_emp_greatswords.png
```

2. Add the import after `from .rpfm_client import CMD, RpfmClient, RpfmError`:

```python
from .extract_images import extract_images, image_containers
```

3. Replace these lines in `extract()`:

```python
        packs = sorted({f["container_name"] for f in files})
```

with:

```python
        image_folders = list(getattr(getattr(cfg, "images", None), "folders", None) or [])
        packs = sorted({f["container_name"] for f in files}
                       | image_containers(deps["vanilla_packed_files"], image_folders))
```

4. After the `for i, f in enumerate(files, 1):` loop ends (still inside `async with`), add:

```python
        manifest["images"] = await extract_images(client, image_folders, staging / "images")
```

5. Replace the final log call with:

```python
    log.info(
        "extracted build %s: %d tables, %d undecodable, %d skipped, %d image files, %d failed image folders",
        bid, len(manifest["tables"]), len(manifest["undecodable"]), len(manifest["skipped"]),
        sum(manifest["images"]["folders"].values()), len(manifest["images"]["failed_folders"]),
    )
```

- [ ] **Step 7: Configure the folders**

In `config.yaml`, add after the `skip_tables` list:

```yaml
# Game image folders exported to raw/<build_id>/images/<in-game path>.
# The packs these come from are part of the build id.
images:
  folders:
    - "ui/battle ui/ability_icons"
    - "ui/campaign ui/technologies"
    - "ui/campaign ui/skills"
    - "ui/campaign ui/effect_bundles"
    - "ui/units/icons"
    - "ui/buildings/icons"
    - "ui/skins"
```

- [ ] **Step 8: Run the full suite**

Run: `uv run pytest`
Expected: all tests pass. (`extract()` itself is exercised against the real server in Task 7.)

- [ ] **Step 9: Commit**

```bash
git add twwiki/extract_images.py twwiki/rpfm_client.py twwiki/extract.py config.yaml tests/test_extract_images.py
git commit -F - <<'EOF'
feat(extract): export game image folders next to the tables

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 3: Image fields on existing entities

**Files:**
- Modify: `twwiki/model/schemas.py`, `twwiki/model/abilities.py`, `twwiki/model/characters.py`, `twwiki/model/technologies.py`, `twwiki/model/effects.py`, `twwiki/model/items.py`, `twwiki/model/units.py`, `twwiki/model/buildings.py`
- Test: `tests/model/test_image_fields.py`

**Interfaces:**
- Consumes: `ctx.images.resolve(field, value, folders)` and the folder constants from Task 1.
- Produces (schema fields, all `str | None`): `Effect.icon_image`, `Effect.icon_negative_image`, `EffectBundle.icon_image`, `Ability.icon_image`, `Skill.icon_image`, `Technology.icon_image`, `Trait.icon_image`, `Unit.card_image`, `BuildingLevel.icon_image`. Count field names: `ability.icon_image`, `skill.icon_image`, `technology.icon_image`, `effect.icon_image`, `effect.icon_negative_image`, `effect_bundle.icon_image`, `trait.icon_image`, `unit.card_image`, `building_level.icon_image`.
- Produces: `buildings.level_variant(ctx, level_key, variants) -> dict | None` (the variant that names a level).

- [ ] **Step 1: Write the failing tests**

Create `tests/model/test_image_fields.py` (existing test modules are imported as modules so pytest does not collect their tests twice):

```python
from pathlib import Path

import tests.model.test_abilities as t_abilities
import tests.model.test_buildings as t_buildings
import tests.model.test_characters as t_characters
import tests.model.test_effects as t_effects
import tests.model.test_items as t_items
import tests.model.test_technologies as t_technologies
import tests.model.test_units as t_units
from twwiki.model import abilities, buildings, characters, effects, items, schemas, technologies, units
from twwiki.model.images import ImageIndex


def with_images(ctx, *paths):
    ctx.images = ImageIndex(Path("images"), paths)
    return ctx


def test_ability_icon_image():
    ctx = with_images(t_abilities.ability_context(), "ui/battle ui/ability_icons/hold.png")
    built = {a["key"]: a for a in abilities.build(ctx)["ability"]}
    assert built["hold"]["icon_image"] == "ui/battle ui/ability_icons/hold.png"
    assert built["plain"]["icon_image"] is None
    assert ctx.images.stats["ability.icon_image"]["missing"] == 1
    for a in built.values():
        schemas.ENTITY_MODELS["ability"].model_validate(a)


def test_skill_icon_image_uses_folder_then_unique_file_name():
    ctx = with_images(t_characters.character_context(),
                      "ui/campaign ui/skills/leader.png", "ui/campaign ui/skills/sub/mentor.png")
    built = {s["key"]: s for s in characters.build(ctx)["skill"]}
    assert built["leader_of_men"]["icon_image"] == "ui/campaign ui/skills/leader.png"
    assert built["mentor"]["icon_image"] == "ui/campaign ui/skills/sub/mentor.png"
    for s in built.values():
        schemas.ENTITY_MODELS["skill"].model_validate(s)


def test_technology_icon_image():
    ctx = with_images(t_technologies.tech_context(), "ui/campaign ui/technologies/hw.png")
    built = {t["key"]: t for t in technologies.build(ctx)["technology"]}
    assert built["heavy_weapons"]["icon_image"] == "ui/campaign ui/technologies/hw.png"
    assert built["piracy"]["icon_image"] is None
    for t in built.values():
        schemas.ENTITY_MODELS["technology"].model_validate(t)


def test_effect_and_bundle_icon_images():
    ctx = with_images(t_effects.effects_context(),
                      "ui/campaign ui/effect_bundles/a.png", "ui/campaign ui/effect_bundles/b.png")
    built = effects.build(ctx)
    by_key = {e["key"]: e for e in built["effect"]}
    assert by_key["e_attack"]["icon_image"] == "ui/campaign ui/effect_bundles/a.png"
    assert by_key["e_attack"]["icon_negative_image"] is None
    assert by_key["e_research"]["icon_image"] is None
    assert "effect.icon_negative_image" not in ctx.images.stats
    assert built["effect_bundle"][0]["icon_image"] == "ui/campaign ui/effect_bundles/b.png"
    for e in built["effect"]:
        schemas.ENTITY_MODELS["effect"].model_validate(e)
    schemas.ENTITY_MODELS["effect_bundle"].model_validate(built["effect_bundle"][0])


def test_trait_icon_image_comes_from_its_category():
    ctx = with_images(t_items.items_context(), "ui/campaign ui/skills/trait_personality.png")
    ctx.con.execute("CREATE TABLE trait_categories (category VARCHAR, icon_path VARCHAR)")
    ctx.con.execute("INSERT INTO trait_categories VALUES (?, ?)",
                    ["personality", "ui\\campaign ui\\skills\\trait_personality.png"])
    built = {t["key"]: t for t in items.build(ctx)["trait"]}
    assert built["brave"]["icon_image"] == "ui/campaign ui/skills/trait_personality.png"
    for t in built.values():
        schemas.ENTITY_MODELS["trait"].model_validate(t)


def test_unit_card_image_uses_the_variant_without_a_faction():
    ctx = with_images(t_units.unit_context({"unit_variants": [
        {"faction": "", "name": "", "unit": "gs_land", "variant": "", "unit_card": "gs_card"},
        {"faction": "reikland", "name": "", "unit": "arch_land", "variant": "", "unit_card": "reik_archers"},
    ]}), "ui/units/icons/gs_card.png", "ui/units/icons/reik_archers.png")
    built = {u["key"]: u for u in units.build(ctx)["unit"]}
    assert built["gs"]["card_image"] == "ui/units/icons/gs_card.png"
    assert built["archers"]["card_image"] is None
    assert built["ship"]["card_image"] is None
    for u in built.values():
        schemas.ENTITY_MODELS["unit"].model_validate(u)


def test_building_level_icon_image_uses_the_naming_variant():
    ctx = with_images(t_buildings.building_context(), "ui/buildings/icons/emp_barracks.png",
                      "ui/buildings/icons/black_tower.png", "ui/buildings/icons/faction_tower.png")
    ctx.con.execute("""UPDATE building_culture_variants SET icon = CASE
        WHEN building = 'barracks_1' THEN 'emp_barracks'
        WHEN faction = 'followers' THEN 'faction_tower'
        ELSE 'black_tower' END""")
    built = {b["key"]: b for b in buildings.build(ctx)["building_level"]}
    assert built["barracks_1"]["icon_image"] == "ui/buildings/icons/emp_barracks.png"
    assert built["tower"]["icon_image"] == "ui/buildings/icons/black_tower.png"
    assert built["barracks_2"]["icon_image"] is None
    assert ctx.images.stats["building_level.icon_image"]["referenced"] == 2
    for b in built.values():
        schemas.ENTITY_MODELS["building_level"].model_validate(b)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/model/test_image_fields.py -v`
Expected: FAIL with `KeyError: 'icon_image'` (or `card_image`)

- [ ] **Step 3: Add the schema fields**

In `twwiki/model/schemas.py`:
- `Effect`: after `icon_negative: str | None` add `icon_image: str | None` and `icon_negative_image: str | None`.
- `EffectBundle`: after `icon: str | None` add `icon_image: str | None`.
- `Ability`: after `icon: str` add `icon_image: str | None`.
- `Unit`: after `land_unit: str | None` add `card_image: str | None`.
- `Skill`: after `image: str` add `icon_image: str | None`.
- `Technology`: after `icon: str` add `icon_image: str | None`.
- `BuildingLevel`: after `short_description: str | None` add `icon_image: str | None`.
- `Trait`: after `icon: str` add `icon_image: str | None`.

- [ ] **Step 4: Resolve the fields in the builders**

`twwiki/model/abilities.py` — add `from .images import ABILITY_ICONS` after the context import; in `build()` after `"icon": r["icon_name"],` add:

```python
            "icon_image": ctx.images.resolve("ability.icon_image", r["icon_name"], ABILITY_ICONS),
```

`twwiki/model/characters.py` — add `from .images import SKILL_ICONS`; in `_skills()` after `"image": r["image_path"],` add:

```python
            "icon_image": ctx.images.resolve("skill.icon_image", r["image_path"], SKILL_ICONS),
```

`twwiki/model/technologies.py` — add `from .images import TECHNOLOGY_ICONS`; in `build()` after `"icon": r["icon_name"],` add:

```python
                "icon_image": ctx.images.resolve("technology.icon_image", r["icon_name"], TECHNOLOGY_ICONS),
```

`twwiki/model/effects.py` — add `from .images import EFFECT_ICONS`; in the effect dict after `"icon_negative": opt(r["icon_negative"]),` add:

```python
                "icon_image": ctx.images.resolve("effect.icon_image", r["icon"], EFFECT_ICONS),
                "icon_negative_image": ctx.images.resolve("effect.icon_negative_image", r["icon_negative"], EFFECT_ICONS),
```

and in the bundle dict after `"icon": opt(r["ui_icon"]),` add:

```python
                "icon_image": ctx.images.resolve("effect_bundle.icon_image", r["ui_icon"], EFFECT_ICONS),
```

`twwiki/model/items.py` — change the context import to `from .context import Context, by_key, grouped, opt`; in `_traits()` after `antitraits = grouped(...)` add:

```python
    categories = by_key(ctx, "trait_categories", "category")
```

and after `"icon": r["icon"],` add:

```python
            "icon_image": ctx.images.resolve(
                "trait.icon_image", categories[r["icon"]]["icon_path"] if r["icon"] in categories else None),
```

`twwiki/model/units.py` — add `from .images import UNIT_CARDS`; in `build()` after `unit_sets = resolve_unit_sets(ctx)` add:

```python
    # Faction-specific cards are out of scope; take the unit's default card.
    cards = {r["unit"]: r["unit_card"] for r in ctx.rows(
        "SELECT unit, unit_card FROM unit_variants WHERE faction = ''")} if ctx.table_exists("unit_variants") else {}
```

and after `"land_unit": lu["key"] if lu else None,` add:

```python
            "card_image": ctx.images.resolve("unit.card_image", cards.get(lu["key"]) if lu else None, UNIT_CARDS),
```

`twwiki/model/buildings.py` — add `from .images import BUILDING_ICONS`; replace `level_name` with:

```python
def _variant_name_key(level_key: str, v: dict) -> str:
    return ("building_culture_variants_name_" + level_key
            + (v["culture"] or "") + (v["subculture"] or "") + (v["faction"] or ""))


def level_variant(ctx: Context, level_key: str, variants: list[dict]) -> dict | None:
    """The variant that names a level (generic first); the first variant if none has text."""
    ordered = sorted(variants, key=_variant_order)
    for v in ordered:
        if ctx.loc.text(_variant_name_key(level_key, v)):
            return v
    return ordered[0] if ordered else None


def level_name(ctx: Context, level_key: str, variants: list[dict]) -> str | None:
    v = level_variant(ctx, level_key, variants)
    return ctx.loc.text(_variant_name_key(level_key, v)) if v else None
```

and in `build()` add after the `own_variants = sorted(...)` line:

```python
        variant = level_variant(ctx, key, own_variants)
```

and after `"short_description": short,` add:

```python
            "icon_image": ctx.images.resolve(
                "building_level.icon_image", opt(variant["icon"]) if variant else None, BUILDING_ICONS),
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/model/test_image_fields.py -v`
Expected: PASS (7 tests)

Run: `uv run pytest`
Expected: all tests pass (real-data tests build every entity with the new fields; images are unavailable there, so all image fields are null).

- [ ] **Step 6: Commit**

```bash
git add twwiki/model tests/model/test_image_fields.py
git commit -F - <<'EOF'
feat(model): resolve icon and unit card images on entities

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 4: Building chain availability

**Files:**
- Modify: `twwiki/model/schemas.py`, `twwiki/model/buildings.py`
- Test: `tests/model/test_buildings.py`, `tests/model/test_real_build.py`

**Interfaces:**
- Produces: `ChainAvailability(culture: Link | None, subculture: Link | None, faction: Link | None, campaign: str | None)`; `BuildingChain.availability: list[ChainAvailability]`. Links use relation `"availability"` with source `("building_chain", <key>)`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/model/test_buildings.py`:

```python
def test_chain_availability_scopes_sorted_and_deduplicated():
    ctx = building_context()
    ctx.con.execute("""CREATE TABLE building_chain_availability_sets AS SELECT * FROM (VALUES
        ('emp_barracks', 'bas_emp'), ('emp_barracks', 'bas_teb'), ('tower_chain', 'bas_emp')) t(building_chain, id)""")
    ctx.con.execute("""CREATE TABLE building_chain_availabilities AS SELECT * FROM (VALUES
        ('bas_teb', 'wh_main_emp_empire', 'wh_main_sc_teb_teb', '', 'wh3_main_combi'),
        ('bas_emp', 'wh_main_emp_empire', 'wh_main_sc_emp_empire', '', ''),
        ('bas_emp', 'wh_main_emp_empire', 'wh_main_sc_emp_empire', '', '')) t(set_id, culture, sub_culture, faction, campaign)""")
    ctx.links.register("culture", {"wh_main_emp_empire": "The Empire"})
    ctx.links.register("subculture", {"wh_main_sc_emp_empire": "The Empire", "wh_main_sc_teb_teb": "Tilea"})
    chains = {c["key"]: c for c in buildings.build(ctx)["building_chain"]}
    assert [(a["culture"]["key"], a["subculture"]["key"], a["faction"], a["campaign"])
            for a in chains["emp_barracks"]["availability"]] == [
        ("wh_main_emp_empire", "wh_main_sc_emp_empire", None, None),
        ("wh_main_emp_empire", "wh_main_sc_teb_teb", None, "wh3_main_combi"),
    ]
    assert len(chains["tower_chain"]["availability"]) == 1
    assert [l["key"] for l in ctx.links.referrers("culture", "wh_main_emp_empire", "availability")] == \
        ["emp_barracks", "tower_chain"]
    for c in chains.values():
        schemas.ENTITY_MODELS["building_chain"].model_validate(c)


def test_chain_availability_is_empty_without_tables():
    chains = buildings.build(building_context())["building_chain"]
    assert all(c["availability"] == [] for c in chains)
```

Append to `tests/model/test_real_build.py`:

```python
def test_empire_settlement_chain_availability(model):
    chain = model[1]["building_chain"]["wh_main_EMPIRE_settlement_major"]
    assert "wh_main_emp_empire" in {a["culture"]["key"] for a in chain["availability"] if a["culture"]}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/model/test_buildings.py -v`
Expected: FAIL with `KeyError: 'availability'`

- [ ] **Step 3: Add the schema**

In `twwiki/model/schemas.py`, add before `@entity("building_chain")`:

```python
class ChainAvailability(Strict):
    culture: Link | None
    subculture: Link | None
    faction: Link | None
    campaign: str | None
```

and add `availability: list[ChainAvailability]` to `BuildingChain` after `levels: list[Link]`.

- [ ] **Step 4: Build availability**

In `twwiki/model/buildings.py`, add `from collections import defaultdict` below `from __future__ import annotations`, and add this function before `build()`:

```python
def chain_availability(ctx: Context) -> dict[str, list[dict]]:
    """Which cultures, subcultures, factions and campaigns can build each chain."""
    if not (ctx.table_exists("building_chain_availability_sets")
            and ctx.table_exists("building_chain_availabilities")):
        return {}
    scopes: dict[str, set[tuple]] = defaultdict(set)
    for r in ctx.rows("""SELECT s.building_chain, a.culture, a.sub_culture, a.faction, a.campaign
                         FROM building_chain_availability_sets s
                         JOIN building_chain_availabilities a ON a.set_id = s.id"""):
        scopes[r["building_chain"]].add(
            (opt(r["culture"]), opt(r["sub_culture"]), opt(r["faction"]), opt(r["campaign"])))
    out: dict[str, list[dict]] = {}
    for chain, found in scopes.items():
        source = ("building_chain", chain)
        out[chain] = [{
            "culture": ctx.links.link("culture", culture, source=source, relation="availability"),
            "subculture": ctx.links.link("subculture", subculture, source=source, relation="availability"),
            "faction": ctx.links.link("faction", faction, source=source, relation="availability"),
            "campaign": campaign,
        } for culture, subculture, faction, campaign in sorted(found, key=lambda s: tuple(x or "" for x in s))]
    return out
```

In `build()`, inside `if ctx.require("building_chain", "building_chains"):` add `availability = chain_availability(ctx)` after `chain_levels = ...`, and add to the chain dict after `"levels": [...]`:

```python
                "availability": availability.get(key, []),
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/model/test_buildings.py tests/model/test_real_build.py -v`
Expected: PASS. If `test_missing_links_do_not_exceed_baseline` fails with new `building_chain.availability->…` counters, check each counted key really is absent from its table (for example `SELECT DISTINCT a.faction FROM building_chain_availabilities a LEFT JOIN factions f ON f.key = a.faction WHERE a.faction <> '' AND f.key IS NULL`). If they are genuine data gaps, add the counters with their current values to `tests/model/missing_links_baseline.json` and say so in the report; if they are not, fix the code.

Run: `uv run pytest`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add twwiki/model/schemas.py twwiki/model/buildings.py tests/model/test_buildings.py tests/model/test_real_build.py tests/model/missing_links_baseline.json
git commit -F - <<'EOF'
feat(model): add building chain availability by culture, faction and campaign

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 5: Regions and provinces

**Files:**
- Create: `twwiki/model/regions.py`
- Modify: `twwiki/model/schemas.py`, `twwiki/model/context.py`, `twwiki/model/build.py`
- Test: `tests/model/test_regions.py`, `tests/model/test_build.py`, `tests/model/test_real_build.py`

**Interfaces:**
- Consumes: `ctx.images.resolve` (Task 1).
- Produces:
  - `regions.region_stem(region_key: str) -> str | None`
  - `regions.index_special_templates(template_keys: Iterable[str]) -> dict[str, list[dict]]` (stem → `[{"key", "role", "variant"}]`)
  - `regions.ChainSets(ctx)` with `chains_of_set(set_key: str, seen: frozenset = frozenset()) -> set[str]` and `permitted(rows: list[dict]) -> list[str]`
  - `regions.catalog(ctx)`, `regions.build(ctx)` returning `{"region": [...], "province": [...]}`
  - `Context.manifest_sections: dict[str, dict]`; `ctx.manifest_sections["regions"] = {"special_templates_unmatched": int}`, written to the model manifest by `write_output`
  - Counters: `region.starting_owner->faction`, `region.province->province` (settlements only), `region.slot_template_resource->resources`; image count field `region.resource.icon_image`.

- [ ] **Step 1: Write the failing unit tests**

Create `tests/model/test_regions.py`:

```python
from pathlib import Path

from twwiki.model import regions, schemas
from twwiki.model.images import ImageIndex
from tests.model.fixtures import make_context, register_catalogs

ALTDORF = "wh3_main_combi_region_altdorf"
GRUNBURG = "wh3_main_combi_region_grunburg"
SEA = "wh3_main_combi_region_kraken_sea"
BEACON = "wh3_prologue_region_ice_canyon_beacon_fort"
COPHER = "wh3_main_chaos_region_copher"
CHAINS = ["emp_settlement", "tmb_settlement", "chaos_altar", "altdorf_palace", "walls_1", "walls_2",
          "emp_barracks", "loop_chain"]


def spr(region, **o):
    row = {"region": region, "campaign": "wh3_main_combi", "owning_faction": "", "faction_capital": False,
           "slot_cap": 4, "cultural_originator": "wh_main_sc_emp_empire"}
    row.update(o)
    return row


def permitted(template, chain="", chain_set="", super_chain="", remove=False):
    return {"slot_template": template, "chain": chain, "chain_set": chain_set, "super_chain": super_chain,
            "remove": remove}


def set_item(set_key, chain, remove=False):
    return {"set": set_key, "chain": chain, "super_chain": "", "remove": remove}


def regions_context():
    ctx = make_context({
        "regions": [{"key": k} for k in [ALTDORF, GRUNBURG, SEA, BEACON, COPHER]],
        "start_pos_regions": [
            spr(ALTDORF, owning_faction="100", faction_capital=True, slot_cap=10),
            spr(GRUNBURG, owning_faction="999"),
            spr(BEACON, campaign="wh3_main_prologue", cultural_originator="wh_main_sc_ksl_kislev"),
            spr(COPHER, campaign="wh3_main_chaos", owning_faction="100"),
        ],
        "start_pos_factions": [{"ID": "100", "faction": "wh_main_emp_empire"}],
        "region_to_province_junctions": [
            {"province": "reikland", "region": ALTDORF, "is_capital": True},
            {"province": "reikland", "region": GRUNBURG, "is_capital": False},
            {"province": "ice_canyon", "region": BEACON, "is_capital": False},
        ],
        "provinces": [{"key": "reikland"}, {"key": "ice_canyon"}],
        "regions_to_region_groups_junctions": [
            {"region": ALTDORF, "region_group": "b_group", "order": 1},
            {"region": ALTDORF, "region_group": "a_group", "order": 0},
        ],
        "slot_templates": [
            {"key": "wh_main_special_altdorf_primary", "resource": ""},
            {"key": "wh_main_special_altdorf_secondary", "resource": "res_oil"},
            {"key": "wh3_cp1_special_altdorf_secondary_obsidian", "resource": ""},
            {"key": "wh2_dlc14_special_copher_port", "resource": ""},
            {"key": "wh3_dlc20_special_ice_canyon_beacon_fort_primary", "resource": "res_missing"},
            {"key": "wh2_main_special_nowhere_primary", "resource": ""},
            {"key": "generic_primary", "resource": ""},
        ],
        "slot_template_permitted_building_chains": [
            permitted("wh_main_special_altdorf_primary", chain_set="altdorf_set"),
            permitted("wh_main_special_altdorf_primary", super_chain="walls"),
            permitted("wh_main_special_altdorf_primary", chain="tmb_settlement", remove=True),
            permitted("wh_main_special_altdorf_secondary", chain="emp_barracks"),
        ],
        "building_chain_sets": [
            {"key": "generic_major", "parent_set": ""},
            {"key": "altdorf_set", "parent_set": "generic_major"},
            {"key": "loop_a", "parent_set": "loop_b"},
            {"key": "loop_b", "parent_set": "loop_a"},
        ],
        "building_chain_set_items": [
            set_item("generic_major", "emp_settlement"),
            set_item("generic_major", "tmb_settlement"),
            set_item("generic_major", "chaos_altar"),
            set_item("altdorf_set", "chaos_altar", remove=True),
            set_item("altdorf_set", "altdorf_palace"),
            set_item("loop_a", "loop_chain"),
        ],
        "building_chains": [{"key": k, "building_superchain": "walls" if k.startswith("walls") else ""}
                            for k in CHAINS],
        "resources": [{"key": "res_oil", "icon_filepath": "ui\\campaign ui\\effect_bundles\\resource_oil.png"}],
    }, loc={
        f"regions_onscreen_{ALTDORF}": "Altdorf",
        "provinces_onscreen_reikland": "Reikland",
        "resources_onscreen_text_res_oil": "Oil",
    })
    register_catalogs(ctx, regions)
    ctx.links.register("faction", {"wh_main_emp_empire": "Reikland"})
    ctx.links.register("subculture", {"wh_main_sc_emp_empire": "The Empire", "wh_main_sc_ksl_kislev": "Kislev"})
    ctx.links.register("building_chain", {k: None for k in CHAINS})
    return ctx


def built(ctx):
    out = regions.build(ctx)
    return {r["key"]: r for r in out["region"]}, {p["key"]: p for p in out["province"]}


def test_region_stem():
    assert regions.region_stem(ALTDORF) == "altdorf"
    assert regions.region_stem(BEACON) == "ice_canyon_beacon_fort"
    assert regions.region_stem("no_marker_here") is None


def test_index_special_templates_reads_role_and_variant():
    index = regions.index_special_templates([
        "wh3_cp1_special_altdorf_secondary_obsidian",
        "wh2_dlc14_special_copher_port",
        "wh3_dlc20_special_ashrak_major_secondary_obsidian",
    ])
    assert index["altdorf"] == [{"key": "wh3_cp1_special_altdorf_secondary_obsidian", "role": "secondary",
                                 "variant": "obsidian"}]
    assert index["copher"] == [{"key": "wh2_dlc14_special_copher_port", "role": "port", "variant": None}]
    assert index["ashrak_major"][0]["variant"] == "obsidian"
    assert "ashrak" not in index


def test_chain_sets_apply_parents_removals_and_survive_cycles():
    chain_sets = regions.ChainSets(regions_context())
    assert chain_sets.chains_of_set("altdorf_set") == {"emp_settlement", "tmb_settlement", "altdorf_palace"}
    assert chain_sets.chains_of_set("loop_a") == {"loop_chain"}
    assert chain_sets.chains_of_set("unknown_set") == set()


def test_altdorf():
    ctx = regions_context()
    by_region, _ = built(ctx)
    altdorf = by_region[ALTDORF]
    assert altdorf["name"] == "Altdorf" and altdorf["campaign"] == "wh3_main_combi"
    assert altdorf["is_settlement"] is True
    assert (altdorf["province"]["key"], altdorf["province"]["name"]) == ("reikland", "Reikland")
    assert altdorf["is_province_capital"] is True and altdorf["is_faction_capital"] is True
    assert altdorf["starting_owner"]["key"] == "wh_main_emp_empire"
    assert altdorf["slot_cap"] == 10
    assert altdorf["cultural_originator"]["key"] == "wh_main_sc_emp_empire"
    assert altdorf["region_groups"] == ["a_group", "b_group"]
    assert altdorf["template_source"] == "special"
    assert [(t["key"], t["role"], t["variant"]) for t in altdorf["slot_templates"]] == [
        ("wh_main_special_altdorf_primary", "primary", None),
        ("wh3_cp1_special_altdorf_secondary_obsidian", "secondary", "obsidian"),
        ("wh_main_special_altdorf_secondary", "secondary", None),
    ]
    primary, _, secondary = altdorf["slot_templates"]
    assert [c["key"] for c in primary["permitted_chains"]] == ["altdorf_palace", "emp_settlement", "walls_1", "walls_2"]
    assert primary["resource"] is None
    assert secondary["resource"] == {"key": "res_oil", "name": "Oil", "icon_image": None}
    assert [c["key"] for c in secondary["permitted_chains"]] == ["emp_barracks"]
    schemas.ENTITY_MODELS["region"].model_validate(altdorf)


def test_generic_sea_prologue_port_and_counted_gaps():
    ctx = regions_context()
    by_region, _ = built(ctx)
    assert by_region[GRUNBURG]["starting_owner"] is None
    assert by_region[GRUNBURG]["template_source"] == "generic" and by_region[GRUNBURG]["slot_templates"] == []
    sea = by_region[SEA]
    assert (sea["is_settlement"], sea["campaign"], sea["province"], sea["slot_cap"], sea["cultural_originator"]) == \
        (False, None, None, None, None)
    assert by_region[BEACON]["slot_templates"][0]["resource"] == {"key": "res_missing", "name": None, "icon_image": None}
    assert by_region[COPHER]["slot_templates"][0]["role"] == "port"
    assert ctx.links.missing["region.starting_owner->faction"] == 1
    assert ctx.links.missing["region.province->province"] == 1
    assert ctx.links.missing["region.slot_template_resource->resources"] == 1
    assert ctx.manifest_sections["regions"] == {"special_templates_unmatched": 1}
    for region in by_region.values():
        schemas.ENTITY_MODELS["region"].model_validate(region)


def test_provinces():
    _, by_province = built(regions_context())
    reikland = by_province["reikland"]
    assert reikland["name"] == "Reikland" and reikland["campaign"] == "wh3_main_combi"
    assert [r["key"] for r in reikland["regions"]] == [ALTDORF, GRUNBURG]
    assert reikland["capital"]["key"] == ALTDORF
    ice = by_province["ice_canyon"]
    assert ice["capital"] is None and ice["campaign"] == "wh3_main_prologue"
    for province in by_province.values():
        schemas.ENTITY_MODELS["province"].model_validate(province)


def test_resource_icon_image_resolves_when_images_exist():
    ctx = regions_context()
    ctx.images = ImageIndex(Path("images"), ["ui/campaign ui/effect_bundles/resource_oil.png"])
    by_region, _ = built(ctx)
    assert by_region[ALTDORF]["slot_templates"][2]["resource"]["icon_image"] == \
        "ui/campaign ui/effect_bundles/resource_oil.png"
```

Append to `tests/model/test_build.py`:

```python
def test_write_output_includes_manifest_sections(tmp_path):
    ctx = make_context({"dummy": [{"a": 1}]})
    ctx.manifest_sections["regions"] = {"special_templates_unmatched": 2}
    entities = build.build_all(ctx, modules=[fake_module()])
    out = build.write_output(ctx, entities, tmp_path, "abc123")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["regions"] == {"special_templates_unmatched": 2}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/model/test_regions.py tests/model/test_build.py -v`
Expected: FAIL with `ImportError: cannot import name 'regions'`

- [ ] **Step 3: Add schemas and the context field**

In `twwiki/model/schemas.py`, change the imports to:

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict
```

and add before the `# ---- Factions, cultures, ...` section:

```python
# ---- Regions ---------------------------------------------------------------

class SlotResource(Strict):
    key: str
    name: str | None
    icon_image: str | None


class SlotTemplate(Strict):
    key: str
    role: Literal["primary", "secondary", "port"]
    variant: str | None
    resource: SlotResource | None
    permitted_chains: list[Link]


@entity("region")
class Region(Strict):
    key: str
    name: str | None
    campaign: str | None
    is_settlement: bool
    province: Link | None
    is_province_capital: bool
    starting_owner: Link | None
    is_faction_capital: bool
    slot_cap: int | None
    cultural_originator: Link | None
    region_groups: list[str]
    template_source: Literal["special", "generic"]
    slot_templates: list[SlotTemplate]


@entity("province")
class Province(Strict):
    key: str
    name: str | None
    campaign: str | None
    regions: list[Link]
    capital: Link | None
```

In `twwiki/model/context.py`, add to `Context` after the `images` field:

```python
    manifest_sections: dict[str, dict] = field(default_factory=dict)
```

- [ ] **Step 4: Implement `twwiki/model/regions.py`**

```python
"""Campaign regions and provinces, from the start-position tables.

Which slot template (and so which resource and buildings) an ordinary
settlement gets is stored only in startpos.esf. Special settlements have slot
templates named after the region, and those are matched here. Every other
settlement is "generic": the web app shows the chains its culture can build.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

from .context import Context, by_key, grouped, opt

SPECIAL = "_special_"
ROLE = re.compile(r"_(primary|secondary|port)(?=_|$)")
ROLE_ORDER = {"primary": 0, "secondary": 1, "port": 2}


def region_stem(region_key: str) -> str | None:
    """wh3_main_combi_region_altdorf -> altdorf."""
    if "_region_" not in region_key:
        return None
    return region_key.split("_region_", 1)[1] or None


def index_special_templates(template_keys: Iterable[str]) -> dict[str, list[dict]]:
    """Map every stem a template key can be read as to that reading.

    A key matches stem S when it ends with _special_S_<role> optionally
    followed by _<variant>; S itself may contain underscores, so every
    _special_ and role occurrence is considered.
    """
    out: dict[str, list[dict]] = defaultdict(list)
    for key in sorted(template_keys):
        start = key.find(SPECIAL)
        while start != -1:
            rest = key[start + len(SPECIAL):]
            for m in ROLE.finditer(rest):
                stem = rest[:m.start()]
                if stem:
                    out[stem].append({"key": key, "role": m.group(1), "variant": rest[m.end() + 1:] or None})
            start = key.find(SPECIAL, start + 1)
    return out


class ChainSets:
    """Resolve building chain sets (parent sets, superchains, removals) to chain keys."""

    def __init__(self, ctx: Context):
        self.superchains: dict[str, set[str]] = defaultdict(set)
        if ctx.table_exists("building_chains"):
            for r in ctx.rows("SELECT key, building_superchain FROM building_chains"):
                if opt(r["building_superchain"]):
                    self.superchains[r["building_superchain"]].add(r["key"])
        self.parents = {k: opt(r["parent_set"]) for k, r in by_key(ctx, "building_chain_sets", "key").items()}
        self.items = grouped(ctx, "building_chain_set_items", "set", "chain, super_chain")

    def chains_of_set(self, set_key: str, seen: frozenset = frozenset()) -> set[str]:
        if set_key in seen:
            return set()
        seen = seen | {set_key}
        parent = self.parents.get(set_key)
        added = self.chains_of_set(parent, seen) if parent else set()
        return self._apply(self.items.get(set_key, []), seen, added)

    def permitted(self, rows: list[dict]) -> list[str]:
        """Chains a slot template allows, from its permitted-chain rows."""
        return sorted(self._apply(rows, frozenset(), set()))

    def _apply(self, rows: list[dict], seen: frozenset, added: set[str]) -> set[str]:
        removed: set[str] = set()
        for row in rows:
            (removed if row["remove"] else added).update(self._row_chains(row, seen))
        return added - removed

    def _row_chains(self, row: dict, seen: frozenset) -> set[str]:
        chains: set[str] = set()
        if opt(row.get("chain")):
            chains.add(row["chain"])
        if opt(row.get("super_chain")):
            chains |= self.superchains.get(row["super_chain"], set())
        if opt(row.get("chain_set")):
            chains |= self.chains_of_set(row["chain_set"], seen)
        return chains


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {"region": {}, "province": {}}
    if ctx.table_exists("regions"):
        for r in ctx.rows("SELECT key FROM regions"):
            out["region"][r["key"]] = ctx.catalog_name("region", f"regions_onscreen_{r['key']}")
    if ctx.table_exists("provinces"):
        for r in ctx.rows("SELECT key FROM provinces"):
            out["province"][r["key"]] = ctx.catalog_name("province", f"provinces_onscreen_{r['key']}")
    return out


def build(ctx: Context) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {"region": [], "province": []}
    start = by_key(ctx, "start_pos_regions", "region")
    if ctx.require("region", "regions"):
        out["region"] = _regions(ctx, start)
    if ctx.require("province", "provinces"):
        out["province"] = _provinces(ctx, start)
    return out


def _regions(ctx: Context, start: dict[str, dict]) -> list[dict]:
    faction_by_id = {k: r["faction"] for k, r in by_key(ctx, "start_pos_factions", "ID").items()}
    junctions = by_key(ctx, "region_to_province_junctions", "region")
    groups = grouped(ctx, "regions_to_region_groups_junctions", "region", '"order", region_group')
    templates = by_key(ctx, "slot_templates", "key")
    resources = by_key(ctx, "resources", "key")
    permitted_rows = grouped(ctx, "slot_template_permitted_building_chains", "slot_template",
                             "chain, chain_set, super_chain")
    special = index_special_templates(k for k in templates if SPECIAL in k)
    chain_sets = ChainSets(ctx)
    chains_for: dict[str, list[str]] = {}
    matched: set[str] = set()

    out = []
    for r in ctx.rows("SELECT key FROM regions ORDER BY key"):
        key = r["key"]
        source = ("region", key)
        s = start.get(key)
        j = junctions.get(key)
        stem = region_stem(key)
        matches = sorted(special.get(stem, []) if stem else [], key=lambda m: (ROLE_ORDER[m["role"]], m["key"]))
        slot_templates = []
        for m in matches:
            matched.add(m["key"])
            if m["key"] not in chains_for:
                chains_for[m["key"]] = chain_sets.permitted(permitted_rows.get(m["key"], []))
            slot_templates.append({
                "key": m["key"],
                "role": m["role"],
                "variant": m["variant"],
                "resource": _resource(ctx, opt(templates[m["key"]]["resource"]), resources),
                "permitted_chains": [ctx.links.link("building_chain", c, source=source, relation="permitted_chains")
                                     for c in chains_for[m["key"]]],
            })
        if s is not None and j is None:
            ctx.links.missing["region.province->province"] += 1
        out.append({
            "key": key,
            "name": ctx.links.name("region", key),
            "campaign": s["campaign"] if s else None,
            "is_settlement": s is not None,
            "province": ctx.links.link("province", j["province"], source=source, relation="province") if j else None,
            "is_province_capital": bool(j and j["is_capital"]),
            "starting_owner": _owner(ctx, s, faction_by_id, source),
            "is_faction_capital": bool(s and s["faction_capital"]),
            "slot_cap": s["slot_cap"] if s else None,
            "cultural_originator": ctx.links.link("subculture", opt(s["cultural_originator"]), source=source,
                                                  relation="cultural_originator") if s else None,
            "region_groups": [g["region_group"] for g in groups.get(key, [])],
            "template_source": "special" if slot_templates else "generic",
            "slot_templates": slot_templates,
        })
    ctx.manifest_sections["regions"] = {
        "special_templates_unmatched": sum(1 for k in templates if SPECIAL in k and k not in matched)}
    return out


def _owner(ctx: Context, s: dict | None, faction_by_id: dict[str, str], source: tuple[str, str]) -> dict | None:
    owner_id = opt(s["owning_faction"]) if s else None
    if owner_id is None:
        return None
    faction = faction_by_id.get(owner_id)
    if faction is None:
        ctx.links.missing["region.starting_owner->faction"] += 1
        return None
    return ctx.links.link("faction", faction, source=source, relation="starting_owner")


def _resource(ctx: Context, key: str | None, resources: dict[str, dict]) -> dict | None:
    if key is None:
        return None
    row = resources.get(key)
    if row is None:
        ctx.links.missing["region.slot_template_resource->resources"] += 1
    return {
        "key": key,
        "name": ctx.loc.text(f"resources_onscreen_text_{key}"),
        "icon_image": ctx.images.resolve("region.resource.icon_image", row["icon_filepath"] if row else None),
    }


def _provinces(ctx: Context, start: dict[str, dict]) -> list[dict]:
    members = grouped(ctx, "region_to_province_junctions", "province", "region")
    out = []
    for r in ctx.rows("SELECT key FROM provinces ORDER BY key"):
        key = r["key"]
        source = ("province", key)
        rows = members.get(key, [])
        capital = next((j["region"] for j in rows if j["is_capital"]), None)
        out.append({
            "key": key,
            "name": ctx.links.name("province", key),
            "campaign": next((start[j["region"]]["campaign"] for j in rows if j["region"] in start), None),
            "regions": [ctx.links.link("region", j["region"], source=source, relation="regions") for j in rows],
            "capital": ctx.links.link("region", capital, source=source, relation="capital"),
        })
    return out
```

- [ ] **Step 5: Register the module and write manifest sections**

In `twwiki/model/build.py`:
- Change the module import to `from . import abilities, buildings, characters, effects, factions, items, regions, technologies, units`.
- Change `MODULES` to `[effects, abilities, units, characters, technologies, buildings, items, factions, regions]`.
- Add to `INDEX_FIELDS`: `"region": ["campaign", "is_settlement", "template_source"],` and `"province": ["campaign"],`.
- In `write_output`, directly after the `manifest = {...}` dict literal, add:

```python
    manifest.update(ctx.manifest_sections)
```

- [ ] **Step 6: Run unit tests**

Run: `uv run pytest tests/model/test_regions.py tests/model/test_build.py -v`
Expected: PASS

- [ ] **Step 7: Add real-data checks**

In `tests/model/test_real_build.py`, add `"region": 945, "province": 316,` to `EXPECTED_COUNTS`, and append:

```python
def test_altdorf_and_reikland(model):
    by_type = model[1]
    altdorf = by_type["region"]["wh3_main_combi_region_altdorf"]
    assert altdorf["name"] == "Altdorf"
    assert altdorf["province"]["key"] == "wh3_main_combi_province_reikland" and altdorf["is_province_capital"]
    assert altdorf["starting_owner"]["key"] == "wh_main_emp_empire" and altdorf["is_faction_capital"]
    assert altdorf["slot_cap"] == 10 and altdorf["template_source"] == "special"
    templates = {t["key"]: t for t in altdorf["slot_templates"]}
    assert {"wh_main_special_altdorf_primary", "wh_main_special_altdorf_secondary"} <= set(templates)
    primary = [c["key"] for c in templates["wh_main_special_altdorf_primary"]["permitted_chains"]]
    assert len(primary) == 54 and "wh2_dlc17_bst_special_settlement_altdorf" in primary
    assert len(templates["wh_main_special_altdorf_secondary"]["permitted_chains"]) == 469
    assert by_type["province"]["wh3_main_combi_province_reikland"]["capital"]["key"] == "wh3_main_combi_region_altdorf"


def test_grom_peak_resources(model):
    grom = model[1]["region"]["wh3_main_combi_region_grom_peak"]
    resources = {t["key"]: t["resource"] for t in grom["slot_templates"]}
    assert resources["wh2_dlc15_special_grom_peak_secondary"]["key"] == "res_rom_oil"
    assert resources["wh3_main_special_grom_peak_primary"]["key"] == "res_stone_trolls"
    assert resources["wh3_main_special_grom_peak_primary"]["name"] == "Stone Trolls Den"


def test_sea_region_is_not_a_settlement(model):
    sea = model[1]["region"]["wh3_main_chaos_region_kraken_sea"]
    assert sea["is_settlement"] is False and sea["province"] is None
```

- [ ] **Step 8: Run the full suite**

Run: `uv run pytest`
Expected: all tests pass. If `test_missing_links_do_not_exceed_baseline` fails with new `region.…` counters, verify each is a genuine data gap with a query (e.g. `SELECT DISTINCT p.chain FROM slot_template_permitted_building_chains p LEFT JOIN building_chains c ON c.key = p.chain WHERE p.chain <> '' AND c.key IS NULL`), then add the counters with their current values to `tests/model/missing_links_baseline.json` and list them in the report. `region.starting_owner->faction` and `region.province->province` are expected to be 0 on build fb20553df5af; a non-zero value there is a bug.

- [ ] **Step 9: Commit**

```bash
git add twwiki/model tests/model/test_regions.py tests/model/test_build.py tests/model/test_real_build.py tests/model/missing_links_baseline.json
git commit -F - <<'EOF'
feat(model): add region and province entities with special slot templates

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 6: Copy images into the model output

**Files:**
- Modify: `twwiki/model/build.py` (`MODEL_VERSION`, `write_output`, `run`), `twwiki/model/__main__.py`
- Test: `tests/model/test_build.py`

**Interfaces:**
- Consumes: `ImageIndex.scan/resolve/copy_used/manifest`, `inline_targets`, `INLINE_ICONS` (Task 1); `ctx.manifest_sections` (Task 5).
- Produces: `run(db_path: Path, out_root: Path, raw_root: Path) -> Path`; `model/<build_id>/images/<path>` for every resolved image; `model/<build_id>/images/inline.json` (`{target: path | null}`, sorted keys); manifest key `images` = `ImageIndex.manifest(files_copied)`; `MODEL_VERSION = 2`.

- [ ] **Step 1: Write the failing tests**

In `tests/model/test_build.py`, add imports at the top:

```python
import duckdb

from twwiki.model.images import ImageIndex
```

and append:

```python
def write_images(root, *paths):
    for rel in paths:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(b"png")


def test_write_output_copies_used_images_and_writes_inline_map(tmp_path):
    raw = tmp_path / "raw_images"
    write_images(raw, "ui/units/icons/gs.png", "ui/units/icons/unused.png", "ui/skins/default/icon_hero.png")
    ctx = make_context({"dummy": [{"a": 1}]})
    ctx.images = ImageIndex.scan(raw)
    assert ctx.images.resolve("unit.card_image", "gs", ("ui/units/icons",)) == "ui/units/icons/gs.png"
    entities = build.build_all(ctx, modules=[fake_module(flags_path="[[img:icon_hero]] [[img:icon_gone]]")])

    out = build.write_output(ctx, entities, tmp_path / "model", "abc123")

    assert (out / "images" / "ui/units/icons/gs.png").read_bytes() == b"png"
    assert (out / "images" / "ui/skins/default/icon_hero.png").exists()
    assert not (out / "images" / "ui/units/icons/unused.png").exists()
    assert json.loads((out / "images" / "inline.json").read_text(encoding="utf-8")) == {
        "icon_gone": None, "icon_hero": "ui/skins/default/icon_hero.png"}
    images = json.loads((out / "manifest.json").read_text(encoding="utf-8"))["images"]
    assert images["available"] is True and images["files_copied"] == 2
    assert images["fields"]["unit.card_image"] == {"referenced": 1, "resolved": 1, "missing": 0, "ambiguous": 0}
    assert images["fields"]["inline"] == {"referenced": 2, "resolved": 1, "missing": 1, "ambiguous": 0}


def test_write_output_without_images_marks_them_unavailable(tmp_path):
    ctx = make_context({"dummy": [{"a": 1}]})
    entities = build.build_all(ctx, modules=[fake_module(flags_path="[[img:icon_hero]]")])
    out = build.write_output(ctx, entities, tmp_path, "abc123")
    assert json.loads((out / "images" / "inline.json").read_text(encoding="utf-8")) == {"icon_hero": None}
    assert json.loads((out / "manifest.json").read_text(encoding="utf-8"))["images"] == {
        "available": False, "files_copied": 0, "fields": {}}


def test_image_copy_failure_fails_the_build_and_publishes_nothing(tmp_path):
    raw = tmp_path / "raw_images"
    write_images(raw, "ui/units/icons/gs.png")
    ctx = make_context({"dummy": [{"a": 1}]})
    ctx.images = ImageIndex.scan(raw)
    ctx.images.resolve("unit.card_image", "ui/units/icons/gs.png")
    (raw / "ui/units/icons/gs.png").unlink()
    entities = build.build_all(ctx, modules=[fake_module()])
    with pytest.raises(OSError):
        build.write_output(ctx, entities, tmp_path / "model", "abc123")
    assert not (tmp_path / "model" / "abc123").exists()


def test_run_reads_images_from_the_raw_build(tmp_path):
    db = tmp_path / "t.duckdb"
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE loc (key VARCHAR, text VARCHAR)")
    con.execute("CREATE TABLE _build AS SELECT 'abc123' AS build_id")
    con.close()
    write_images(tmp_path / "raw" / "abc123" / "images", "ui/skins/default/x.png")

    out = build.run(db, tmp_path / "model", tmp_path / "raw")

    assert out == tmp_path / "model" / "abc123"
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["images"]["available"] is True and manifest["model_version"] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/model/test_build.py -v`
Expected: FAIL (`inline.json` missing, `run()` takes 2 positional arguments)

- [ ] **Step 3: Implement**

In `twwiki/model/build.py`:

1. Add `from .images import INLINE_ICONS, ImageIndex, inline_targets` after `from .context import Context`.
2. Set `MODEL_VERSION = 2`.
3. In `write_output`, change `for sub in ("entities", "index", "schema"):` to `for sub in ("entities", "index", "schema", "images"):`.
4. In `write_output`, directly before `manifest = {`, add:

```python
    inline = {target: ctx.images.resolve("inline", target, INLINE_ICONS) for target in inline_targets(entities)}
    (staging / "images" / "inline.json").write_text(
        json.dumps(inline, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    files_copied = ctx.images.copy_used(staging / "images")
```

5. Add `"images": ctx.images.manifest(files_copied),` to the manifest dict after `"partial": ctx.partial,`.
6. Replace `run` with:

```python
def run(db_path: Path, out_root: Path, raw_root: Path) -> Path:
    started = time.perf_counter()
    ctx = Context.open(db_path)
    try:
        build_id = ctx.con.execute("SELECT build_id FROM _build").fetchone()[0]
        ctx.images = ImageIndex.scan(Path(raw_root) / build_id / "images")
        if not ctx.images.available:
            log.warning("no images at %s; image fields will be null", Path(raw_root) / build_id / "images")
        entities = build_all(ctx)
        absent = sorted(set(ENTITY_MODELS) - set(entities))
        if absent:
            raise ModelBuildError(f"entity types not built: {absent}")
        out = write_output(ctx, entities, out_root, build_id)
    finally:
        ctx.con.close()
    log.info("model %s written to %s in %.0fs; missing names %d, missing links %d, images copied %d, partial types %s",
             build_id, out, time.perf_counter() - started, sum(ctx.missing_names.values()),
             sum(ctx.links.missing.values()), len(ctx.images.used), sorted(ctx.partial) or "none")
    return out
```

In `twwiki/model/__main__.py`, replace the `run(...)` call with:

```python
    run(Path(cfg.paths.db_path), Path(getattr(cfg.paths, "model_dir", "./model")), Path(cfg.paths.raw_dir))
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/model/test_build.py -v`
Expected: PASS

Run: `uv run pytest`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add twwiki/model/build.py twwiki/model/__main__.py tests/model/test_build.py
git commit -F - <<'EOF'
feat(model): copy referenced images and inline icon map into the model output

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 7: Real extraction, image baseline and docs

**Files:**
- Modify: `tests/model/test_real_build.py`, `README.md`
- Create: `tests/model/missing_images_baseline.json`
- Generated (git-ignored): `raw/<new build_id>/`, `twwiki.duckdb`, `model/<new build_id>/`

**Interfaces:**
- Consumes: everything above.
- Produces: a real build with images; image gap baseline; documentation.

This task needs rpfm_ui open (it keeps rpfm_server alive) with the Warhammer 3 dependency cache generated. Do not change RPFM settings. Extraction re-reads all 1,521 tables and ~20,000 image files; run it with a 10-minute timeout or in the background.

- [ ] **Step 1: Check the server is up**

Run: `curl -s http://127.0.0.1:45127/version`
Expected: JSON containing `"version"`. If the request fails, stop and report BLOCKED: "rpfm_server is not running; open rpfm_ui".

- [ ] **Step 2: Extract**

Run: `uv run python -m twwiki.extract`
Expected: a new `raw/<build_id>/` (different from `fb20553df5af`, because the image packs are now part of the id) whose `manifest.json` has `"undecodable": []`, `images.failed_folders == []` and `images.folders` counts close to: ability_icons 2399, technologies 1506, skills 793, effect_bundles 1049, units/icons 1023, buildings/icons 1363, ui/skins 12075. Check with:

```bash
uv run python -c "import json,sys; from pathlib import Path; from twwiki.load import latest_build; m=json.loads((latest_build(Path('raw'))/'manifest.json').read_text(encoding='utf-8')); print(m['build_id'], len(m['tables']), m['undecodable'], m['images'])"
```

If any folder failed, stop and report the error text.

- [ ] **Step 3: Load and build the model**

Run: `uv run python -m twwiki.load`
Then: `uv run python -m twwiki.model`
Expected: log line `model <build_id> written to model/<build_id> ... images copied N` with N in the thousands, and `model/<build_id>/images/inline.json` present.

- [ ] **Step 4: Point the real-data tests at the images**

In `tests/model/test_real_build.py`:
- Add `from twwiki.model.images import ImageIndex` to the imports.
- Add constants below `BASELINE`:

```python
RAW = Path("raw")
IMAGES_BASELINE = Path(__file__).parent / "missing_images_baseline.json"
```

- Replace the `model` fixture with:

```python
@pytest.fixture(scope="module")
def model():
    ctx = Context.open(DB)
    build_id = ctx.con.execute("SELECT build_id FROM _build").fetchone()[0]
    ctx.images = ImageIndex.scan(RAW / build_id / "images")
    entities = build_all(ctx)
    yield ctx, {t: {e["key"]: e for e in rows} for t, rows in entities.items()}
    ctx.con.close()


def require_images(ctx):
    if not ctx.images.available:
        pytest.skip("no raw images for this build; run extract with images.folders configured")
```

- Append:

```python
def test_unit_card_and_ability_icon_images(model):
    ctx, by_type = model
    require_images(ctx)
    assert by_type["unit"]["wh_main_emp_inf_greatswords"]["card_image"] == "ui/units/icons/wh_main_emp_greatswords.png"
    assert by_type["ability"]["wh2_dlc09_army_abilities_barrage_of_the_legion"]["icon_image"] == \
        "ui/battle ui/ability_icons/wh2_dlc09_army_abilities_barrage_of_the_legion.png"


def test_missing_images_do_not_exceed_baseline(model):
    ctx, _ = model
    require_images(ctx)
    baseline = json.loads(IMAGES_BASELINE.read_text(encoding="utf-8"))
    worse = {}
    for field, counts in ctx.images.stats.items():
        allowed = baseline.get(field, {})
        over = {k: (counts[k], allowed.get(k, 0)) for k in ("missing", "ambiguous") if counts[k] > allowed.get(k, 0)}
        if over:
            worse[field] = over
    assert worse == {}, f"image gaps above baseline (now, baseline): {worse}"
```

- [ ] **Step 5: Generate the image baseline**

Run:

```bash
uv run python -c "import json; from pathlib import Path; from twwiki.model.build import build_all; from twwiki.model.context import Context; from twwiki.model.images import ImageIndex; ctx = Context.open('twwiki.duckdb'); bid = ctx.con.execute('SELECT build_id FROM _build').fetchone()[0]; ctx.images = ImageIndex.scan(Path('raw') / bid / 'images'); build_all(ctx); Path('tests/model/missing_images_baseline.json').write_text(json.dumps({f: {'missing': c['missing'], 'ambiguous': c['ambiguous']} for f, c in sorted(ctx.images.stats.items())}, indent=2) + '\n', encoding='utf-8'); print(json.dumps({f: dict(c) for f, c in sorted(ctx.images.stats.items())}, indent=1))"
```

Expected: printed counts per field. Sanity check against the spec's findings (distinct values there, references here, so only proportions compare): `ability.icon_image`, `technology.icon_image`, `building_level.icon_image` and `trait.icon_image` resolve almost everything; `unit.card_image` resolves most. If a field resolves nothing, stop and investigate rather than baselining it.

- [ ] **Step 6: Document**

In `README.md`:

1. Replace the pipeline diagram block with:

```
rpfm_server (WS) → raw/<build_id>/{files,images}/ → twwiki.duckdb → model/<build_id>/ → web app
     extract.py            (immutable)               load.py        model (Python)
```

2. In "Why this shape", replace the sentence starting `The id is derived from` with:

```
The id is derived from the size and mtime of the packs the data came from
(`db.pack`, `local_en.pack`, and the UI packs holding the exported images).
```

3. Add a section after "Raw file format":

```markdown
## Images

`config.yaml` `images.folders` lists in-game folders exported as they are to
`raw/<build_id>/images/<in-game path>` (all PNG for what the wiki uses). A
folder that fails to export is listed under `images.failed_folders` in the raw
manifest and extraction carries on.

The model resolves each image reference in the tables (bare names, names with
`.png`, full paths with backslashes) against those files, copies only the
referenced ones to `model/<build_id>/images/`, and writes
`images/inline.json` mapping every `[[img:…]]` text icon to a file or null.
Image fields end in `_image`. The manifest's `images` section counts
referenced, resolved, missing and ambiguous references per field. Without
`raw/<build_id>/images` the build still succeeds with every image field null.
```

4. In "Game data model", change `for 17 types (units, characters` to `for 19 types (units, characters`, change `difficulty levels, campaign variables).` to `difficulty levels, campaign variables, regions, provinces).`, and add this bullet directly after that `entities/<type>.jsonl` bullet (before the `index/<type>.json` bullet):

```markdown
- Regions and provinces come from the start-position tables: owner at
  campaign start, capitals, slot cap and province. Slot templates, resources
  and permitted building chains are known only for special settlements (their
  templates are named after the region); every other settlement is marked
  `template_source: "generic"`. Exact slots for those need `startpos.esf`,
  which is not decoded.
```

5. In the tests paragraph, after the sentence about `missing_links_baseline.json`, add:

```
Regenerate `tests/model/missing_images_baseline.json` the same way, only after
checking why images went missing.
```

- [ ] **Step 7: Run the full suite**

Run: `uv run pytest`
Expected: all tests pass, including the image tests (not skipped).

- [ ] **Step 8: Commit**

```bash
git add tests/model/test_real_build.py tests/model/missing_images_baseline.json README.md
git commit -F - <<'EOF'
test(model): check real images against a baseline; document images and regions

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```
