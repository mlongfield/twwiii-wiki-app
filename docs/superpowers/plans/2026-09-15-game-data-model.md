# Game Data Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `model` pipeline stage that turns `twwiki.duckdb` into curated, schema-validated entity files in `model/<build_id>/` for the web app.

**Architecture:** A `twwiki/model/` package. Each domain module exposes `catalog(ctx)` (entity keys and names, registered first so every link can be resolved) and `build(ctx)` (entity dicts). `build.py` runs all catalogs, then all builders, fills reverse links from the link registry, validates every entity with Pydantic, and writes JSON Lines, indexes, JSON Schemas and a manifest to a `.partial` directory that is renamed on success.

**Tech Stack:** Python 3.13 (uv), DuckDB, Pydantic v2, pytest.

**Spec:** `docs/superpowers/specs/2026-09-15-game-data-model-design.md`

## Global Constraints

- Read `twwiki.duckdb` read-only. Never write to `raw/` or the database.
- Output directory: `model/<build_id>/`, where `build_id` comes from the `_build` table. Write to `model/<build_id>.partial/` and rename only when every step succeeds; remove an existing `.partial` first.
- Output files: `entities/<type>.jsonl` (one entity per line), `index/<type>.json`, `schema/<type>.schema.json`, `manifest.json`.
- Entity types (17): `unit`, `character`, `skill`, `ability`, `effect`, `effect_bundle`, `building_level`, `building_chain`, `technology`, `technology_tree`, `item`, `trait`, `faction`, `culture`, `subculture`, `difficulty_level`, `campaign_variable`.
- Every cross-entity reference is a Link `{type, key, name, missing}` created through the link registry. `missing` is always present (`false` normally); the spec shows it only when true, and always emitting it keeps the TypeScript type non-optional.
- Missing or empty loc text is `null`. `{{tr:<target>}}` is substituted using, in order: exact key `<target>`, `ui_text_replacements_localised_text_<target>`, `campaign_localised_strings_string_<target>`, `cultures_subcultures_<target>`, `random_localisation_strings_string_<target>`; repeat up to depth 5; unresolved tokens stay unchanged. `{{tt:…}}`, `{{Cco…}}` and `[[…]]` markup stay unchanged.
- The model never calculates final stats or research turns.
- Gaps in game data are counted in the manifest; an entity failing schema validation stops the build.
- New runtime dependency: `pydantic>=2.8`. New dev dependency: `pytest>=8`.
- Tests that need the real `twwiki.duckdb` are skipped with a clear message when it is absent.

## Deviations from the spec (clarifications, agreed intent unchanged)

- The spec's single `campaign.py` is split into `buildings.py`, `technologies.py`, `items.py` (items and traits) and `factions.py` (factions, cultures, subcultures, difficulty levels, campaign variables) to keep files focused.
- Pydantic models live next to each domain in `schemas.py` sections added task by task; `schemas.py` remains the single contract module.
- A unit links to `characters: list[Link]` rather than one character, because 62 units are the associated unit of more than one agent subtype.
- A character's `name` is its associated unit's onscreen name (e.g. "Emperor Karl Franz"); `agent_subtypes_onscreen_name_override_<key>` becomes `title` (e.g. "Legendary Lord").
- Mounts, armour, shields, weapons, projectiles and unit attributes are not entity types, so units store them as keys or embedded records rather than links.
- A bonus target whose referenced table is not an entity type (for example `unit_sets`) has `target: null` and carries `target_table` and `target_key`. Targets that point at the combined tables `unit_set_unit_ability_junctions`, `unit_set_unit_attribute_junctions` and `unit_set_special_ability_phase_junctions` are expanded into `unit_set` plus the ability, attribute or phase.
- Cultures and subcultures do not carry their own unit, lord and hero lists; the web app derives them through `subculture.factions` → `faction.units` / `faction.characters`, which the model already provides.
- Ability activation's `spawned_unit`, `activated_projectile`, `bombardment` and `vortex` are stored as keys, not links, because `land_units`, `projectiles`, `projectile_bombardments` and `battle_vortexs` are not entity types.

## Data facts used by the code (verified against build `fb20553df5af`)

- Loc name patterns: `land_units_onscreen_name_<land_unit>`, `unit_description_short_texts_text_<short_description_text>`, `agent_subtypes_onscreen_name_override_<key>`, `character_skills_localised_name_<key>`, `character_skills_localised_description_<key>`, `unit_abilities_onscreen_name_<key>`, `unit_abilities_tooltip_text_<key>`, `unit_ability_types_onscreen_name_<key>`, `unit_ability_source_types_name_<key>`, `special_ability_groups_name_<ability_group>`, `unit_stat_localisations_onscreen_name_<modifiable_unit_stats.localisation>`, `unit_attributes_imued_effect_text_<key>`, `unit_attributes_bullet_text_<key>`, `effects_description_<effect>`, `campaign_effect_scopes_localised_text_<scope>`, `effect_bundles_localised_title_<key>`, `effect_bundles_localised_description_<key>`, `building_culture_variants_name_<building><culture><subculture><faction>`, `building_chains_encyclopedia_name_<key>`, `technologies_onscreen_name_<key>`, `technologies_short_description_<key>`, `technology_node_sets_localised_name_<key>`, `ancillaries_onscreen_name_<key>`, `ancillaries_colour_text_<key>`, `character_trait_levels_onscreen_name_<level key>`, `character_trait_levels_colour_text_<level key>`, `factions_screen_name_<key>`, `cultures_name_<key>`, `cultures_subcultures_name_<subculture>`, `unit_castes_localised_name_<caste>`, `unit_category_localised_name_<category>`, `unit_class_onscreen_<class>`.
- Unit-set rules (`unit_set_to_unit_junctions`): a row matches a unit when every non-empty filter among `unit_record`, `unit_caste`, `unit_category`, `unit_class` matches. Membership = matches any include row and no exclude row. Caste comes from `main_units.caste`; category and class from the unit's `land_units` row (naval units have none). Sets with `use_unit_exp_level_range` are conditional.
- Expected values for tests are listed in Task 14.

## File Structure

| File | Responsibility |
|---|---|
| `pyproject.toml` | Add `pydantic` dependency, `pytest` dev dependency, pytest config |
| `twwiki/model/__init__.py` | Package marker |
| `twwiki/model/__main__.py` | CLI: `python -m twwiki.model` |
| `twwiki/model/text.py` | `LocResolver`: loc lookup and `{{tr:}}` substitution |
| `twwiki/model/links.py` | `LinkRegistry`: names per type, link creation, missing counts, reverse edges |
| `twwiki/model/context.py` | `Context`: DuckDB connection, loc, links, manifest counters, row helpers |
| `twwiki/model/schemas.py` | Pydantic models for every entity type |
| `twwiki/model/unit_sets.py` | Unit-set membership evaluation |
| `twwiki/model/effects.py` | `effect`, `effect_bundle`, bonus targets, `effect_application()` helper |
| `twwiki/model/abilities.py` | `ability` |
| `twwiki/model/units.py` | `unit` |
| `twwiki/model/characters.py` | `character`, `skill` |
| `twwiki/model/buildings.py` | `building_level`, `building_chain` |
| `twwiki/model/technologies.py` | `technology`, `technology_tree`, resource costs |
| `twwiki/model/items.py` | `item`, `trait` |
| `twwiki/model/factions.py` | `faction`, `culture`, `subculture`, `difficulty_level`, `campaign_variable` |
| `twwiki/model/build.py` | Orchestration, reverse links, validation, indexes, schemas, manifest |
| `tests/model/fixtures.py` | `make_context(tables)` in-memory DuckDB builder for unit tests |
| `tests/model/test_*.py` | One test file per module |
| `tests/model/test_real_build.py` | Known entities and whole-build checks against the real database |
| `README.md` | Document the model stage |

---

### Task 1: Dependencies, test setup and loc text resolver

**Files:**
- Modify: `pyproject.toml`
- Create: `twwiki/model/__init__.py`, `twwiki/model/text.py`, `tests/__init__.py`, `tests/model/__init__.py`
- Test: `tests/model/test_text.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `LocResolver(entries: dict[str, str])` with `.raw(key) -> str | None`, `.text(key) -> str | None`, `.substitute(text: str) -> str`, `.unresolved_targets: set[str]`, and `LocResolver.from_duckdb(con) -> LocResolver`.

- [ ] **Step 1: Add dependencies**

Run:
```bash
uv add "pydantic>=2.8"
uv add --dev "pytest>=8"
```

Then append to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

Create empty files `twwiki/model/__init__.py`, `tests/__init__.py`, `tests/model/__init__.py`.

- [ ] **Step 2: Write the failing tests**

`tests/model/test_text.py`:
```python
from twwiki.model.text import LocResolver


def test_raw_returns_none_for_missing_or_empty():
    loc = LocResolver({"a": "", "b": "Bee"})
    assert loc.raw("a") is None
    assert loc.raw("missing") is None
    assert loc.raw("b") == "Bee"


def test_text_substitutes_ui_text_replacement():
    loc = LocResolver({
        "effects_description_x": "{{tr:effect_technology_research_points_description}}: %+n",
        "ui_text_replacements_localised_text_effect_technology_research_points_description": "Research rate",
    })
    assert loc.text("effects_description_x") == "Research rate: %+n"
    assert loc.unresolved_targets == set()


def test_exact_key_wins_over_prefixed_key():
    loc = LocResolver({
        "s": "{{tr:rank7}}",
        "rank7": "exact",
        "ui_text_replacements_localised_text_rank7": "prefixed",
    })
    assert loc.text("s") == "exact"


def test_nested_tokens_resolve_up_to_depth():
    loc = LocResolver({"s": "{{tr:a}}", "a": "{{tr:b}}!", "b": "done"})
    assert loc.text("s") == "done!"


def test_unresolved_token_is_kept_and_recorded():
    loc = LocResolver({"s": "Pay {{tr:nothing_here}} now"})
    assert loc.text("s") == "Pay {{tr:nothing_here}} now"
    assert loc.unresolved_targets == {"nothing_here"}


def test_self_referencing_token_stops_after_max_depth():
    loc = LocResolver({"s": "{{tr:loop}}", "loop": "{{tr:loop}}"})
    assert loc.text("s") == "{{tr:loop}}"


def test_markup_and_context_tokens_are_untouched():
    text = "[[col:red]]%n[[/col]] {{tt:tip}} {{CcoCampaignFaction:x}}"
    loc = LocResolver({"s": text})
    assert loc.text("s") == text
    assert loc.unresolved_targets == set()
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/model/test_text.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'twwiki.model.text'`

- [ ] **Step 4: Implement `twwiki/model/text.py`**

```python
"""Loc lookups with {{tr:...}} text-replacement substitution.

Game markup ([[col:...]], [[img:...]]) and live-context tokens ({{tt:...}},
{{Cco...}}) are left unchanged; the web app renders them.
"""

from __future__ import annotations

import re

# Where a {{tr:<target>}} token's text is looked up, in order.
TR_PREFIXES = (
    "",
    "ui_text_replacements_localised_text_",
    "campaign_localised_strings_string_",
    "cultures_subcultures_",
    "random_localisation_strings_string_",
)
TR_TOKEN = re.compile(r"\{\{tr:([^}]+)\}\}")
MAX_DEPTH = 5


class LocResolver:
    def __init__(self, entries: dict[str, str]):
        self._entries = entries
        self.unresolved_targets: set[str] = set()

    @classmethod
    def from_duckdb(cls, con) -> "LocResolver":
        return cls(dict(con.execute("SELECT key, text FROM loc").fetchall()))

    def raw(self, key: str) -> str | None:
        """Loc text without substitution; empty text counts as missing."""
        text = self._entries.get(key)
        return text if text else None

    def text(self, key: str) -> str | None:
        raw = self.raw(key)
        return None if raw is None else self.substitute(raw)

    def substitute(self, text: str) -> str:
        for _ in range(MAX_DEPTH):
            changed = False

            def replace(match: re.Match) -> str:
                nonlocal changed
                target = match.group(1)
                for prefix in TR_PREFIXES:
                    value = self._entries.get(prefix + target)
                    if value is not None:
                        changed = True
                        return value
                self.unresolved_targets.add(target)
                return match.group(0)

            text = TR_TOKEN.sub(replace, text)
            if not changed:
                break
        return text
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/model/test_text.py -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock twwiki/model/__init__.py twwiki/model/text.py tests/__init__.py tests/model/__init__.py tests/model/test_text.py
git commit -m "feat(model): add loc resolver with text-replacement substitution"
```

### Task 2: Link registry

**Files:**
- Create: `twwiki/model/links.py`
- Test: `tests/model/test_links.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `LinkRegistry` with
  - `.register(entity_type: str, names: dict[str, str | None]) -> None`
  - `.has(entity_type: str, key: str) -> bool`
  - `.name(entity_type: str, key: str) -> str | None`
  - `.keys(entity_type: str) -> list[str]`
  - `.link(entity_type: str, key: str | None, *, source: tuple[str, str] | None, relation: str) -> dict | None` returning `{"type", "key", "name", "missing"}` or `None` for an empty key
  - `.referrers(entity_type: str, key: str, relation: str, source_type: str | None = None) -> list[dict]`
  - `.missing: collections.Counter[str]` keyed `"<source type>.<relation>-><target type>"`

- [ ] **Step 1: Write the failing tests**

`tests/model/test_links.py`:
```python
from twwiki.model.links import LinkRegistry


def make_registry():
    reg = LinkRegistry()
    reg.register("ability", {"hold": "Hold the Line!", "unnamed": None})
    reg.register("unit", {"gs": "Greatswords", "hb": "Halberdiers"})
    return reg


def test_link_to_known_entity():
    reg = make_registry()
    link = reg.link("ability", "hold", source=("unit", "gs"), relation="abilities")
    assert link == {"type": "ability", "key": "hold", "name": "Hold the Line!", "missing": False}
    assert reg.missing == {}


def test_link_to_known_entity_without_name():
    reg = make_registry()
    assert reg.link("ability", "unnamed", source=("unit", "gs"), relation="abilities")["name"] is None


def test_link_to_unknown_entity_is_marked_and_counted():
    reg = make_registry()
    link = reg.link("ability", "nope", source=("unit", "gs"), relation="abilities")
    assert link == {"type": "ability", "key": "nope", "name": None, "missing": True}
    assert reg.missing["unit.abilities->ability"] == 1


def test_empty_key_gives_no_link():
    reg = make_registry()
    assert reg.link("ability", "", source=("unit", "gs"), relation="abilities") is None
    assert reg.link("ability", None, source=("unit", "gs"), relation="abilities") is None
    assert reg.missing == {}


def test_referrers_are_deduplicated_sorted_and_filtered():
    reg = make_registry()
    reg.register("character", {"kf": "Karl Franz"})
    reg.link("ability", "hold", source=("unit", "hb"), relation="abilities")
    reg.link("ability", "hold", source=("unit", "gs"), relation="abilities")
    reg.link("ability", "hold", source=("unit", "gs"), relation="abilities")
    reg.link("ability", "hold", source=("character", "kf"), relation="abilities")
    reg.link("ability", "hold", source=("unit", "gs"), relation="other")

    assert [l["key"] for l in reg.referrers("ability", "hold", "abilities")] == ["kf", "gs", "hb"]
    assert [l["key"] for l in reg.referrers("ability", "hold", "abilities", source_type="unit")] == ["gs", "hb"]
    assert reg.referrers("ability", "hold", "abilities")[1] == {
        "type": "unit", "key": "gs", "name": "Greatswords", "missing": False}


def test_register_merges_and_keys_lists_registered():
    reg = make_registry()
    reg.register("unit", {"new": None})
    assert sorted(reg.keys("unit")) == ["gs", "hb", "new"]
    assert reg.has("unit", "new") and not reg.has("unit", "zzz")
    assert reg.keys("faction") == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/model/test_links.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'twwiki.model.links'`

- [ ] **Step 3: Implement `twwiki/model/links.py`**

```python
"""Every reference between entities goes through here.

Catalogs register each entity type's keys and names before any entity is
built, so a link can say whether its target exists. Links to existing targets
are recorded as edges; build.py turns those into reverse-link fields.
"""

from __future__ import annotations

from collections import Counter, defaultdict


class LinkRegistry:
    def __init__(self) -> None:
        self._names: dict[str, dict[str, str | None]] = {}
        self._edges: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)
        self.missing: Counter[str] = Counter()

    def register(self, entity_type: str, names: dict[str, str | None]) -> None:
        self._names.setdefault(entity_type, {}).update(names)

    def has(self, entity_type: str, key: str) -> bool:
        return key in self._names.get(entity_type, {})

    def name(self, entity_type: str, key: str) -> str | None:
        return self._names.get(entity_type, {}).get(key)

    def keys(self, entity_type: str) -> list[str]:
        return list(self._names.get(entity_type, {}))

    def link(self, entity_type: str, key: str | None, *,
             source: tuple[str, str] | None, relation: str) -> dict | None:
        if not key:
            return None
        names = self._names.get(entity_type, {})
        if key in names:
            if source is not None:
                self._edges[(entity_type, key)].append((source[0], source[1], relation))
            return {"type": entity_type, "key": key, "name": names[key], "missing": False}
        source_type = source[0] if source else "-"
        self.missing[f"{source_type}.{relation}->{entity_type}"] += 1
        return {"type": entity_type, "key": key, "name": None, "missing": True}

    def referrers(self, entity_type: str, key: str, relation: str,
                  source_type: str | None = None) -> list[dict]:
        seen: set[tuple[str, str]] = set()
        out = []
        for s_type, s_key, rel in self._edges.get((entity_type, key), []):
            if rel != relation or (source_type and s_type != source_type):
                continue
            if (s_type, s_key) in seen:
                continue
            seen.add((s_type, s_key))
            out.append({"type": s_type, "key": s_key,
                        "name": self.name(s_type, s_key), "missing": False})
        return sorted(out, key=lambda link: (link["type"], link["key"]))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/model/test_links.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add twwiki/model/links.py tests/model/test_links.py
git commit -m "feat(model): add link registry with missing-link counts and reverse edges"
```

### Task 3: Context, core schemas and test fixtures

**Files:**
- Create: `twwiki/model/context.py`, `twwiki/model/schemas.py`, `tests/model/fixtures.py`
- Test: `tests/model/test_context.py`

**Interfaces:**
- Consumes: `LocResolver` (Task 1), `LinkRegistry` (Task 2).
- Produces:
  - `opt(value) -> value | None`: `""` and `None` become `None`.
  - `Context(con, loc, links=LinkRegistry())` dataclass with `.missing_names: Counter[str]`, `.partial: dict[str, list[str]]`, `Context.open(db_path) -> Context`, `.rows(sql: str, params: list | None = None) -> list[dict]`, `.table_exists(name: str) -> bool`, `.require(entity_type: str, *tables: str) -> bool`, `.catalog_name(entity_type: str, loc_key: str) -> str | None`.
  - `schemas.Strict` (Pydantic base, `extra="forbid"`), `schemas.Link`, `schemas.EffectApplication`, `schemas.ENTITY_MODELS: dict[str, type[Strict]]`, decorator `schemas.entity(type_name: str)`.
  - `tests/model/fixtures.make_context(tables: dict[str, list[dict]], loc: dict[str, str] | None = None) -> Context`. Every table passed must have at least one row.

Rules later tasks follow:
- `ctx.catalog_name(...)` is called **only in `catalog()` functions**, so missing names are counted once per entity. Builders read names back with `ctx.links.name(type, key)`.
- Builders call `ctx.require(entity_type, *tables)` first and return an empty list for that type when it is `False`.

- [ ] **Step 1: Write the failing tests**

`tests/model/test_context.py`:
```python
import pytest
from pydantic import ValidationError

from twwiki.model import schemas
from twwiki.model.context import opt
from tests.model.fixtures import make_context


def test_opt_turns_empty_strings_into_none():
    assert opt("") is None
    assert opt(None) is None
    assert opt("x") == "x"
    assert opt(0) == 0


def test_rows_returns_dicts():
    ctx = make_context({"things": [{"key": "a", "n": 1}, {"key": "b", "n": 2}]})
    assert ctx.rows("SELECT key, n FROM things ORDER BY key") == [{"key": "a", "n": 1}, {"key": "b", "n": 2}]
    assert ctx.rows("SELECT key FROM things WHERE n = ?", [2]) == [{"key": "b"}]


def test_require_records_missing_tables_as_partial():
    ctx = make_context({"things": [{"key": "a"}]})
    assert ctx.table_exists("things") and not ctx.table_exists("nope")
    assert ctx.require("unit", "things") is True
    assert ctx.require("unit", "things", "nope", "gone") is False
    assert ctx.partial == {"unit": ["nope", "gone"]}


def test_catalog_name_counts_missing_names():
    ctx = make_context({"things": [{"key": "a"}]}, loc={"name_a": "Alpha", "name_b": ""})
    assert ctx.catalog_name("unit", "name_a") == "Alpha"
    assert ctx.catalog_name("unit", "name_b") is None
    assert ctx.catalog_name("unit", "name_c") is None
    assert ctx.missing_names == {"unit": 2}


def test_link_model_rejects_extra_fields():
    schemas.Link(type="unit", key="k", name=None, missing=True)
    with pytest.raises(ValidationError):
        schemas.Link(type="unit", key="k", name=None, missing=False, extra=1)


def test_effect_application_optional_fields_default_to_none():
    link = {"type": "effect", "key": "e", "name": None, "missing": False}
    src = {"type": "skill", "key": "s", "name": None, "missing": False}
    app = schemas.EffectApplication(effect=link, scope="force_to_force_own", value=4.0, source=src)
    dumped = app.model_dump(mode="json")
    assert dumped["value_damaged"] is None and dumped["context_requirement"] is None


def test_entity_decorator_registers_model():
    @schemas.entity("test_only_type")
    class Thing(schemas.Strict):
        key: str

    assert schemas.ENTITY_MODELS["test_only_type"] is Thing
    del schemas.ENTITY_MODELS["test_only_type"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/model/test_context.py -v`
Expected: FAIL with `ModuleNotFoundError` for `twwiki.model.context` or `tests.model.fixtures`

- [ ] **Step 3: Implement `twwiki/model/context.py`**

```python
"""Shared state for one model build."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from .links import LinkRegistry
from .text import LocResolver


def opt(value):
    """RPFM optional strings arrive as ''. Treat them as absent."""
    return None if value == "" or value is None else value


@dataclass
class Context:
    con: duckdb.DuckDBPyConnection
    loc: LocResolver
    links: LinkRegistry = field(default_factory=LinkRegistry)
    missing_names: Counter = field(default_factory=Counter)
    partial: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def open(cls, db_path: str | Path) -> "Context":
        con = duckdb.connect(str(db_path), read_only=True)
        return cls(con=con, loc=LocResolver.from_duckdb(con))

    def rows(self, sql: str, params: list | None = None) -> list[dict]:
        cur = self.con.execute(sql, params or [])
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def table_exists(self, name: str) -> bool:
        return bool(self.con.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = ?", [name]
        ).fetchone())

    def require(self, entity_type: str, *tables: str) -> bool:
        missing = [t for t in tables if not self.table_exists(t)]
        if missing:
            self.partial.setdefault(entity_type, []).extend(missing)
        return not missing

    def catalog_name(self, entity_type: str, loc_key: str) -> str | None:
        """Resolve an entity's display name. Call from catalog() only."""
        text = self.loc.text(loc_key)
        if text is None:
            self.missing_names[entity_type] += 1
        return text
```

- [ ] **Step 4: Implement `twwiki/model/schemas.py` (core section)**

```python
"""Pydantic models: the contract between the model build and the web app.

Every entity model is registered with @entity("<type>") so build.py can
validate entities and export one JSON Schema per type.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

ENTITY_MODELS: dict[str, type["Strict"]] = {}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def entity(type_name: str):
    def register(cls: type[Strict]) -> type[Strict]:
        ENTITY_MODELS[type_name] = cls
        return cls
    return register


# ---- Shared shapes ---------------------------------------------------------

class Link(Strict):
    type: str
    key: str
    name: str | None
    missing: bool


class EffectApplication(Strict):
    effect: Link
    scope: str | None
    value: float
    source: Link
    value_damaged: float | None = None      # buildings only
    value_ruined: float | None = None       # buildings only
    context_requirement: str | None = None  # buildings only
    advancement_stage: str | None = None    # effect bundles only
```

- [ ] **Step 5: Implement `tests/model/fixtures.py`**

```python
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
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/model/test_context.py -v`
Expected: 7 passed

- [ ] **Step 7: Commit**

```bash
git add twwiki/model/context.py twwiki/model/schemas.py tests/model/fixtures.py tests/model/test_context.py
git commit -m "feat(model): add build context, core schemas and test fixtures"
```

### Task 4: Unit-set membership

**Files:**
- Create: `twwiki/model/unit_sets.py`
- Test: `tests/model/test_unit_sets.py`

**Interfaces:**
- Consumes: `Context`, `opt` (Task 3).
- Produces:
  - `evaluate_membership(units: list[dict], rules: list[dict]) -> dict[str, set[str]]`. Unit dicts have `unit`, `caste`, `category`, `class` (category/class may be `None`). Rule dicts have `unit_set`, `exclude`, `unit_record`, `unit_caste`, `unit_category`, `unit_class` (empty string = not filtered). Returns set key → member unit keys.
  - `resolve_unit_sets(ctx: Context) -> dict[str, list[dict]]`: unit key → sorted list of `{"key": str, "conditional": bool, "min_exp_level": int | None, "max_exp_level": int | None}`. Returns `{}` and marks `unit` partial when a source table is missing.

- [ ] **Step 1: Write the failing tests**

`tests/model/test_unit_sets.py`:
```python
from twwiki.model.unit_sets import evaluate_membership, resolve_unit_sets
from tests.model.fixtures import make_context

UNITS = [
    {"unit": "gs", "caste": "melee_infantry", "category": "inf_melee", "class": "inf_mel"},
    {"unit": "kf", "caste": "lord", "category": "inf_melee", "class": "com"},
    {"unit": "hag", "caste": "hero", "category": "inf_melee", "class": "com"},
    {"unit": "ship", "caste": "warship", "category": None, "class": None},
]


def rule(unit_set, exclude=False, record="", caste="", category="", cls=""):
    return {"unit_set": unit_set, "exclude": exclude, "unit_record": record,
            "unit_caste": caste, "unit_category": category, "unit_class": cls}


def test_single_filter_rules():
    members = evaluate_membership(UNITS, [
        rule("by_record", record="gs"),
        rule("by_caste", caste="lord"),
        rule("by_category", category="inf_melee"),
        rule("by_class", cls="com"),
    ])
    assert members["by_record"] == {"gs"}
    assert members["by_caste"] == {"kf"}
    assert members["by_category"] == {"gs", "kf", "hag"}
    assert members["by_class"] == {"kf", "hag"}


def test_row_with_two_filters_needs_both():
    members = evaluate_membership(UNITS, [rule("both", record="hag", caste="hero"),
                                          rule("wrong", record="hag", caste="lord")])
    assert members["both"] == {"hag"}
    assert members["wrong"] == set()


def test_exclude_rows_remove_members():
    members = evaluate_membership(UNITS, [
        rule("no_characters", cls="inf_mel"),
        rule("no_characters", cls="com"),
        rule("no_characters", exclude=True, caste="hero"),
        rule("no_characters", exclude=True, caste="lord"),
    ])
    assert members["no_characters"] == {"gs"}


def test_units_without_land_unit_only_match_record_or_caste():
    members = evaluate_membership(UNITS, [rule("naval", caste="warship"), rule("cls", cls="com")])
    assert members["naval"] == {"ship"}
    assert "ship" not in members["cls"]


def test_resolve_unit_sets_marks_conditional_sets():
    ctx = make_context({
        "main_units": [{"unit": "gs", "caste": "melee_infantry", "land_unit": "gs_land"},
                       {"unit": "ship", "caste": "warship", "land_unit": ""}],
        "land_units": [{"key": "gs_land", "category": "inf_melee", "class": "inf_mel"}],
        "unit_sets": [
            {"key": "all_inf", "use_unit_exp_level_range": False, "min_unit_exp_level_inclusive": 0, "max_unit_exp_level_inclusive": 0},
            {"key": "vet_inf", "use_unit_exp_level_range": True, "min_unit_exp_level_inclusive": 3, "max_unit_exp_level_inclusive": 9},
        ],
        "unit_set_to_unit_junctions": [
            {"unit_set": "all_inf", "exclude": False, "unit_record": "", "unit_caste": "", "unit_category": "inf_melee", "unit_class": ""},
            {"unit_set": "vet_inf", "exclude": False, "unit_record": "gs", "unit_caste": "", "unit_category": "", "unit_class": ""},
        ],
    })
    result = resolve_unit_sets(ctx)
    assert result["gs"] == [
        {"key": "all_inf", "conditional": False, "min_exp_level": None, "max_exp_level": None},
        {"key": "vet_inf", "conditional": True, "min_exp_level": 3, "max_exp_level": 9},
    ]
    assert "ship" not in result


def test_resolve_unit_sets_missing_table_is_partial():
    ctx = make_context({"main_units": [{"unit": "gs", "caste": "x", "land_unit": ""}]})
    assert resolve_unit_sets(ctx) == {}
    assert ctx.partial["unit"] == ["land_units", "unit_sets", "unit_set_to_unit_junctions"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/model/test_unit_sets.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'twwiki.model.unit_sets'`

- [ ] **Step 3: Implement `twwiki/model/unit_sets.py`**

```python
"""Which unit sets each unit belongs to.

A rule row matches a unit when every non-empty filter on the row matches.
A unit is a member when it matches any include row and no exclude row.
Evaluated once here so the stat engine never re-implements the rules.
"""

from __future__ import annotations

from collections import defaultdict

from .context import Context

FILTERS = (("unit_record", "unit"), ("unit_caste", "caste"),
           ("unit_category", "category"), ("unit_class", "class"))


def evaluate_membership(units: list[dict], rules: list[dict]) -> dict[str, set[str]]:
    index: dict[tuple[str, str], set[str]] = defaultdict(set)
    for u in units:
        for _, field in FILTERS:
            if u.get(field):
                index[(field, u[field])].add(u["unit"])

    include: dict[str, set[str]] = defaultdict(set)
    exclude: dict[str, set[str]] = defaultdict(set)
    for r in rules:
        matched: set[str] | None = None
        for rule_col, field in FILTERS:
            value = r.get(rule_col)
            if not value:
                continue
            hits = index.get((field, value), set())
            matched = set(hits) if matched is None else matched & hits
        target = exclude if r["exclude"] else include
        target[r["unit_set"]] |= matched or set()

    return {s: include.get(s, set()) - exclude.get(s, set())
            for s in set(include) | set(exclude)}


def resolve_unit_sets(ctx: Context) -> dict[str, list[dict]]:
    if not ctx.require("unit", "main_units", "land_units", "unit_sets", "unit_set_to_unit_junctions"):
        return {}
    units = ctx.rows("""
        SELECT mu.unit, mu.caste, lu.category, lu.class
        FROM main_units mu LEFT JOIN land_units lu ON lu.key = mu.land_unit
    """)
    rules = ctx.rows("""
        SELECT unit_set, exclude, unit_record, unit_caste, unit_category, unit_class
        FROM unit_set_to_unit_junctions
    """)
    sets = {r["key"]: r for r in ctx.rows("SELECT * FROM unit_sets")}

    by_unit: dict[str, list[dict]] = defaultdict(list)
    for set_key, members in evaluate_membership(units, rules).items():
        meta = sets.get(set_key)
        conditional = bool(meta and meta["use_unit_exp_level_range"])
        entry = {
            "key": set_key,
            "conditional": conditional,
            "min_exp_level": meta["min_unit_exp_level_inclusive"] if conditional else None,
            "max_exp_level": meta["max_unit_exp_level_inclusive"] if conditional else None,
        }
        for unit in members:
            by_unit[unit].append(entry)
    return {u: sorted(entries, key=lambda e: e["key"]) for u, entries in by_unit.items()}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/model/test_unit_sets.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add twwiki/model/unit_sets.py tests/model/test_unit_sets.py
git commit -m "feat(model): resolve unit-set membership from include/exclude rules"
```

### Task 5: Effects, effect bundles and bonus targets

**Files:**
- Create: `twwiki/model/effects.py`
- Modify: `twwiki/model/schemas.py` (append effects section), `tests/model/fixtures.py` (append `register_catalogs`)
- Test: `tests/model/test_effects.py`

**Interfaces:**
- Consumes: `Context`, `opt`, `schemas.Strict`, `schemas.Link`, `schemas.EffectApplication`, `schemas.entity` (Task 3).
- Produces:
  - `effects.catalog(ctx) -> dict[str, dict[str, str | None]]` for `effect` (name = description) and `effect_bundle` (name = title).
  - `effects.build(ctx) -> dict[str, list[dict]]` for `effect` and `effect_bundle`.
  - `effects.effect_application(ctx, effect_key: str, *, scope: str | None, value: float, source: tuple[str, str], **extra) -> dict`. Links the effect with relation `"effect"` (so `effect.sources` can be filled later) and the source entity. Every later module uses this for effect applications.
  - `effects.ENTITY_TYPE_FOR_TABLE: dict[str, str]`.
  - Link relation `"bonus_target"` from `effect` to the target entity (used by Task 13 for `ability.modified_by_effects`).
  - Schemas: `BonusTarget`, `Effect` (`@entity("effect")`, field `sources: list[Link] = []` filled by Task 13), `EffectBundle` (`@entity("effect_bundle")`).
  - `tests/model/fixtures.register_catalogs(ctx, *modules) -> None`.

- [ ] **Step 1: Append the fixture helper**

Append to `tests/model/fixtures.py`:
```python
def register_catalogs(ctx: Context, *modules) -> None:
    """Register entity names the way build.py does before building."""
    for module in modules:
        for entity_type, names in module.catalog(ctx).items():
            ctx.links.register(entity_type, names)
```

- [ ] **Step 2: Write the failing tests**

`tests/model/test_effects.py`:
```python
from twwiki.model import effects, schemas
from tests.model.fixtures import make_context, register_catalogs


def columns(table, *cols_and_refs):
    return [{"table_name": table, "column_name": c, "ref_table": r} for c, r in cols_and_refs]


def effects_context(**overrides):
    tables = {
        "effects": [
            {"effect": "e_attack", "icon": "a.png", "priority": 1, "icon_negative": "", "category": "battle", "is_positive_value_good": True},
            {"effect": "e_research", "icon": "", "priority": 2, "icon_negative": "", "category": "campaign", "is_positive_value_good": True},
        ],
        "effect_bundles": [{"key": "b1", "localised_description": "", "localised_title": "", "bundle_target": "faction",
                            "priority": 0, "ui_icon": "b.png", "is_global_effect": False, "show_in_3d_space": False, "owner_only": False}],
        "effect_bundles_to_effects_junctions": [{"effect_bundle_key": "b1", "effect_key": "e_research",
                                                 "effect_scope": "faction_to_faction_own", "value": 5.0, "advancement_stage": "start_turn_completed"}],
        "unit_abilities": [{"key": "hold"}],
        "effect_bonus_value_basic_junction": [{"effect": "e_research", "bonus_value_id": "research_points"}],
        "effect_bonus_value_ids_unit_sets": [{"bonus_value_id": "melee_attack_mod", "effect": "e_attack", "unit_set": "giants"}],
        "effect_bonus_value_unit_ability_junctions": [{"effect": "e_attack", "bonus_value_id": "enable", "unit_ability": "hold"}],
        "effect_bonus_value_unit_set_unit_ability_junctions": [{"bonus_value_id": "enable", "effect": "e_attack", "unit_set_ability": "combo"}],
        "unit_set_unit_ability_junctions": [{"key": "combo", "unit_ability": "hold", "unit_set": "engineers"}],
        "_columns": (
            columns("effect_bonus_value_basic_junction", ("effect", "effects"), ("bonus_value_id", "campaign_bonus_value_ids_basic"))
            + columns("effect_bonus_value_ids_unit_sets", ("bonus_value_id", "x"), ("effect", "effects"), ("unit_set", "unit_sets"))
            + columns("effect_bonus_value_unit_ability_junctions", ("effect", "effects"), ("bonus_value_id", "x"), ("unit_ability", "unit_abilities"))
            + columns("effect_bonus_value_unit_set_unit_ability_junctions", ("bonus_value_id", "x"), ("effect", "effects"),
                      ("unit_set_ability", "unit_set_unit_ability_junctions"))
        ),
    }
    tables.update(overrides)
    loc = {
        "effects_description_e_attack": "Melee attack: %+n",
        "effects_description_e_research": "{{tr:research}}: %+n",
        "ui_text_replacements_localised_text_research": "Research rate",
        "effect_bundles_localised_title_b1": "First Book",
    }
    ctx = make_context(tables, loc)
    register_catalogs(ctx, effects)
    ctx.links.register("ability", {"hold": "Hold the Line!"})
    return ctx


def test_catalog_uses_description_and_title():
    ctx = effects_context()
    assert ctx.links.name("effect", "e_research") == "Research rate: %+n"
    assert ctx.links.name("effect_bundle", "b1") == "First Book"


def test_bonus_targets_cover_each_table_shape():
    ctx = effects_context()
    built = {e["key"]: e for e in effects.build(ctx)["effect"]}

    assert built["e_research"]["bonus_targets"] == [{
        "bonus_value_id": "research_points", "source_table": "effect_bonus_value_basic_junction",
        "target_table": None, "target_key": None, "target": None,
        "unit_set": None, "ability": None, "attribute": None, "phase": None}]

    attack = {t["source_table"]: t for t in built["e_attack"]["bonus_targets"]}
    assert attack["effect_bonus_value_ids_unit_sets"]["unit_set"] == "giants"
    assert attack["effect_bonus_value_ids_unit_sets"]["target"] is None
    assert attack["effect_bonus_value_unit_ability_junctions"]["target"] == {
        "type": "ability", "key": "hold", "name": "Hold the Line!", "missing": False}
    combo = attack["effect_bonus_value_unit_set_unit_ability_junctions"]
    assert combo["unit_set"] == "engineers" and combo["ability"]["key"] == "hold"
    assert combo["target_table"] == "unit_set_unit_ability_junctions" and combo["target_key"] == "combo"

    assert [l["key"] for l in ctx.links.referrers("ability", "hold", "bonus_target")] == ["e_attack"]
    for entity in built.values():
        schemas.ENTITY_MODELS["effect"].model_validate(entity)


def test_bundle_effect_applications_link_effect_and_source():
    ctx = effects_context()
    bundle = effects.build(ctx)["effect_bundle"][0]
    assert bundle["title"] == "First Book"
    app = bundle["effects"][0]
    assert app["effect"]["key"] == "e_research" and app["value"] == 5.0
    assert app["source"] == {"type": "effect_bundle", "key": "b1", "name": "First Book", "missing": False}
    assert app["advancement_stage"] == "start_turn_completed"
    assert [l["key"] for l in ctx.links.referrers("effect", "e_research", "effect")] == ["b1"]
    schemas.ENTITY_MODELS["effect_bundle"].model_validate(bundle)


def test_missing_effects_table_is_partial():
    ctx = make_context({"_columns": columns("x", ("a", None))})
    assert effects.catalog(ctx) == {"effect": {}, "effect_bundle": {}}
    assert effects.build(ctx) == {"effect": [], "effect_bundle": []}
    assert ctx.partial == {"effect": ["effects"], "effect_bundle": ["effect_bundles", "effect_bundles_to_effects_junctions"]}
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/model/test_effects.py -v`
Expected: FAIL with `ImportError: cannot import name 'effects' from 'twwiki.model'`

- [ ] **Step 4: Append the effects section to `twwiki/model/schemas.py`**

```python
# ---- Effects ---------------------------------------------------------------

class BonusTarget(Strict):
    bonus_value_id: str
    source_table: str
    target_table: str | None
    target_key: str | None
    target: Link | None
    unit_set: str | None
    ability: Link | None
    attribute: str | None
    phase: str | None


@entity("effect")
class Effect(Strict):
    key: str
    description: str | None
    additional_tooltip: str | None
    category: str
    icon: str | None
    icon_negative: str | None
    priority: int
    is_positive_value_good: bool
    bonus_targets: list[BonusTarget]
    sources: list[Link] = []


@entity("effect_bundle")
class EffectBundle(Strict):
    key: str
    title: str | None
    description: str | None
    target: str
    priority: int
    icon: str | None
    is_global_effect: bool
    effects: list[EffectApplication]
```

- [ ] **Step 5: Implement `twwiki/model/effects.py`**

```python
"""Effects, effect bundles, and what each effect targets.

The 53 effect_bonus_value_* tables all say "effect E, bonus type B, applied to
thing T". They are normalised into one BonusTarget list per effect. Column
roles come from the schema metadata in _columns, so new bonus tables in a
patch are picked up without code changes.
"""

from __future__ import annotations

from collections import defaultdict

from .context import Context, opt

ENTITY_TYPE_FOR_TABLE = {
    "main_units": "unit",
    "unit_abilities": "ability",
    "agent_subtypes": "character",
    "effects": "effect",
    "building_levels": "building_level",
    "building_chains": "building_chain",
    "technologies": "technology",
    "ancillaries": "item",
    "factions": "faction",
    "cultures": "culture",
    "cultures_subcultures": "subculture",
}
# Junction tables that pair a unit set with one specific thing.
COMBINED_UNIT_SET_TABLES = {
    "unit_set_unit_ability_junctions": "unit_ability",
    "unit_set_unit_attribute_junctions": "unit_attribute",
    "unit_set_special_ability_phase_junctions": "special_ability_phase",
}
EFFECT_COLUMNS = ("effect", "effect_key")
BONUS_COLUMNS = ("bonus_value_id", "bonus_value")


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {"effect": {}, "effect_bundle": {}}
    if ctx.table_exists("effects"):
        for r in ctx.rows("SELECT effect FROM effects"):
            out["effect"][r["effect"]] = ctx.catalog_name("effect", f"effects_description_{r['effect']}")
    if ctx.table_exists("effect_bundles"):
        for r in ctx.rows("SELECT key FROM effect_bundles"):
            out["effect_bundle"][r["key"]] = ctx.catalog_name(
                "effect_bundle", f"effect_bundles_localised_title_{r['key']}")
    return out


def effect_application(ctx: Context, effect_key: str, *, scope: str | None, value: float,
                       source: tuple[str, str], **extra) -> dict:
    app = {
        "effect": ctx.links.link("effect", effect_key, source=source, relation="effect"),
        "scope": opt(scope),
        "value": float(value),
        "source": ctx.links.link(source[0], source[1], source=None, relation="source"),
    }
    app.update(extra)
    return app


def bonus_targets(ctx: Context) -> dict[str, list[dict]]:
    tables = [r["table_name"] for r in ctx.rows(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_name LIKE 'effect_bonus_value%' ORDER BY table_name")]
    combined = {t: {r["key"]: r for r in ctx.rows(f'SELECT * FROM "{t}"')}
                for t in COMBINED_UNIT_SET_TABLES if ctx.table_exists(t)}

    out: dict[str, list[dict]] = defaultdict(list)
    for table in tables:
        cols = {r["column_name"]: r["ref_table"] for r in ctx.rows(
            "SELECT column_name, ref_table FROM _columns WHERE table_name = ?", [table])}
        effect_col = next(c for c in EFFECT_COLUMNS if c in cols)
        bonus_col = next(c for c in BONUS_COLUMNS if c in cols)
        target_cols = [c for c in cols if c not in (effect_col, bonus_col)]
        target_col = target_cols[0] if target_cols else None
        select = f'"{effect_col}" AS effect, "{bonus_col}" AS bonus'
        if target_col:
            select += f', "{target_col}" AS target'
        for r in ctx.rows(f'SELECT {select} FROM "{table}"'):
            out[r["effect"]].append(_bonus_target(
                ctx, table, cols.get(target_col), r.get("target"), r["bonus"], r["effect"], combined))
    for targets in out.values():
        targets.sort(key=lambda t: (t["source_table"], t["bonus_value_id"], t["target_key"] or ""))
    return out


def _bonus_target(ctx: Context, table: str, target_table: str | None, raw_key, bonus: str,
                  effect: str, combined: dict) -> dict:
    key = None if raw_key is None or raw_key == "" else str(raw_key)
    target = {"bonus_value_id": bonus, "source_table": table, "target_table": target_table,
              "target_key": key, "target": None, "unit_set": None, "ability": None,
              "attribute": None, "phase": None}
    source = ("effect", effect)
    entity_type = ENTITY_TYPE_FOR_TABLE.get(target_table)
    if entity_type and key:
        target["target"] = ctx.links.link(entity_type, key, source=source, relation="bonus_target")
    if target_table == "unit_sets":
        target["unit_set"] = key
    elif target_table in combined and key in combined[target_table]:
        row = combined[target_table][key]
        target["unit_set"] = row["unit_set"]
        if target_table == "unit_set_unit_ability_junctions":
            target["ability"] = ctx.links.link("ability", row["unit_ability"], source=source,
                                               relation="bonus_target")
        elif target_table == "unit_set_unit_attribute_junctions":
            target["attribute"] = row["unit_attribute"]
        else:
            target["phase"] = row["special_ability_phase"]
    return target


def build(ctx: Context) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {"effect": [], "effect_bundle": []}

    if ctx.require("effect", "effects"):
        targets = bonus_targets(ctx) if ctx.table_exists("_columns") else {}
        for r in ctx.rows("SELECT * FROM effects ORDER BY effect"):
            key = r["effect"]
            out["effect"].append({
                "key": key,
                "description": ctx.links.name("effect", key),
                "additional_tooltip": ctx.loc.text(
                    f"effects_additional_tooltip_details_localised_description_{key}"),
                "category": r["category"],
                "icon": opt(r["icon"]),
                "icon_negative": opt(r["icon_negative"]),
                "priority": r["priority"],
                "is_positive_value_good": r["is_positive_value_good"],
                "bonus_targets": targets.get(key, []),
                "sources": [],
            })

    if ctx.require("effect_bundle", "effect_bundles", "effect_bundles_to_effects_junctions"):
        apps: dict[str, list[dict]] = defaultdict(list)
        for r in ctx.rows("SELECT * FROM effect_bundles_to_effects_junctions "
                          "ORDER BY effect_bundle_key, effect_key"):
            apps[r["effect_bundle_key"]].append(effect_application(
                ctx, r["effect_key"], scope=r["effect_scope"], value=r["value"],
                source=("effect_bundle", r["effect_bundle_key"]),
                advancement_stage=opt(r["advancement_stage"])))
        for r in ctx.rows("SELECT * FROM effect_bundles ORDER BY key"):
            key = r["key"]
            out["effect_bundle"].append({
                "key": key,
                "title": ctx.links.name("effect_bundle", key),
                "description": ctx.loc.text(f"effect_bundles_localised_description_{key}"),
                "target": r["bundle_target"],
                "priority": r["priority"],
                "icon": opt(r["ui_icon"]),
                "is_global_effect": r["is_global_effect"],
                "effects": apps.get(key, []),
            })
    return out
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/model/test_effects.py -v`
Expected: 4 passed

- [ ] **Step 7: Commit**

```bash
git add twwiki/model/effects.py twwiki/model/schemas.py tests/model/fixtures.py tests/model/test_effects.py
git commit -m "feat(model): build effects, bundles and normalised bonus targets"
```

### Task 6: Abilities

**Files:**
- Create: `twwiki/model/abilities.py`
- Modify: `twwiki/model/schemas.py` (append abilities section), `twwiki/model/context.py` (append `by_key` and `grouped` helpers)
- Test: `tests/model/test_abilities.py`

**Interfaces:**
- Consumes: `Context`, `opt`, `schemas.Strict`, `schemas.Link`, `schemas.entity`.
- Produces:
  - `context.by_key(ctx, table: str, key_col: str) -> dict[str, dict]` (empty dict when the table is missing).
  - `context.grouped(ctx, table: str, key_col: str, order: str) -> dict[str, list[dict]]` (`order` is a raw SQL ORDER BY list; empty dict when the table is missing).
  - `abilities.catalog(ctx)` → `{"ability": {key: name}}`; `abilities.build(ctx)` → `{"ability": [...]}`.
  - Schemas: `Activation`, `StatEffect`, `AttributeEffect`, `Phase`, `Ability` (`@entity("ability")`) with reverse fields `units`, `characters`, `modified_by_effects` defaulting to `[]` (filled in Task 13).

- [ ] **Step 1: Append helpers to `twwiki/model/context.py`**

```python
from collections import defaultdict  # add to the imports at the top


def by_key(ctx: "Context", table: str, key_col: str) -> dict[str, dict]:
    """All rows of an optional table, indexed by one column."""
    if not ctx.table_exists(table):
        return {}
    return {r[key_col]: r for r in ctx.rows(f'SELECT * FROM "{table}"')}


def grouped(ctx: "Context", table: str, key_col: str, order: str) -> dict[str, list[dict]]:
    """All rows of an optional table, grouped by one column, in `order`."""
    out: dict[str, list[dict]] = defaultdict(list)
    if ctx.table_exists(table):
        for r in ctx.rows(f'SELECT * FROM "{table}" ORDER BY {order}'):
            out[r[key_col]].append(r)
    return out
```

- [ ] **Step 2: Write the failing tests**

`tests/model/test_abilities.py`:
```python
from twwiki.model import abilities, schemas
from tests.model.fixtures import make_context, register_catalogs


def special(**overrides):
    row = {
        "key": "hold", "active_time": -1.0, "recharge_time": -1.0, "num_uses": -1, "effect_range": 35.0,
        "affect_self": True, "num_effected_friendly_units": -1, "num_effected_enemy_units": 0,
        "initial_recharge": 0.0, "activated_projectile": "", "target_friends": False, "target_enemies": False,
        "target_ground": False, "wind_up_time": 0.0, "passive": True, "bombardment": "", "spawned_unit": "",
        "mana_cost": 0.0, "min_range": 0.0, "vortex": "", "miscast_chance": 0.0, "target_self": False,
    }
    row.update(overrides)
    return row


def phase_row(**overrides):
    row = {
        "id": "hold_phase", "duration": -1.0, "effect_type": "positive", "cant_move": False,
        "fatigue_change_ratio": 0.0, "ability_recharge_change": 0.0, "hp_change_frequency": 0.0,
        "damage_amount": 0, "max_damaged_entities": 0, "resurrect": False, "mana_regen_mod": 0.0,
        "imbue_magical": False, "imbue_ignition": 0, "is_hidden_in_ui": False, "replenish_ammo": 0.0,
        "heal_amount": 0.0, "execute_ratio": 0.0,
    }
    row.update(overrides)
    return row


def ability_context():
    ctx = make_context({
        "unit_abilities": [
            {"key": "hold", "requires_effect_enabling": False, "icon_name": "hold.png", "type": "wh_type_augment",
             "is_unit_upgrade": False, "is_hidden_in_ui": False, "source_type": "lord"},
            {"key": "plain", "requires_effect_enabling": False, "icon_name": "p.png", "type": "wh_type_augment",
             "is_unit_upgrade": False, "is_hidden_in_ui": True, "source_type": "unit"},
        ],
        "unit_special_abilities": [special()],
        "special_ability_to_special_ability_phase_junctions": [
            {"order": 0, "phase": "hold_phase", "special_ability": "hold",
             "target_self": True, "target_friends": True, "target_enemies": False},
            {"order": 1, "phase": "gone_phase", "special_ability": "hold",
             "target_self": True, "target_friends": False, "target_enemies": False},
        ],
        "special_ability_phases": [phase_row()],
        "special_ability_phase_stat_effects": [
            {"phase": "hold_phase", "value": 5.0, "stat": "stat_melee_defence", "how": "add"},
            {"phase": "hold_phase", "value": 4.0, "stat": "stat_morale", "how": "add"},
        ],
        "special_ability_phase_attribute_effects": [
            {"attribute": "unbreakable", "phase": "hold_phase", "attribute_type": "positive"}],
        "modifiable_unit_stats": [{"stat_key": "stat_melee_defence", "localisation": "stat_melee_defence"},
                                  {"stat_key": "stat_morale", "localisation": "stat_morale"}],
    }, loc={
        "unit_abilities_onscreen_name_hold": "Hold the Line!",
        "unit_abilities_tooltip_text_hold": "Stand firm.",
        "unit_ability_source_types_name_lord": "Lord Ability",
        "unit_stat_localisations_onscreen_name_stat_melee_defence": "Melee Defence",
        "unit_stat_localisations_onscreen_name_stat_morale": "Leadership",
    })
    register_catalogs(ctx, abilities)
    return ctx


def test_hold_the_line_activation_and_phases():
    ctx = ability_context()
    built = {a["key"]: a for a in abilities.build(ctx)["ability"]}
    hold = built["hold"]
    assert hold["name"] == "Hold the Line!" and hold["description"] == "Stand firm."
    assert hold["source_type_name"] == "Lord Ability"
    assert hold["activation"]["passive"] is True and hold["activation"]["effect_range"] == 35.0
    assert len(hold["phases"]) == 1
    phase = hold["phases"][0]
    assert phase["order"] == 0 and phase["target_friends"] is True
    assert phase["stat_effects"] == [
        {"stat": "stat_melee_defence", "stat_name": "Melee Defence", "value": 5.0, "how": "add"},
        {"stat": "stat_morale", "stat_name": "Leadership", "value": 4.0, "how": "add"},
    ]
    assert phase["attribute_effects"] == [{"attribute": "unbreakable", "attribute_type": "positive"}]
    assert ctx.links.missing["ability.phase->special_ability_phase"] == 1
    schemas.ENTITY_MODELS["ability"].model_validate(hold)


def test_ability_without_special_row_has_no_activation():
    plain = {a["key"]: a for a in abilities.build(ability_context())["ability"]}["plain"]
    assert plain["name"] is None and plain["activation"] is None and plain["phases"] == []
    assert plain["units"] == [] and plain["modified_by_effects"] == []
    schemas.ENTITY_MODELS["ability"].model_validate(plain)
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/model/test_abilities.py -v`
Expected: FAIL with `ImportError: cannot import name 'abilities' from 'twwiki.model'`

- [ ] **Step 4: Append the abilities section to `twwiki/model/schemas.py`**

```python
# ---- Abilities -------------------------------------------------------------

class Activation(Strict):
    passive: bool
    active_time: float
    recharge_time: float
    initial_recharge: float
    num_uses: int
    effect_range: float
    min_range: float
    mana_cost: float
    wind_up_time: float
    miscast_chance: float
    target_self: bool
    target_friends: bool
    target_enemies: bool
    target_ground: bool
    affect_self: bool
    num_effected_friendly_units: int
    num_effected_enemy_units: int
    spawned_unit: str | None
    activated_projectile: str | None
    bombardment: str | None
    vortex: str | None


class StatEffect(Strict):
    stat: str
    stat_name: str | None
    value: float
    how: str


class AttributeEffect(Strict):
    attribute: str
    attribute_type: str


class Phase(Strict):
    key: str
    order: int
    target_self: bool
    target_friends: bool
    target_enemies: bool
    duration: float
    effect_type: str
    stat_effects: list[StatEffect]
    attribute_effects: list[AttributeEffect]
    damage_amount: int
    max_damaged_entities: int
    heal_amount: float
    hp_change_frequency: float
    resurrect: bool
    imbue_magical: bool
    imbue_ignition: int
    replenish_ammo: float
    fatigue_change_ratio: float
    ability_recharge_change: float
    mana_regen_mod: float
    cant_move: bool
    execute_ratio: float
    is_hidden_in_ui: bool


@entity("ability")
class Ability(Strict):
    key: str
    name: str | None
    description: str | None
    type: str
    type_name: str | None
    source_type: str
    source_type_name: str | None
    icon: str
    is_hidden_in_ui: bool
    is_unit_upgrade: bool
    requires_effect_enabling: bool
    activation: Activation | None
    phases: list[Phase]
    units: list[Link] = []
    characters: list[Link] = []
    modified_by_effects: list[Link] = []
```

- [ ] **Step 5: Implement `twwiki/model/abilities.py`**

```python
"""Unit abilities: activation parameters and ordered phases."""

from __future__ import annotations

from .context import Context, by_key, grouped, opt

ACTIVATION_FIELDS = (
    "passive", "active_time", "recharge_time", "initial_recharge", "num_uses", "effect_range",
    "min_range", "mana_cost", "wind_up_time", "miscast_chance", "target_self", "target_friends",
    "target_enemies", "target_ground", "affect_self", "num_effected_friendly_units",
    "num_effected_enemy_units",
)
ACTIVATION_KEYS = ("spawned_unit", "activated_projectile", "bombardment", "vortex")
PHASE_FIELDS = (
    "duration", "effect_type", "damage_amount", "max_damaged_entities", "heal_amount",
    "hp_change_frequency", "resurrect", "imbue_magical", "imbue_ignition", "replenish_ammo",
    "fatigue_change_ratio", "ability_recharge_change", "mana_regen_mod", "cant_move",
    "execute_ratio", "is_hidden_in_ui",
)


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    names: dict[str, str | None] = {}
    if ctx.table_exists("unit_abilities"):
        for r in ctx.rows("SELECT key FROM unit_abilities"):
            names[r["key"]] = ctx.catalog_name("ability", f"unit_abilities_onscreen_name_{r['key']}")
    return {"ability": names}


def build(ctx: Context) -> dict[str, list[dict]]:
    if not ctx.require("ability", "unit_abilities"):
        return {"ability": []}
    special = by_key(ctx, "unit_special_abilities", "key")
    phase_links = grouped(ctx, "special_ability_to_special_ability_phase_junctions",
                          "special_ability", '"order", phase')
    phases = by_key(ctx, "special_ability_phases", "id")
    stat_effects = grouped(ctx, "special_ability_phase_stat_effects", "phase", "stat")
    attribute_effects = grouped(ctx, "special_ability_phase_attribute_effects", "phase", "attribute")
    stat_loc = {k: v["localisation"] for k, v in by_key(ctx, "modifiable_unit_stats", "stat_key").items()}

    out = []
    for r in ctx.rows("SELECT * FROM unit_abilities ORDER BY key"):
        key = r["key"]
        built_phases = []
        for link in phase_links.get(key, []):
            phase = phases.get(link["phase"])
            if phase is None:
                ctx.links.missing["ability.phase->special_ability_phase"] += 1
                continue
            built_phases.append(_phase(ctx, link, phase, stat_effects, attribute_effects, stat_loc))
        out.append({
            "key": key,
            "name": ctx.links.name("ability", key),
            "description": ctx.loc.text(f"unit_abilities_tooltip_text_{key}"),
            "type": r["type"],
            "type_name": ctx.loc.text(f"unit_ability_types_onscreen_name_{r['type']}"),
            "source_type": r["source_type"],
            "source_type_name": ctx.loc.text(f"unit_ability_source_types_name_{r['source_type']}"),
            "icon": r["icon_name"],
            "is_hidden_in_ui": r["is_hidden_in_ui"],
            "is_unit_upgrade": r["is_unit_upgrade"],
            "requires_effect_enabling": r["requires_effect_enabling"],
            "activation": _activation(special.get(key)),
            "phases": built_phases,
            "units": [],
            "characters": [],
            "modified_by_effects": [],
        })
    return {"ability": out}


def _activation(row: dict | None) -> dict | None:
    if row is None:
        return None
    activation = {f: row[f] for f in ACTIVATION_FIELDS}
    activation.update({f: opt(row[f]) for f in ACTIVATION_KEYS})
    return activation


def _phase(ctx: Context, link: dict, phase: dict, stat_effects: dict, attribute_effects: dict,
           stat_loc: dict) -> dict:
    built = {
        "key": phase["id"],
        "order": link["order"],
        "target_self": link["target_self"],
        "target_friends": link["target_friends"],
        "target_enemies": link["target_enemies"],
        "stat_effects": [
            {"stat": s["stat"],
             "stat_name": ctx.loc.text(f"unit_stat_localisations_onscreen_name_{stat_loc.get(s['stat'], s['stat'])}"),
             "value": s["value"], "how": s["how"]}
            for s in stat_effects.get(phase["id"], [])
        ],
        "attribute_effects": [
            {"attribute": a["attribute"], "attribute_type": a["attribute_type"]}
            for a in attribute_effects.get(phase["id"], [])
        ],
    }
    built.update({f: phase[f] for f in PHASE_FIELDS})
    return built
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/model/test_abilities.py tests/model/test_context.py -v`
Expected: 9 passed

- [ ] **Step 7: Commit**

```bash
git add twwiki/model/abilities.py twwiki/model/schemas.py twwiki/model/context.py tests/model/test_abilities.py
git commit -m "feat(model): build abilities with activation and phases"
```

### Task 7: Units

**Files:**
- Create: `twwiki/model/units.py`
- Modify: `twwiki/model/schemas.py` (append units section)
- Test: `tests/model/test_units.py`

**Interfaces:**
- Consumes: `Context`, `opt`, `by_key`, `grouped` (Tasks 3, 6); `resolve_unit_sets(ctx)` (Task 4); schemas core.
- Produces:
  - `units.catalog(ctx)` → `{"unit": {key: name}}` where name = `land_units_onscreen_name_<main_units.land_unit>` (naval units without a land unit get `None`).
  - `units.build(ctx)` → `{"unit": [...]}`.
  - Link relations from `unit`: `"abilities"` → ability, `"characters"` → character, `"custom_battle_factions"` → faction, `"recruited_by_buildings"` → building_level. Task 13 uses `"abilities"` for `ability.units` and `"custom_battle_factions"` for `faction.units`.
  - Schemas: `BaseStats`, `MeleeWeapon`, `Projectile`, `MissileWeapon`, `Shield`, `UnitAttribute`, `UnitSetMembership`, `Unit` (`@entity("unit")`).

- [ ] **Step 1: Write the failing tests**

`tests/model/test_units.py`:
```python
from twwiki.model import schemas, units
from tests.model.fixtures import make_context


def main_unit(**o):
    row = {"unit": "gs", "land_unit": "gs_land", "caste": "melee_infantry", "is_naval": False, "tier": 3,
           "num_men": 120, "recruitment_cost": 850, "upkeep_cost": 225, "multiplayer_cost": 700,
           "campaign_cap": -1, "multiplayer_cap": 0}
    row.update(o)
    return row


def land_unit(**o):
    row = {"key": "gs_land", "category": "inf_melee", "class": "inf_mel", "man_entity": "man",
           "primary_melee_weapon": "greatsword", "primary_missile_weapon": "", "armour": "plate",
           "shield": "none", "mount": "", "attribute_group": "gs_attrs", "short_description_text": "gs_short",
           "bonus_hit_points": 68, "melee_attack": 32, "melee_defence": 30, "charge_bonus": 18, "morale": 75,
           "accuracy": 10, "reload": 0, "primary_ammo": 0, "secondary_ammo": 0, "damage_mod_physical": 0,
           "damage_mod_magic": 0, "damage_mod_flame": 0, "damage_mod_missile": 0, "damage_mod_all": 0,
           "healing_power": 1.0, "spell_mastery": 1.0, "num_mounts": 0, "rank_depth": 4}
    row.update(o)
    return row


def unit_context():
    ctx = make_context({
        "main_units": [main_unit(),
                       main_unit(unit="ship", land_unit="", caste="warship", is_naval=True),
                       main_unit(unit="archers", land_unit="arch_land", caste="missile_infantry")],
        "land_units": [land_unit(),
                       land_unit(key="arch_land", primary_melee_weapon="nope", primary_missile_weapon="bow",
                                 attribute_group="", shield="small")],
        "battle_entities": [{"key": "man", "hit_points": 8, "walk_speed": 1.2, "run_speed": 2.8,
                             "charge_speed": 3.5, "fly_speed": 0.0, "mass": 90.0}],
        "melee_weapons": [{"key": "greatsword", "damage": 10, "ap_damage": 25, "bonus_v_large": 0,
                           "bonus_v_infantry": 14, "is_magical": False, "splash_attack_target_size": "",
                           "splash_attack_max_attacks": 0, "splash_attack_power_multiplier": 1.0,
                           "melee_attack_interval": 4.0, "building_damage_multiplier": 1.0, "ignition_amount": 0.0}],
        "missile_weapons": [{"key": "bow", "default_projectile": "arrow"}],
        "projectiles": [{"key": "arrow", "category": "arrow", "damage": 20, "ap_damage": 5, "bonus_v_large": 0,
                         "bonus_v_infantry": 0, "effective_range": 150, "minimum_range": 0, "base_reload_time": 10.0,
                         "projectile_number": 1, "shots_per_volley": 1, "burst_size": 1, "marksmanship_bonus": 0.0,
                         "is_magical": False, "ignition_amount": 0.0, "shockwave_radius": -1.0, "explosion_type": ""}],
        "unit_armour_types": [{"key": "plate", "armour_value": 95}],
        "unit_shield_types": [{"key": "small", "shield_defence_value": 3, "shield_armour_value": 10, "missile_block_chance": 35}],
        "unit_attributes_to_groups_junctions": [{"attribute": "hide_forest", "attribute_group": "gs_attrs"}],
        "land_units_to_unit_abilites_junctions": [{"ability": "hold", "land_unit": "gs_land"},
                                                  {"ability": "missing_ability", "land_unit": "gs_land"}],
        "agent_subtypes": [{"key": "captain", "associated_unit_override": "gs"}],
        "units_custom_battle_permissions": [{"faction": "reikland", "unit": "gs"}, {"faction": "reikland", "unit": "gs"}],
        "building_units_allowed": [{"building": "barracks_2", "unit": "gs"}],
    }, loc={
        "land_units_onscreen_name_gs_land": "Greatswords",
        "unit_description_short_texts_text_gs_short": "Elite melee.",
        "unit_castes_localised_name_melee_infantry": "Melee Infantry",
        "unit_category_localised_name_inf_melee": "Infantry",
        "unit_class_onscreen_inf_mel": "Melee Infantry",
        "unit_attributes_imued_effect_text_hide_forest": "Hide (forest)",
        "unit_attributes_bullet_text_hide_forest": "Hide (forest)||Can hide in forests.",
    })
    for entity_type, names in units.catalog(ctx).items():
        ctx.links.register(entity_type, names)
    ctx.links.register("ability", {"hold": "Hold the Line!"})
    ctx.links.register("character", {"captain": "Empire Captain"})
    ctx.links.register("faction", {"reikland": "Reikland"})
    ctx.links.register("building_level", {"barracks_2": "Barracks"})
    return ctx


def built_units():
    ctx = unit_context()
    return ctx, {u["key"]: u for u in units.build(ctx)["unit"]}


def test_greatswords_stats_weapons_and_links():
    ctx, built = built_units()
    gs = built["gs"]
    assert gs["name"] == "Greatswords" and gs["short_description"] == "Elite melee."
    assert (gs["caste_name"], gs["category_name"], gs["class_name"]) == ("Melee Infantry", "Infantry", "Melee Infantry")
    stats = gs["base_stats"]
    assert (stats["num_men"], stats["hit_points_per_entity"], stats["bonus_hit_points"]) == (120, 8, 68)
    assert (stats["melee_attack"], stats["melee_defence"], stats["armour"]) == (32, 30, 95)
    assert gs["melee_weapon"]["damage"] == 10 and gs["melee_weapon"]["ap_damage"] == 25
    assert gs["missile_weapon"] is None and gs["shield"] is None
    assert gs["attributes"] == [{"key": "hide_forest", "name": "Hide (forest)", "description": "Hide (forest)||Can hide in forests."}]
    assert [a["key"] for a in gs["abilities"]] == ["hold", "missing_ability"]
    assert gs["abilities"][1]["missing"] is True
    assert [c["key"] for c in gs["characters"]] == ["captain"]
    assert [f["key"] for f in gs["custom_battle_factions"]] == ["reikland"]
    assert [b["key"] for b in gs["recruited_by_buildings"]] == ["barracks_2"]
    assert [l["key"] for l in ctx.links.referrers("ability", "hold", "abilities")] == ["gs"]
    schemas.ENTITY_MODELS["unit"].model_validate(gs)


def test_archers_missile_weapon_shield_and_missing_melee_weapon():
    _, built = built_units()
    archers = built["archers"]
    assert archers["melee_weapon"] is None
    assert archers["missile_weapon"]["projectile"]["effective_range"] == 150
    assert archers["shield"]["missile_block_chance"] == 35
    schemas.ENTITY_MODELS["unit"].model_validate(archers)


def test_naval_unit_without_land_unit():
    _, built = built_units()
    ship = built["ship"]
    assert ship["name"] is None and ship["land_unit"] is None and ship["base_stats"] is None
    assert ship["category"] is None and ship["attributes"] == [] and ship["unit_sets"] == []
    schemas.ENTITY_MODELS["unit"].model_validate(ship)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/model/test_units.py -v`
Expected: FAIL with `ImportError: cannot import name 'units' from 'twwiki.model'`

- [ ] **Step 3: Append the units section to `twwiki/model/schemas.py`**

```python
# ---- Units -----------------------------------------------------------------

class BaseStats(Strict):
    num_men: int
    hit_points_per_entity: int | None
    bonus_hit_points: int
    walk_speed: float | None
    run_speed: float | None
    charge_speed: float | None
    fly_speed: float | None
    mass: float | None
    melee_attack: int
    melee_defence: int
    charge_bonus: int
    morale: int
    accuracy: int
    reload: int
    armour: int | None
    primary_ammo: int
    secondary_ammo: int
    damage_mod_physical: int
    damage_mod_magic: int
    damage_mod_flame: int
    damage_mod_missile: int
    damage_mod_all: int
    healing_power: float
    spell_mastery: float
    num_mounts: int
    rank_depth: int


class MeleeWeapon(Strict):
    key: str
    damage: int
    ap_damage: int
    bonus_v_large: int
    bonus_v_infantry: int
    is_magical: bool
    splash_attack_target_size: str | None
    splash_attack_max_attacks: int
    splash_attack_power_multiplier: float
    melee_attack_interval: float
    building_damage_multiplier: float
    ignition_amount: float


class Projectile(Strict):
    key: str
    category: str
    damage: int
    ap_damage: int
    bonus_v_large: int
    bonus_v_infantry: int
    effective_range: int
    minimum_range: int
    base_reload_time: float
    projectile_number: int
    shots_per_volley: int
    burst_size: int
    marksmanship_bonus: float
    is_magical: bool
    ignition_amount: float
    shockwave_radius: float
    explosion_type: str | None


class MissileWeapon(Strict):
    key: str
    projectile: Projectile | None


class Shield(Strict):
    key: str
    shield_defence_value: int
    shield_armour_value: int
    missile_block_chance: int


class UnitAttribute(Strict):
    key: str
    name: str | None
    description: str | None


class UnitSetMembership(Strict):
    key: str
    conditional: bool
    min_exp_level: int | None
    max_exp_level: int | None


@entity("unit")
class Unit(Strict):
    key: str
    name: str | None
    short_description: str | None
    caste: str
    caste_name: str | None
    category: str | None
    category_name: str | None
    unit_class: str | None
    class_name: str | None
    is_naval: bool
    tier: int
    land_unit: str | None
    recruitment_cost: int
    upkeep_cost: int
    multiplayer_cost: int
    campaign_cap: int
    multiplayer_cap: int
    base_stats: BaseStats | None
    melee_weapon: MeleeWeapon | None
    missile_weapon: MissileWeapon | None
    shield: Shield | None
    mount: str | None
    attributes: list[UnitAttribute]
    abilities: list[Link]
    characters: list[Link]
    unit_sets: list[UnitSetMembership]
    custom_battle_factions: list[Link]
    recruited_by_buildings: list[Link]
```

- [ ] **Step 4: Implement `twwiki/model/units.py`**

```python
"""Units: base stats as components, weapons, and what the unit connects to.

Stats are not combined here (no total HP, no buffs); the stat engine does that.
"""

from __future__ import annotations

from collections import defaultdict

from .context import Context, by_key, grouped, opt
from .unit_sets import resolve_unit_sets

LAND_STAT_FIELDS = (
    "bonus_hit_points", "melee_attack", "melee_defence", "charge_bonus", "morale", "accuracy",
    "reload", "primary_ammo", "secondary_ammo", "damage_mod_physical", "damage_mod_magic",
    "damage_mod_flame", "damage_mod_missile", "damage_mod_all", "healing_power", "spell_mastery",
    "num_mounts", "rank_depth",
)
ENTITY_STAT_FIELDS = ("walk_speed", "run_speed", "charge_speed", "fly_speed", "mass")
MELEE_FIELDS = (
    "key", "damage", "ap_damage", "bonus_v_large", "bonus_v_infantry", "is_magical",
    "splash_attack_max_attacks", "splash_attack_power_multiplier", "melee_attack_interval",
    "building_damage_multiplier", "ignition_amount",
)
PROJECTILE_FIELDS = (
    "key", "category", "damage", "ap_damage", "bonus_v_large", "bonus_v_infantry", "effective_range",
    "minimum_range", "base_reload_time", "projectile_number", "shots_per_volley", "burst_size",
    "marksmanship_bonus", "is_magical", "ignition_amount", "shockwave_radius",
)
SHIELD_FIELDS = ("key", "shield_defence_value", "shield_armour_value", "missile_block_chance")


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    names: dict[str, str | None] = {}
    if ctx.table_exists("main_units"):
        for r in ctx.rows("SELECT unit, land_unit FROM main_units"):
            land_unit = opt(r["land_unit"])
            names[r["unit"]] = (ctx.catalog_name("unit", f"land_units_onscreen_name_{land_unit}")
                                if land_unit else None)
            if not land_unit:
                ctx.missing_names["unit"] += 1
    return {"unit": names}


def _distinct(ctx: Context, table: str, key_col: str, value_col: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    if ctx.table_exists(table):
        for r in ctx.rows(f'SELECT DISTINCT "{key_col}" AS k, "{value_col}" AS v FROM "{table}" ORDER BY 1, 2'):
            if opt(r["v"]):
                out[r["k"]].append(r["v"])
    return out


def build(ctx: Context) -> dict[str, list[dict]]:
    if not ctx.require("unit", "main_units", "land_units"):
        return {"unit": []}
    land = by_key(ctx, "land_units", "key")
    entities = by_key(ctx, "battle_entities", "key")
    melee = by_key(ctx, "melee_weapons", "key")
    missile = by_key(ctx, "missile_weapons", "key")
    projectiles = by_key(ctx, "projectiles", "key")
    armour = by_key(ctx, "unit_armour_types", "key")
    shields = by_key(ctx, "unit_shield_types", "key")
    attributes = _distinct(ctx, "unit_attributes_to_groups_junctions", "attribute_group", "attribute")
    abilities = _distinct(ctx, "land_units_to_unit_abilites_junctions", "land_unit", "ability")
    characters = _distinct(ctx, "agent_subtypes", "associated_unit_override", "key")
    factions = _distinct(ctx, "units_custom_battle_permissions", "unit", "faction")
    buildings = _distinct(ctx, "building_units_allowed", "unit", "building")
    unit_sets = resolve_unit_sets(ctx)

    out = []
    for r in ctx.rows("SELECT * FROM main_units ORDER BY unit"):
        key = r["unit"]
        source = ("unit", key)
        lu = land.get(opt(r["land_unit"]))
        link = lambda t, k, rel: ctx.links.link(t, k, source=source, relation=rel)  # noqa: E731
        out.append({
            "key": key,
            "name": ctx.links.name("unit", key),
            "short_description": ctx.loc.text(f"unit_description_short_texts_text_{lu['short_description_text']}") if lu else None,
            "caste": r["caste"],
            "caste_name": ctx.loc.text(f"unit_castes_localised_name_{r['caste']}"),
            "category": lu["category"] if lu else None,
            "category_name": ctx.loc.text(f"unit_category_localised_name_{lu['category']}") if lu else None,
            "unit_class": lu["class"] if lu else None,
            "class_name": ctx.loc.text(f"unit_class_onscreen_{lu['class']}") if lu else None,
            "is_naval": r["is_naval"],
            "tier": r["tier"],
            "land_unit": lu["key"] if lu else None,
            "recruitment_cost": r["recruitment_cost"],
            "upkeep_cost": r["upkeep_cost"],
            "multiplayer_cost": r["multiplayer_cost"],
            "campaign_cap": r["campaign_cap"],
            "multiplayer_cap": r["multiplayer_cap"],
            "base_stats": _base_stats(r, lu, entities, armour) if lu else None,
            "melee_weapon": _melee(melee.get(lu["primary_melee_weapon"])) if lu else None,
            "missile_weapon": _missile(missile.get(opt(lu["primary_missile_weapon"])), projectiles) if lu else None,
            "shield": _shield(shields.get(lu["shield"])) if lu else None,
            "mount": opt(lu["mount"]) if lu else None,
            "attributes": [
                {"key": a, "name": ctx.loc.text(f"unit_attributes_imued_effect_text_{a}"),
                 "description": ctx.loc.text(f"unit_attributes_bullet_text_{a}")}
                for a in (attributes.get(lu["attribute_group"], []) if lu and opt(lu["attribute_group"]) else [])
            ],
            "abilities": [link("ability", a, "abilities") for a in (abilities.get(lu["key"], []) if lu else [])],
            "characters": [link("character", c, "characters") for c in characters.get(key, [])],
            "unit_sets": unit_sets.get(key, []),
            "custom_battle_factions": [link("faction", f, "custom_battle_factions") for f in factions.get(key, [])],
            "recruited_by_buildings": [link("building_level", b, "recruited_by_buildings") for b in buildings.get(key, [])],
        })
    return {"unit": out}


def _base_stats(main: dict, lu: dict, entities: dict, armour: dict) -> dict:
    entity = entities.get(lu["man_entity"])
    stats = {f: lu[f] for f in LAND_STAT_FIELDS}
    stats.update({f: (entity[f] if entity else None) for f in ENTITY_STAT_FIELDS})
    stats["num_men"] = main["num_men"]
    stats["hit_points_per_entity"] = entity["hit_points"] if entity else None
    armour_row = armour.get(lu["armour"])
    stats["armour"] = armour_row["armour_value"] if armour_row else None
    return stats


def _melee(row: dict | None) -> dict | None:
    if row is None:
        return None
    weapon = {f: row[f] for f in MELEE_FIELDS}
    weapon["splash_attack_target_size"] = opt(row["splash_attack_target_size"])
    return weapon


def _missile(row: dict | None, projectiles: dict) -> dict | None:
    if row is None:
        return None
    projectile = projectiles.get(row["default_projectile"])
    built = None
    if projectile is not None:
        built = {f: projectile[f] for f in PROJECTILE_FIELDS}
        built["explosion_type"] = opt(projectile["explosion_type"])
    return {"key": row["key"], "projectile": built}


def _shield(row: dict | None) -> dict | None:
    if row is None or row["key"] == "none":
        return None
    return {f: row[f] for f in SHIELD_FIELDS}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/model/test_units.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add twwiki/model/units.py twwiki/model/schemas.py tests/model/test_units.py
git commit -m "feat(model): build units with base stats, weapons and links"
```

### Task 8: Characters, skills and skill trees

**Files:**
- Create: `twwiki/model/characters.py`
- Modify: `twwiki/model/schemas.py` (append characters section)
- Test: `tests/model/test_characters.py`

**Interfaces:**
- Consumes: `Context`, `opt`, `by_key`, `grouped` (Tasks 3, 6); `effects.effect_application` (Task 5).
- Produces:
  - `characters.catalog(ctx)` → `{"character": {...}, "skill": {...}}`. Character name = associated unit's `land_units_onscreen_name_<land_unit>`, falling back to `agent_subtypes_onscreen_name_override_<key>`.
  - `characters.build(ctx)` → `{"character": [...], "skill": [...]}`.
  - Link relations: character → unit `"associated_unit"`, → faction `"factions"`, → ability `"abilities"`; skill tree node → skill `"skill_tree"` (source is the character). Task 13 uses `"abilities"` (source type character) for `ability.characters`, `"factions"` for `faction.characters`, `"skill_tree"` for `skill.characters`.
  - Skill trees attach to the character named by `character_skill_node_sets.agent_subtype_key`. Sets without a subtype are counted in `ctx.links.missing["skill_tree.no_agent_subtype"]`.
  - Schemas: `LoreOfMagic`, `SkillTreeNode`, `SkillTreeLink`, `SkillLock`, `SkillTree`, `SkillLevel`, `Character` (`@entity("character")`, reverse field `items`), `Skill` (`@entity("skill")`, reverse field `characters`).

- [ ] **Step 1: Write the failing tests**

`tests/model/test_characters.py`:
```python
from twwiki.model import characters, schemas
from tests.model.fixtures import make_context


def subtype(**o):
    row = {"key": "kf", "associated_unit_override": "kf_unit", "magic_lore": "", "is_caster": False,
           "can_equip_ancillaries": True, "recruitable": True, "can_gain_xp": True, "cost": 1100, "cap": -1}
    row.update(o)
    return row


def skill_node(key, skill, tier, indent, **o):
    row = {"key": key, "character_skill_key": skill, "tier": tier, "indent": indent, "points_on_creation": 0,
           "required_num_parents": 0, "visible_in_ui": True, "faction_key": "", "subculture": "", "campaign_key": ""}
    row.update(o)
    return row


def character_context():
    ctx = make_context({
        "agent_subtypes": [subtype(), subtype(key="wizard", associated_unit_override="wiz_unit",
                                             magic_lore="lore_fire", is_caster=True)],
        "main_units": [{"unit": "kf_unit", "land_unit": "kf_land"}, {"unit": "wiz_unit", "land_unit": "wiz_land"}],
        "land_units_to_unit_abilites_junctions": [{"ability": "hold", "land_unit": "kf_land"}],
        "faction_agent_permitted_subtypes": [
            {"agent": "general", "faction": "reikland", "subtype": "kf"},
            {"agent": "general", "faction": "golden_order", "subtype": "kf"},
            {"agent": "wizard", "faction": "reikland", "subtype": "wizard"},
        ],
        "special_ability_groups": [{"ability_group": "lore_fire"}],
        "character_skill_node_sets": [
            {"key": "kf_tree", "agent_subtype_key": "kf", "agent_key": "general", "faction_key": "", "subculture": "",
             "campaign_key": "", "for_army": False, "for_navy": False},
            {"key": "orphan_tree", "agent_subtype_key": "", "agent_key": "champion", "faction_key": "", "subculture": "",
             "campaign_key": "", "for_army": False, "for_navy": False},
        ],
        "character_skill_node_set_items": [{"set": "kf_tree", "item": "n_leader"}, {"set": "kf_tree", "item": "n_mentor"}],
        "character_skill_nodes": [skill_node("n_leader", "leader_of_men", 7, 0),
                                  skill_node("n_mentor", "mentor", 30, 0, subculture="wh_main_sc_emp_empire")],
        "character_skill_node_links": [{"parent_key": "n_leader", "child_key": "n_mentor", "link_type": "REQUIRED",
                                        "initial_descent_tiers": 0}],
        "character_skill_nodes_skill_locks": [{"character_skill": "mentor", "character_skill_node": "n_mentor", "level": 2}],
        "character_skills": [
            {"key": "leader_of_men", "image_path": "leader.png", "unlocked_at_rank": 7, "is_background_skill": False},
            {"key": "mentor", "image_path": "mentor.png", "unlocked_at_rank": 0, "is_background_skill": False},
        ],
        "character_skill_level_to_effects_junctions": [
            {"character_skill_key": "leader_of_men", "effect_key": "e_aura", "effect_scope": "character_to_character_own", "level": 1, "value": 50.0},
            {"character_skill_key": "mentor", "effect_key": "e_xp", "effect_scope": "character_to_character_own", "level": 1, "value": 15.0},
            {"character_skill_key": "mentor", "effect_key": "e_xp", "effect_scope": "character_to_character_own", "level": 2, "value": 30.0},
        ],
        "character_skill_level_details": [{"skill_key": "mentor", "level": 2, "unlocked_at_rank": 12,
                                           "faction_key": "", "subculture_key": "", "campaign_key": "", "image_path": "x"}],
    }, loc={
        "land_units_onscreen_name_kf_land": "Emperor Karl Franz",
        "agent_subtypes_onscreen_name_override_kf": "Legendary Lord",
        "agent_subtypes_onscreen_name_override_wizard": "Bright Wizard",
        "special_ability_groups_name_lore_fire": "Lore of Fire",
        "character_skills_localised_name_leader_of_men": "Leader of Men",
    })
    for entity_type, names in characters.catalog(ctx).items():
        ctx.links.register(entity_type, names)
    ctx.links.register("unit", {"kf_unit": "Emperor Karl Franz", "wiz_unit": None})
    ctx.links.register("ability", {"hold": "Hold the Line!"})
    ctx.links.register("faction", {"reikland": "Reikland", "golden_order": "Golden Order"})
    ctx.links.register("effect", {"e_aura": "Leadership aura size: %+n%", "e_xp": "XP"})
    return ctx


def test_catalog_names_characters_from_their_unit():
    ctx = character_context()
    assert ctx.links.name("character", "kf") == "Emperor Karl Franz"
    assert ctx.links.name("character", "wizard") == "Bright Wizard"


def test_karl_franz_character_and_tree():
    ctx = character_context()
    built = characters.build(ctx)
    kf = {c["key"]: c for c in built["character"]}["kf"]
    assert kf["name"] == "Emperor Karl Franz" and kf["title"] == "Legendary Lord"
    assert kf["agent_types"] == ["general"]
    assert kf["associated_unit"]["key"] == "kf_unit"
    assert [f["key"] for f in kf["factions"]] == ["golden_order", "reikland"]
    assert [a["key"] for a in kf["abilities"]] == ["hold"]
    assert len(kf["skill_trees"]) == 1
    tree = kf["skill_trees"][0]
    assert [n["key"] for n in tree["nodes"]] == ["n_leader", "n_mentor"]
    assert tree["nodes"][1]["subculture"] == "wh_main_sc_emp_empire"
    assert tree["links"] == [{"parent": "n_leader", "child": "n_mentor", "link_type": "REQUIRED", "initial_descent_tiers": 0}]
    assert tree["locks"][0]["skill"]["key"] == "mentor" and tree["locks"][0]["level"] == 2
    assert ctx.links.missing["skill_tree.no_agent_subtype"] == 1
    assert [l["key"] for l in ctx.links.referrers("skill", "mentor", "skill_tree")] == ["kf"]
    schemas.ENTITY_MODELS["character"].model_validate(kf)


def test_wizard_lore_of_magic():
    wizard = {c["key"]: c for c in characters.build(character_context())["character"]}["wizard"]
    assert wizard["lore_of_magic"] == {"key": "lore_fire", "name": "Lore of Fire"}
    assert wizard["skill_trees"] == []
    schemas.ENTITY_MODELS["character"].model_validate(wizard)


def test_skill_levels_and_effects():
    ctx = character_context()
    skills = {s["key"]: s for s in characters.build(ctx)["skill"]}
    leader = skills["leader_of_men"]
    assert leader["name"] == "Leader of Men"
    assert leader["levels"] == [{"level": 1, "unlocked_at_rank": None, "effects": [leader["levels"][0]["effects"][0]]}]
    assert leader["levels"][0]["effects"][0]["value"] == 50.0
    mentor = skills["mentor"]
    assert [(l["level"], l["unlocked_at_rank"]) for l in mentor["levels"]] == [(1, None), (2, 12)]
    for skill in skills.values():
        schemas.ENTITY_MODELS["skill"].model_validate(skill)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/model/test_characters.py -v`
Expected: FAIL with `ImportError: cannot import name 'characters' from 'twwiki.model'`

- [ ] **Step 3: Append the characters section to `twwiki/model/schemas.py`**

```python
# ---- Characters and skills -------------------------------------------------

class LoreOfMagic(Strict):
    key: str
    name: str | None


class SkillTreeNode(Strict):
    key: str
    skill: Link
    tier: int
    indent: int
    points_on_creation: int
    required_num_parents: int
    visible_in_ui: bool
    faction: str | None
    subculture: str | None
    campaign: str | None


class SkillTreeLink(Strict):
    parent: str
    child: str
    link_type: str
    initial_descent_tiers: int


class SkillLock(Strict):
    node: str
    skill: Link
    level: int


class SkillTree(Strict):
    key: str
    agent_type: str | None
    faction: str | None
    subculture: str | None
    campaign: str | None
    for_army: bool
    for_navy: bool
    nodes: list[SkillTreeNode]
    links: list[SkillTreeLink]
    locks: list[SkillLock]


class SkillLevel(Strict):
    level: int
    unlocked_at_rank: int | None
    effects: list[EffectApplication]


@entity("character")
class Character(Strict):
    key: str
    name: str | None
    title: str | None
    description: str | None
    agent_types: list[str]
    associated_unit: Link | None
    lore_of_magic: LoreOfMagic | None
    is_caster: bool
    can_equip_ancillaries: bool
    recruitable: bool
    can_gain_xp: bool
    cost: int
    cap: int
    factions: list[Link]
    abilities: list[Link]
    skill_trees: list[SkillTree]
    items: list[Link] = []


@entity("skill")
class Skill(Strict):
    key: str
    name: str | None
    description: str | None
    image: str
    unlocked_at_rank: int
    is_background_skill: bool
    levels: list[SkillLevel]
    characters: list[Link] = []
```

- [ ] **Step 4: Implement `twwiki/model/characters.py`**

```python
"""Characters (agent subtypes), their skill trees, and skills."""

from __future__ import annotations

from collections import defaultdict

from .context import Context, by_key, grouped, opt
from .effects import effect_application


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {"character": {}, "skill": {}}
    if ctx.table_exists("agent_subtypes"):
        land_unit = {r["unit"]: opt(r["land_unit"]) for r in ctx.rows("SELECT unit, land_unit FROM main_units")} \
            if ctx.table_exists("main_units") else {}
        for r in ctx.rows("SELECT key, associated_unit_override FROM agent_subtypes"):
            lu = land_unit.get(r["associated_unit_override"])
            name = (ctx.loc.text(f"land_units_onscreen_name_{lu}") if lu else None) \
                or ctx.loc.text(f"agent_subtypes_onscreen_name_override_{r['key']}")
            if name is None:
                ctx.missing_names["character"] += 1
            out["character"][r["key"]] = name
    if ctx.table_exists("character_skills"):
        for r in ctx.rows("SELECT key FROM character_skills"):
            out["skill"][r["key"]] = ctx.catalog_name("skill", f"character_skills_localised_name_{r['key']}")
    return out


def build(ctx: Context) -> dict[str, list[dict]]:
    return {"character": _characters(ctx), "skill": _skills(ctx)}


def _characters(ctx: Context) -> list[dict]:
    if not ctx.require("character", "agent_subtypes"):
        return []
    land_unit = {r["unit"]: opt(r["land_unit"]) for r in ctx.rows("SELECT unit, land_unit FROM main_units")} \
        if ctx.table_exists("main_units") else {}
    unit_abilities = grouped(ctx, "land_units_to_unit_abilites_junctions", "land_unit", "ability")
    permitted = grouped(ctx, "faction_agent_permitted_subtypes", "subtype", "faction, agent")
    trees = _skill_trees(ctx)

    out = []
    for r in ctx.rows("SELECT * FROM agent_subtypes ORDER BY key"):
        key = r["key"]
        source = ("character", key)
        lore = opt(r["magic_lore"])
        lu = land_unit.get(r["associated_unit_override"])
        rows = permitted.get(key, [])
        out.append({
            "key": key,
            "name": ctx.links.name("character", key),
            "title": ctx.loc.text(f"agent_subtypes_onscreen_name_override_{key}"),
            "description": ctx.loc.text(f"agent_subtypes_description_text_override_{key}"),
            "agent_types": sorted({p["agent"] for p in rows}),
            "associated_unit": ctx.links.link("unit", opt(r["associated_unit_override"]), source=source,
                                              relation="associated_unit"),
            "lore_of_magic": {"key": lore, "name": ctx.loc.text(f"special_ability_groups_name_{lore}")} if lore else None,
            "is_caster": r["is_caster"],
            "can_equip_ancillaries": r["can_equip_ancillaries"],
            "recruitable": r["recruitable"],
            "can_gain_xp": r["can_gain_xp"],
            "cost": r["cost"],
            "cap": r["cap"],
            "factions": [ctx.links.link("faction", f, source=source, relation="factions")
                         for f in sorted({p["faction"] for p in rows})],
            "abilities": [ctx.links.link("ability", a["ability"], source=source, relation="abilities")
                          for a in (unit_abilities.get(lu, []) if lu else [])],
            "skill_trees": [_tree(ctx, key, t) for t in trees.get(key, [])],
            "items": [],
        })
    return out


def _skill_trees(ctx: Context) -> dict[str, list[dict]]:
    """character key -> raw tree dicts with their node, link and lock rows."""
    if not ctx.table_exists("character_skill_node_sets"):
        return {}
    items = grouped(ctx, "character_skill_node_set_items", "set", "item")
    nodes = by_key(ctx, "character_skill_nodes", "key")
    links = grouped(ctx, "character_skill_node_links", "parent_key", "child_key")
    locks = grouped(ctx, "character_skill_nodes_skill_locks", "character_skill_node", "character_skill, level")

    by_character: dict[str, list[dict]] = defaultdict(list)
    for s in ctx.rows("SELECT * FROM character_skill_node_sets ORDER BY key"):
        subtype = opt(s["agent_subtype_key"])
        if not subtype:
            ctx.links.missing["skill_tree.no_agent_subtype"] += 1
            continue
        node_rows = sorted((nodes[i["item"]] for i in items.get(s["key"], []) if i["item"] in nodes),
                           key=lambda n: (n["indent"], n["tier"], n["key"]))
        node_keys = {n["key"] for n in node_rows}
        by_character[subtype].append({
            "set": s,
            "nodes": node_rows,
            "links": [l for k in sorted(node_keys) for l in links.get(k, [])],
            "locks": [l for k in sorted(node_keys) for l in locks.get(k, [])],
        })
    return by_character


def _tree(ctx: Context, character: str, tree: dict) -> dict:
    source = ("character", character)
    s = tree["set"]
    return {
        "key": s["key"],
        "agent_type": opt(s["agent_key"]),
        "faction": opt(s["faction_key"]),
        "subculture": opt(s["subculture"]),
        "campaign": opt(s["campaign_key"]),
        "for_army": s["for_army"],
        "for_navy": s["for_navy"],
        "nodes": [{
            "key": n["key"],
            "skill": ctx.links.link("skill", n["character_skill_key"], source=source, relation="skill_tree"),
            "tier": n["tier"],
            "indent": n["indent"],
            "points_on_creation": n["points_on_creation"],
            "required_num_parents": n["required_num_parents"],
            "visible_in_ui": n["visible_in_ui"],
            "faction": opt(n["faction_key"]),
            "subculture": opt(n["subculture"]),
            "campaign": opt(n["campaign_key"]),
        } for n in tree["nodes"]],
        "links": [{"parent": l["parent_key"], "child": l["child_key"], "link_type": l["link_type"],
                   "initial_descent_tiers": l["initial_descent_tiers"]} for l in tree["links"]],
        "locks": [{"node": l["character_skill_node"],
                   "skill": ctx.links.link("skill", l["character_skill"], source=source, relation="skill_lock"),
                   "level": l["level"]} for l in tree["locks"]],
    }


def _skills(ctx: Context) -> list[dict]:
    if not ctx.require("skill", "character_skills"):
        return []
    effect_rows = grouped(ctx, "character_skill_level_to_effects_junctions", "character_skill_key", "level, effect_key")
    # Unlock rank per skill level, from the variant that applies everywhere.
    ranks: dict[str, dict[int, int]] = defaultdict(dict)
    if ctx.table_exists("character_skill_level_details"):
        for d in ctx.rows("""SELECT skill_key, level, unlocked_at_rank FROM character_skill_level_details
                             WHERE faction_key = '' AND subculture_key = '' AND campaign_key = ''"""):
            ranks[d["skill_key"]][d["level"]] = d["unlocked_at_rank"]

    out = []
    for r in ctx.rows("SELECT * FROM character_skills ORDER BY key"):
        key = r["key"]
        skill_ranks = ranks.get(key, {})
        levels: dict[int, list[dict]] = defaultdict(list)
        for e in effect_rows.get(key, []):
            levels[e["level"]].append(effect_application(
                ctx, e["effect_key"], scope=e["effect_scope"], value=e["value"], source=("skill", key)))
        for level in skill_ranks:
            levels.setdefault(level, [])
        out.append({
            "key": key,
            "name": ctx.links.name("skill", key),
            "description": ctx.loc.text(f"character_skills_localised_description_{key}"),
            "image": r["image_path"],
            "unlocked_at_rank": r["unlocked_at_rank"],
            "is_background_skill": r["is_background_skill"],
            "levels": [{"level": lvl, "unlocked_at_rank": ranks.get((key, lvl)), "effects": levels[lvl]}
                       for lvl in sorted(levels)],
            "characters": [],
        })
    return out
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/model/test_characters.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add twwiki/model/characters.py twwiki/model/schemas.py tests/model/test_characters.py
git commit -m "feat(model): build characters, skill trees and skills"
```

### Task 9: Technologies, technology trees and resource costs

**Files:**
- Create: `twwiki/model/technologies.py`
- Modify: `twwiki/model/schemas.py` (append technologies section)
- Test: `tests/model/test_technologies.py`

**Interfaces:**
- Consumes: `Context`, `opt`, `by_key`, `grouped` (Tasks 3, 6); `effects.effect_application` (Task 5).
- Produces:
  - `technologies.load_resource_costs(ctx) -> dict[str, dict]`: resource cost key → `{"key", "treasury_cost", "pooled_resources": [{"pooled_resource_factor", "amount", "context"}], "trade_resources": [str]}`. Task 10 reuses it for building levels.
  - `technologies.catalog(ctx)` → `{"technology": {...}, "technology_tree": {...}}`; `technologies.build(ctx)` → same keys with entity lists.
  - Link relations: technology → technology_tree `"placements"`; technology_tree → technology `"tree_nodes"`; technology → technology `"required_technologies"`; technology → building_level `"required_buildings"` and `"unlocked_by_building"`; technology_tree → culture `"culture"`, → subculture `"subculture"`, → faction `"faction"`.
  - Schemas: `PooledResourceCost`, `ResourceCost`, `Placement`, `TreeNode`, `TreeLink`, `Technology` (`@entity("technology")`), `TechnologyTree` (`@entity("technology_tree")`).

- [ ] **Step 1: Write the failing tests**

`tests/model/test_technologies.py`:
```python
from twwiki.model import schemas, technologies
from tests.model.fixtures import make_context


def node(key, tech, tree, rp, tier=0, indent=0, cost_per_round=0, resource_cost=""):
    return {"key": key, "technology_key": tech, "technology_node_set": tree, "tier": tier, "indent": indent,
            "research_points_required": rp, "cost_per_round": cost_per_round, "food_cost": 0,
            "optional_ui_group": "", "resource_cost": resource_cost, "required_parents": 0,
            "pixel_offset_x": 0, "pixel_offset_y": 0, "faction_key": "", "campaign_key": ""}


def tech_context():
    ctx = make_context({
        "technologies": [
            {"key": "heavy_weapons", "building_level": "", "icon_name": "hw.png", "is_civil": False,
             "is_engineering": False, "is_military": True, "is_hidden": False},
            {"key": "agent_unlock", "building_level": "pyramid_1", "icon_name": "a.png", "is_civil": True,
             "is_engineering": False, "is_military": False, "is_hidden": False},
            {"key": "piracy", "building_level": "", "icon_name": "p.png", "is_civil": False,
             "is_engineering": False, "is_military": False, "is_hidden": False},
        ],
        "technology_node_sets": [
            {"key": "emp_civ_reworkd", "culture": "wh_main_emp_empire", "subculture": "", "faction_key": "",
             "campaign_key": "", "colour_hex": "#ffffff"},
            {"key": "emp_wulfhart", "culture": "wh_main_emp_empire", "subculture": "", "faction_key": "wulfhart_faction",
             "campaign_key": "", "colour_hex": "#000000"},
        ],
        "technology_nodes": [
            node("hw_node", "heavy_weapons", "emp_civ_reworkd", 900, tier=1, indent=1),
            node("hw_wulf_node", "heavy_weapons", "emp_wulfhart", 700, tier=0, indent=1),
            node("agent_node", "agent_unlock", "emp_civ_reworkd", 500, cost_per_round=5000, resource_cost="jars_250"),
        ],
        "technology_node_links": [{"parent_key": "agent_node", "child_key": "hw_node", "initial_descent_tiers": 0, "visible_in_ui": True}],
        "technology_required_technology_junctions": [{"technology": "heavy_weapons", "required_technology": "agent_unlock"}],
        "technology_required_building_levels_junctions": [{"technology": "heavy_weapons", "required_building_level": "forge_2"}],
        "technology_effects_junction": [{"technology": "heavy_weapons", "effect": "e_attack", "effect_scope": "faction_to_force_own", "value": 4.0}],
        "resource_costs": [{"id": "jars_250", "treasury_cost": 0}],
        "resource_cost_pooled_resource_junctions": [{"resource_cost": "jars_250", "pooled_resource_factor": "canopic_jars_technology",
                                                     "amount": -250, "context": "absolute"}],
        "resource_cost_trade_resource_junctions": [{"resource_cost": "jars_250", "trade_resource": "res_gems"}],
    }, loc={
        "technologies_onscreen_name_heavy_weapons": "Improved Heavy Weapons",
        "technologies_short_description_heavy_weapons": "Bigger swords.",
        "technology_node_sets_localised_name_emp_civ_reworkd": "Empire Civil Tech",
    })
    for entity_type, names in technologies.catalog(ctx).items():
        ctx.links.register(entity_type, names)
    ctx.links.register("effect", {"e_attack": "Melee attack: %+n"})
    ctx.links.register("building_level", {"pyramid_1": "Pyramid", "forge_2": "Forge"})
    ctx.links.register("culture", {"wh_main_emp_empire": "The Empire"})
    ctx.links.register("faction", {"wulfhart_faction": "Wulfhart"})
    return ctx


def test_resource_costs_embed_pooled_and_trade_resources():
    ctx = tech_context()
    assert technologies.load_resource_costs(ctx)["jars_250"] == {
        "key": "jars_250", "treasury_cost": 0,
        "pooled_resources": [{"pooled_resource_factor": "canopic_jars_technology", "amount": -250, "context": "absolute"}],
        "trade_resources": ["res_gems"],
    }


def test_technology_placements_carry_per_tree_costs():
    ctx = tech_context()
    built = technologies.build(ctx)
    techs = {t["key"]: t for t in built["technology"]}
    hw = techs["heavy_weapons"]
    assert hw["name"] == "Improved Heavy Weapons" and hw["description"] == "Bigger swords."
    assert [(p["tree"]["key"], p["research_points_required"], p["tier"]) for p in hw["placements"]] == [
        ("emp_civ_reworkd", 900, 1), ("emp_wulfhart", 700, 0)]
    assert [t["key"] for t in hw["required_technologies"]] == ["agent_unlock"]
    assert hw["required_buildings"][0]["name"] == "Forge"
    assert hw["effects"][0]["value"] == 4.0 and hw["effects"][0]["source"]["key"] == "heavy_weapons"

    agent = techs["agent_unlock"]
    assert agent["unlocked_by_building"]["key"] == "pyramid_1"
    placement = agent["placements"][0]
    assert placement["cost_per_round"] == 5000
    assert placement["resource_cost"]["pooled_resources"][0]["amount"] == -250

    assert techs["piracy"]["placements"] == []
    for tech in techs.values():
        schemas.ENTITY_MODELS["technology"].model_validate(tech)


def test_technology_tree_scope_nodes_and_links():
    ctx = tech_context()
    trees = {t["key"]: t for t in technologies.build(ctx)["technology_tree"]}
    civ = trees["emp_civ_reworkd"]
    assert civ["name"] == "Empire Civil Tech" and civ["culture"]["name"] == "The Empire"
    assert civ["faction"] is None
    assert [n["key"] for n in civ["nodes"]] == ["agent_node", "hw_node"]
    assert civ["nodes"][1]["technology"]["key"] == "heavy_weapons"
    assert civ["links"] == [{"parent": "agent_node", "child": "hw_node", "initial_descent_tiers": 0, "visible_in_ui": True}]
    assert trees["emp_wulfhart"]["faction"]["key"] == "wulfhart_faction"
    for tree in trees.values():
        schemas.ENTITY_MODELS["technology_tree"].model_validate(tree)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/model/test_technologies.py -v`
Expected: FAIL with `ImportError: cannot import name 'technologies' from 'twwiki.model'`

- [ ] **Step 3: Append the technologies section to `twwiki/model/schemas.py`**

```python
# ---- Technologies ----------------------------------------------------------

class PooledResourceCost(Strict):
    pooled_resource_factor: str
    amount: int
    context: str


class ResourceCost(Strict):
    key: str
    treasury_cost: int
    pooled_resources: list[PooledResourceCost]
    trade_resources: list[str]


class Placement(Strict):
    tree: Link
    node_key: str
    tier: int
    indent: int
    research_points_required: int
    cost_per_round: int
    resource_cost: ResourceCost | None


class TreeNode(Strict):
    key: str
    technology: Link
    tier: int
    indent: int
    research_points_required: int
    cost_per_round: int
    resource_cost: ResourceCost | None
    required_parents: int
    ui_group: str | None
    pixel_offset_x: int
    pixel_offset_y: int


class TreeLink(Strict):
    parent: str
    child: str
    initial_descent_tiers: int
    visible_in_ui: bool


@entity("technology")
class Technology(Strict):
    key: str
    name: str | None
    description: str | None
    long_description: str | None
    icon: str
    is_civil: bool
    is_engineering: bool
    is_military: bool
    is_hidden: bool
    unlocked_by_building: Link | None
    required_technologies: list[Link]
    required_buildings: list[Link]
    effects: list[EffectApplication]
    placements: list[Placement]


@entity("technology_tree")
class TechnologyTree(Strict):
    key: str
    name: str | None
    culture: Link | None
    subculture: Link | None
    faction: Link | None
    campaign: str | None
    colour: str | None
    nodes: list[TreeNode]
    links: list[TreeLink]
```

- [ ] **Step 4: Implement `twwiki/model/technologies.py`**

```python
"""Technologies and research trees.

Research cost lives on the tree node, not the technology: one technology can
sit in several trees at different costs, so each technology lists placements.
"""

from __future__ import annotations

from collections import defaultdict

from .context import Context, by_key, grouped, opt
from .effects import effect_application


def load_resource_costs(ctx: Context) -> dict[str, dict]:
    costs = {
        key: {"key": key, "treasury_cost": row["treasury_cost"], "pooled_resources": [], "trade_resources": []}
        for key, row in by_key(ctx, "resource_costs", "id").items()
    }
    for key, rows in grouped(ctx, "resource_cost_pooled_resource_junctions", "resource_cost",
                             "resource_cost, pooled_resource_factor").items():
        if key in costs:
            costs[key]["pooled_resources"] = [
                {"pooled_resource_factor": r["pooled_resource_factor"], "amount": r["amount"], "context": r["context"]}
                for r in rows]
    for key, rows in grouped(ctx, "resource_cost_trade_resource_junctions", "resource_cost",
                             "resource_cost, trade_resource").items():
        if key in costs:
            costs[key]["trade_resources"] = [r["trade_resource"] for r in rows]
    return costs


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {"technology": {}, "technology_tree": {}}
    if ctx.table_exists("technologies"):
        for r in ctx.rows("SELECT key FROM technologies"):
            out["technology"][r["key"]] = ctx.catalog_name("technology", f"technologies_onscreen_name_{r['key']}")
    if ctx.table_exists("technology_node_sets"):
        for r in ctx.rows("SELECT key FROM technology_node_sets"):
            out["technology_tree"][r["key"]] = ctx.catalog_name(
                "technology_tree", f"technology_node_sets_localised_name_{r['key']}")
    return out


def build(ctx: Context) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {"technology": [], "technology_tree": []}
    costs = load_resource_costs(ctx)
    nodes = ctx.rows("SELECT * FROM technology_nodes ORDER BY technology_node_set, key") \
        if ctx.table_exists("technology_nodes") else []

    if ctx.require("technology", "technologies"):
        placements: dict[str, list[dict]] = defaultdict(list)
        for n in nodes:
            placements[n["technology_key"]].append({
                "tree": ctx.links.link("technology_tree", n["technology_node_set"],
                                       source=("technology", n["technology_key"]), relation="placements"),
                "node_key": n["key"],
                "tier": n["tier"],
                "indent": n["indent"],
                "research_points_required": n["research_points_required"],
                "cost_per_round": n["cost_per_round"],
                "resource_cost": costs.get(opt(n["resource_cost"])),
            })
        required_techs = grouped(ctx, "technology_required_technology_junctions", "technology", "required_technology")
        required_buildings = grouped(ctx, "technology_required_building_levels_junctions", "technology",
                                     "required_building_level")
        effect_rows = grouped(ctx, "technology_effects_junction", "technology", "effect")
        for r in ctx.rows("SELECT * FROM technologies ORDER BY key"):
            key = r["key"]
            source = ("technology", key)
            out["technology"].append({
                "key": key,
                "name": ctx.links.name("technology", key),
                "description": ctx.loc.text(f"technologies_short_description_{key}"),
                "long_description": ctx.loc.text(f"technologies_long_description_{key}"),
                "icon": r["icon_name"],
                "is_civil": r["is_civil"],
                "is_engineering": r["is_engineering"],
                "is_military": r["is_military"],
                "is_hidden": r["is_hidden"],
                "unlocked_by_building": ctx.links.link("building_level", opt(r["building_level"]),
                                                       source=source, relation="unlocked_by_building"),
                "required_technologies": [
                    ctx.links.link("technology", j["required_technology"], source=source, relation="required_technologies")
                    for j in required_techs.get(key, [])],
                "required_buildings": [
                    ctx.links.link("building_level", j["required_building_level"], source=source, relation="required_buildings")
                    for j in required_buildings.get(key, [])],
                "effects": [effect_application(ctx, e["effect"], scope=e["effect_scope"], value=e["value"], source=source)
                            for e in effect_rows.get(key, [])],
                "placements": placements.get(key, []),
            })

    if ctx.require("technology_tree", "technology_node_sets", "technology_nodes"):
        tree_nodes: dict[str, list[dict]] = defaultdict(list)
        node_tree = {}
        for n in nodes:
            node_tree[n["key"]] = n["technology_node_set"]
            tree_nodes[n["technology_node_set"]].append({
                "key": n["key"],
                "technology": ctx.links.link("technology", n["technology_key"],
                                             source=("technology_tree", n["technology_node_set"]), relation="tree_nodes"),
                "tier": n["tier"],
                "indent": n["indent"],
                "research_points_required": n["research_points_required"],
                "cost_per_round": n["cost_per_round"],
                "resource_cost": costs.get(opt(n["resource_cost"])),
                "required_parents": n["required_parents"],
                "ui_group": opt(n["optional_ui_group"]),
                "pixel_offset_x": n["pixel_offset_x"],
                "pixel_offset_y": n["pixel_offset_y"],
            })
        tree_links: dict[str, list[dict]] = defaultdict(list)
        if ctx.table_exists("technology_node_links"):
            for l in ctx.rows("SELECT * FROM technology_node_links ORDER BY parent_key, child_key"):
                tree = node_tree.get(l["parent_key"])
                if tree:
                    tree_links[tree].append({"parent": l["parent_key"], "child": l["child_key"],
                                             "initial_descent_tiers": l["initial_descent_tiers"],
                                             "visible_in_ui": l["visible_in_ui"]})
        for r in ctx.rows("SELECT * FROM technology_node_sets ORDER BY key"):
            key = r["key"]
            source = ("technology_tree", key)
            out["technology_tree"].append({
                "key": key,
                "name": ctx.links.name("technology_tree", key),
                "culture": ctx.links.link("culture", opt(r["culture"]), source=source, relation="culture"),
                "subculture": ctx.links.link("subculture", opt(r["subculture"]), source=source, relation="subculture"),
                "faction": ctx.links.link("faction", opt(r["faction_key"]), source=source, relation="faction"),
                "campaign": opt(r["campaign_key"]),
                "colour": opt(r["colour_hex"]),
                "nodes": tree_nodes.get(key, []),
                "links": tree_links.get(key, []),
            })
    return out
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/model/test_technologies.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add twwiki/model/technologies.py twwiki/model/schemas.py tests/model/test_technologies.py
git commit -m "feat(model): build technologies with per-tree research costs and trees"
```

### Task 10: Building levels and chains

**Files:**
- Create: `twwiki/model/buildings.py`
- Modify: `twwiki/model/schemas.py` (append buildings section)
- Test: `tests/model/test_buildings.py`

**Interfaces:**
- Consumes: `Context`, `opt`, `by_key`, `grouped` (Tasks 3, 6); `effects.effect_application` (Task 5); `technologies.load_resource_costs` and `schemas.ResourceCost` (Task 9).
- Produces:
  - `buildings.level_name(ctx, level_key: str, variants: list[dict]) -> str | None`: culture-variant name, generic variant (empty culture, subculture and faction) first, then by culture, subculture, faction; skips empty loc text.
  - `buildings.catalog(ctx)` → `{"building_level": {...}, "building_chain": {...}}`. Chain name = `building_chains_encyclopedia_name_<key>`, falling back to `building_chains_chain_tooltip_<key>`.
  - `buildings.build(ctx)` → same keys with entity lists.
  - Link relations: building_level → building_chain `"chain"`, → unit `"units_recruited"`; building_chain → building_level `"levels"`.
  - Schemas: `BuildingLevel` (`@entity("building_level")`), `BuildingChain` (`@entity("building_chain")`).

- [ ] **Step 1: Write the failing tests**

`tests/model/test_buildings.py`:
```python
from twwiki.model import buildings, schemas
from tests.model.fixtures import make_context


def level(key, chain, lvl, **o):
    row = {"level_name": key, "chain": chain, "level": lvl, "create_time": 1, "create_cost": 750, "upkeep_cost": 0,
           "only_in_capital": False, "faction_unique": False, "can_convert": True, "visible_in_ui": True,
           "development_point_cost": 0, "food_cost": 0, "resource_cost": ""}
    row.update(o)
    return row


def variant(building, culture="", subculture="", faction="", short=""):
    return {"building": building, "culture": culture, "subculture": subculture, "faction": faction,
            "short_description": short, "icon": "", "disables": False}


def building_context():
    ctx = make_context({
        "building_levels": [level("barracks_1", "emp_barracks", 0),
                            level("barracks_2", "emp_barracks", 1, create_cost=1500, resource_cost="scrap_50"),
                            level("tower", "tower_chain", 0)],
        "building_chains": [{"key": "emp_barracks", "chain_category": "military", "in_encyclopedia": True},
                            {"key": "tower_chain", "chain_category": "", "in_encyclopedia": False}],
        "building_culture_variants": [
            variant("barracks_1", culture="wh_main_emp_empire", short="barracks_1"),
            variant("tower", faction="followers"),
            variant("tower"),
        ],
        "building_effects_junction": [
            {"building": "barracks_1", "effect": "e_upkeep", "effect_scope": "province_to_province_own", "value": -5.0,
             "value_damaged": -2.0, "value_ruined": 0.0, "context_requirement": "IsChaosCampaign"}],
        "building_units_allowed": [{"building": "barracks_1", "unit": "spearmen"}],
        "resource_costs": [{"id": "scrap_50", "treasury_cost": 0}],
    }, loc={
        "building_culture_variants_name_barracks_1wh_main_emp_empire": "Training Field",
        "building_culture_variants_name_towerfollowers": "Faction Tower",
        "building_culture_variants_name_tower": "Black Tower",
        "building_short_description_texts_short_description_barracks_1": "Drill troops.",
        "building_chains_encyclopedia_name_emp_barracks": "",
        "building_chains_chain_tooltip_emp_barracks": "Barracks",
    })
    for entity_type, names in buildings.catalog(ctx).items():
        ctx.links.register(entity_type, names)
    ctx.links.register("effect", {"e_upkeep": "Upkeep"})
    ctx.links.register("unit", {"spearmen": "Spearmen"})
    return ctx


def test_level_names_prefer_generic_variant():
    ctx = building_context()
    assert ctx.links.name("building_level", "barracks_1") == "Training Field"
    assert ctx.links.name("building_level", "tower") == "Black Tower"
    assert ctx.links.name("building_level", "barracks_2") is None
    assert ctx.links.name("building_chain", "emp_barracks") == "Barracks"


def test_training_field_level():
    ctx = building_context()
    levels = {b["key"]: b for b in buildings.build(ctx)["building_level"]}
    tf = levels["barracks_1"]
    assert tf["chain"]["name"] == "Barracks" and tf["level"] == 0 and tf["create_cost"] == 750
    assert tf["cultures"] == ["wh_main_emp_empire"]
    assert tf["short_description"] == "Drill troops."
    effect = tf["effects"][0]
    assert (effect["value"], effect["value_damaged"], effect["value_ruined"]) == (-5.0, -2.0, 0.0)
    assert effect["context_requirement"] == "IsChaosCampaign"
    assert [u["key"] for u in tf["units_recruited"]] == ["spearmen"]
    assert levels["barracks_2"]["resource_cost"]["key"] == "scrap_50"
    for b in levels.values():
        schemas.ENTITY_MODELS["building_level"].model_validate(b)


def test_chain_lists_levels_in_order():
    ctx = building_context()
    chains = {c["key"]: c for c in buildings.build(ctx)["building_chain"]}
    assert [l["key"] for l in chains["emp_barracks"]["levels"]] == ["barracks_1", "barracks_2"]
    assert chains["tower_chain"]["category"] is None
    for c in chains.values():
        schemas.ENTITY_MODELS["building_chain"].model_validate(c)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/model/test_buildings.py -v`
Expected: FAIL with `ImportError: cannot import name 'buildings' from 'twwiki.model'`

- [ ] **Step 3: Append the buildings section to `twwiki/model/schemas.py`**

```python
# ---- Buildings -------------------------------------------------------------

@entity("building_level")
class BuildingLevel(Strict):
    key: str
    name: str | None
    short_description: str | None
    chain: Link | None
    level: int
    create_time: int
    create_cost: int
    upkeep_cost: int
    development_point_cost: int
    food_cost: int
    only_in_capital: bool
    faction_unique: bool
    can_convert: bool
    visible_in_ui: bool
    resource_cost: ResourceCost | None
    cultures: list[str]
    effects: list[EffectApplication]
    units_recruited: list[Link]


@entity("building_chain")
class BuildingChain(Strict):
    key: str
    name: str | None
    category: str | None
    in_encyclopedia: bool
    levels: list[Link]
```

- [ ] **Step 4: Implement `twwiki/model/buildings.py`**

```python
"""Building levels and chains.

Level names live on culture variants, keyed by building + culture + subculture
+ faction concatenated without separators. The generic variant wins.
"""

from __future__ import annotations

from .context import Context, grouped, opt
from .effects import effect_application
from .technologies import load_resource_costs


def _variant_order(v: dict) -> tuple:
    specific = bool(opt(v["culture"]) or opt(v["subculture"]) or opt(v["faction"]))
    return (specific, v["culture"] or "", v["subculture"] or "", v["faction"] or "")


def level_name(ctx: Context, level_key: str, variants: list[dict]) -> str | None:
    for v in sorted(variants, key=_variant_order):
        text = ctx.loc.text("building_culture_variants_name_" + level_key
                            + (v["culture"] or "") + (v["subculture"] or "") + (v["faction"] or ""))
        if text:
            return text
    return None


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {"building_level": {}, "building_chain": {}}
    variants = grouped(ctx, "building_culture_variants", "building", "building")
    if ctx.table_exists("building_levels"):
        for r in ctx.rows("SELECT level_name FROM building_levels"):
            key = r["level_name"]
            name = level_name(ctx, key, variants.get(key, []))
            if name is None:
                ctx.missing_names["building_level"] += 1
            out["building_level"][key] = name
    if ctx.table_exists("building_chains"):
        for r in ctx.rows("SELECT key FROM building_chains"):
            name = ctx.loc.text(f"building_chains_encyclopedia_name_{r['key']}") \
                or ctx.loc.text(f"building_chains_chain_tooltip_{r['key']}")
            if name is None:
                ctx.missing_names["building_chain"] += 1
            out["building_chain"][r["key"]] = name
    return out


def build(ctx: Context) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {"building_level": [], "building_chain": []}
    if not ctx.require("building_level", "building_levels"):
        ctx.require("building_chain", "building_chains")
        return out
    variants = grouped(ctx, "building_culture_variants", "building", "building")
    effect_rows = grouped(ctx, "building_effects_junction", "building", "effect, context_requirement")
    recruits = grouped(ctx, "building_units_allowed", "building", "unit")
    costs = load_resource_costs(ctx)
    levels = ctx.rows("SELECT * FROM building_levels ORDER BY chain, level, level_name")

    for r in sorted(levels, key=lambda l: l["level_name"]):
        key = r["level_name"]
        source = ("building_level", key)
        own_variants = sorted(variants.get(key, []), key=_variant_order)
        short = next((ctx.loc.text(f"building_short_description_texts_short_description_{v['short_description']}")
                      for v in own_variants if opt(v["short_description"])), None)
        out["building_level"].append({
            "key": key,
            "name": ctx.links.name("building_level", key),
            "short_description": short,
            "chain": ctx.links.link("building_chain", r["chain"], source=source, relation="chain"),
            "level": r["level"],
            "create_time": r["create_time"],
            "create_cost": r["create_cost"],
            "upkeep_cost": r["upkeep_cost"],
            "development_point_cost": r["development_point_cost"],
            "food_cost": r["food_cost"],
            "only_in_capital": r["only_in_capital"],
            "faction_unique": r["faction_unique"],
            "can_convert": r["can_convert"],
            "visible_in_ui": r["visible_in_ui"],
            "resource_cost": costs.get(opt(r["resource_cost"])),
            "cultures": sorted({v["culture"] for v in own_variants if opt(v["culture"])}),
            "effects": [effect_application(
                ctx, e["effect"], scope=e["effect_scope"], value=e["value"], source=source,
                value_damaged=e["value_damaged"], value_ruined=e["value_ruined"],
                context_requirement=opt(e["context_requirement"]))
                for e in effect_rows.get(key, [])],
            "units_recruited": [ctx.links.link("unit", u, source=source, relation="units_recruited")
                                for u in sorted({row["unit"] for row in recruits.get(key, [])})],
        })

    if ctx.require("building_chain", "building_chains"):
        chain_levels = grouped(ctx, "building_levels", "chain", "level, level_name")
        for r in ctx.rows("SELECT * FROM building_chains ORDER BY key"):
            key = r["key"]
            out["building_chain"].append({
                "key": key,
                "name": ctx.links.name("building_chain", key),
                "category": opt(r["chain_category"]),
                "in_encyclopedia": r["in_encyclopedia"],
                "levels": [ctx.links.link("building_level", l["level_name"], source=("building_chain", key),
                                          relation="levels") for l in chain_levels.get(key, [])],
            })
    return out
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/model/test_buildings.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add twwiki/model/buildings.py twwiki/model/schemas.py tests/model/test_buildings.py
git commit -m "feat(model): build building levels and chains"
```

### Task 11: Items and traits

**Files:**
- Create: `twwiki/model/items.py`
- Modify: `twwiki/model/schemas.py` (append items section)
- Test: `tests/model/test_items.py`

**Interfaces:**
- Consumes: `Context`, `opt`, `by_key`, `grouped` (Tasks 3, 6); `effects.effect_application` (Task 5).
- Produces:
  - `items.catalog(ctx)` → `{"item": {...}, "trait": {...}}`. Item name = `ancillaries_onscreen_name_<key>`. Trait name = onscreen name of the trait level whose key equals the trait key, otherwise of its lowest level.
  - `items.build(ctx)` → `{"item": [...], "trait": [...]}`.
  - Link relations: item → character `"agent_subtypes"` (Task 13 fills `character.items` from it), item → skill `"required_skills"`, item → unit `"bodyguard"`, trait → trait `"antitraits"`.
  - Schemas: `RequiredSkill`, `Item` (`@entity("item")`), `TraitLevel`, `Trait` (`@entity("trait")`).

- [ ] **Step 1: Write the failing tests**

`tests/model/test_items.py`:
```python
from twwiki.model import items, schemas
from tests.model.fixtures import make_context


def ancillary(**o):
    row = {"key": "blue_khepra", "type": "wh_main_anc_arcane_item", "applies_to": "character", "transferrable": True,
           "unique_to_world": True, "unique_to_faction": False, "legendary_item": False, "category": "arcane_item",
           "subcategory": "", "provided_bodyguard_unit": ""}
    row.update(o)
    return row


def trait_level(key, trait, level, points=0):
    return {"key": key, "trait": trait, "level": level, "threshold_points": points}


def items_context():
    ctx = make_context({
        "ancillaries": [ancillary(), ancillary(key="banner", provided_bodyguard_unit="gs", legendary_item=True, subcategory="banner")],
        "ancillary_to_effects": [{"ancillary": "blue_khepra", "effect": "e_power", "effect_scope": "character_to_character_own", "value": 10.0}],
        "ancillary_to_included_agents": [{"ancillary": "blue_khepra", "agent": "wizard"}, {"ancillary": "blue_khepra", "agent": "general"}],
        "ancillaries_included_agent_subtypes": [{"ancillary": "blue_khepra", "agent_subtype": "liche_priest"}],
        "ancillaries_required_skills": [{"ancillary": "banner", "required_skill": "bearer", "required_skill_level": 1}],
        "character_traits": [
            {"key": "brave", "no_going_back_level": 0, "hidden": False, "precedence": 1, "icon": "personality"},
            {"key": "coward", "no_going_back_level": 0, "hidden": True, "precedence": 2, "icon": "personality"},
        ],
        "character_trait_levels": [trait_level("brave_2", "brave", 2, 10), trait_level("brave", "brave", 1, 5),
                                   trait_level("coward_1", "coward", 1)],
        "trait_level_effects": [{"trait_level": "brave", "effect": "e_morale", "effect_scope": "character_to_force_own", "value": 2.0}],
        "trait_to_antitraits": [{"trait": "brave", "antitrait": "coward"}],
    }, loc={
        "ancillaries_onscreen_name_blue_khepra": "Blue Khepra",
        "ancillaries_colour_text_blue_khepra": "Sapphires.",
        "character_trait_levels_onscreen_name_brave": "Brave",
        "character_trait_levels_onscreen_name_brave_2": "Fearless",
        "character_trait_levels_onscreen_name_coward_1": "Coward",
    })
    for entity_type, names in items.catalog(ctx).items():
        ctx.links.register(entity_type, names)
    ctx.links.register("effect", {"e_power": "Power", "e_morale": "Morale"})
    ctx.links.register("character", {"liche_priest": "Liche Priest"})
    ctx.links.register("skill", {"bearer": "Battle Standard Bearer"})
    ctx.links.register("unit", {"gs": "Greatswords"})
    return ctx


def test_item_fields_and_links():
    ctx = items_context()
    built = {i["key"]: i for i in items.build(ctx)["item"]}
    khepra = built["blue_khepra"]
    assert khepra["name"] == "Blue Khepra" and khepra["description"] == "Sapphires."
    assert khepra["agent_types"] == ["general", "wizard"]
    assert [s["key"] for s in khepra["agent_subtypes"]] == ["liche_priest"]
    assert khepra["effects"][0]["value"] == 10.0
    assert [l["key"] for l in ctx.links.referrers("character", "liche_priest", "agent_subtypes")] == ["blue_khepra"]
    banner = built["banner"]
    assert banner["legendary"] is True and banner["subcategory"] == "banner"
    assert banner["bodyguard_unit"]["key"] == "gs"
    assert banner["required_skills"] == [{"skill": {"type": "skill", "key": "bearer", "name": "Battle Standard Bearer", "missing": False}, "level": 1}]
    for item in built.values():
        schemas.ENTITY_MODELS["item"].model_validate(item)


def test_trait_names_levels_and_antitraits():
    ctx = items_context()
    assert ctx.links.name("trait", "brave") == "Brave"
    assert ctx.links.name("trait", "coward") == "Coward"
    traits = {t["key"]: t for t in items.build(ctx)["trait"]}
    brave = traits["brave"]
    assert [(l["key"], l["level"], l["name"]) for l in brave["levels"]] == [("brave", 1, "Brave"), ("brave_2", 2, "Fearless")]
    assert brave["levels"][0]["effects"][0]["value"] == 2.0
    assert [a["key"] for a in brave["antitraits"]] == ["coward"]
    for trait in traits.values():
        schemas.ENTITY_MODELS["trait"].model_validate(trait)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/model/test_items.py -v`
Expected: FAIL with `ImportError: cannot import name 'items' from 'twwiki.model'`

- [ ] **Step 3: Append the items section to `twwiki/model/schemas.py`**

```python
# ---- Items and traits ------------------------------------------------------

class RequiredSkill(Strict):
    skill: Link
    level: int


@entity("item")
class Item(Strict):
    key: str
    name: str | None
    description: str | None
    explanation: str | None
    type: str
    category: str
    subcategory: str | None
    legendary: bool
    applies_to: str
    transferrable: bool
    unique_to_world: bool
    unique_to_faction: bool
    bodyguard_unit: Link | None
    agent_types: list[str]
    agent_subtypes: list[Link]
    required_skills: list[RequiredSkill]
    effects: list[EffectApplication]


class TraitLevel(Strict):
    key: str
    level: int
    name: str | None
    description: str | None
    threshold_points: int
    effects: list[EffectApplication]


@entity("trait")
class Trait(Strict):
    key: str
    name: str | None
    hidden: bool
    precedence: int
    icon: str
    no_going_back_level: int
    levels: list[TraitLevel]
    antitraits: list[Link]
```

- [ ] **Step 4: Implement `twwiki/model/items.py`**

```python
"""Items (ancillaries) and character traits."""

from __future__ import annotations

from .context import Context, grouped, opt
from .effects import effect_application


def _trait_levels(ctx: Context) -> dict[str, list[dict]]:
    return grouped(ctx, "character_trait_levels", "trait", "level, key")


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {"item": {}, "trait": {}}
    if ctx.table_exists("ancillaries"):
        for r in ctx.rows("SELECT key FROM ancillaries"):
            out["item"][r["key"]] = ctx.catalog_name("item", f"ancillaries_onscreen_name_{r['key']}")
    if ctx.table_exists("character_traits"):
        levels = _trait_levels(ctx)
        for r in ctx.rows("SELECT key FROM character_traits"):
            key = r["key"]
            own = [l for l in levels.get(key, []) if l["key"] == key]
            chosen = own[0] if own else (levels.get(key) or [None])[0]
            name = ctx.loc.text(f"character_trait_levels_onscreen_name_{chosen['key']}") if chosen else None
            if name is None:
                ctx.missing_names["trait"] += 1
            out["trait"][key] = name
    return out


def build(ctx: Context) -> dict[str, list[dict]]:
    return {"item": _items(ctx), "trait": _traits(ctx)}


def _items(ctx: Context) -> list[dict]:
    if not ctx.require("item", "ancillaries"):
        return []
    effect_rows = grouped(ctx, "ancillary_to_effects", "ancillary", "effect")
    agents = grouped(ctx, "ancillary_to_included_agents", "ancillary", "agent")
    subtypes = grouped(ctx, "ancillaries_included_agent_subtypes", "ancillary", "agent_subtype")
    required = grouped(ctx, "ancillaries_required_skills", "ancillary", "required_skill")

    out = []
    for r in ctx.rows("SELECT * FROM ancillaries ORDER BY key"):
        key = r["key"]
        source = ("item", key)
        out.append({
            "key": key,
            "name": ctx.links.name("item", key),
            "description": ctx.loc.text(f"ancillaries_colour_text_{key}"),
            "explanation": ctx.loc.text(f"ancillaries_explanation_text_{key}"),
            "type": r["type"],
            "category": r["category"],
            "subcategory": opt(r["subcategory"]),
            "legendary": r["legendary_item"],
            "applies_to": r["applies_to"],
            "transferrable": r["transferrable"],
            "unique_to_world": r["unique_to_world"],
            "unique_to_faction": r["unique_to_faction"],
            "bodyguard_unit": ctx.links.link("unit", opt(r["provided_bodyguard_unit"]), source=source, relation="bodyguard"),
            "agent_types": sorted({a["agent"] for a in agents.get(key, [])}),
            "agent_subtypes": [ctx.links.link("character", s["agent_subtype"], source=source, relation="agent_subtypes")
                               for s in subtypes.get(key, [])],
            "required_skills": [{"skill": ctx.links.link("skill", s["required_skill"], source=source, relation="required_skills"),
                                 "level": s["required_skill_level"]} for s in required.get(key, [])],
            "effects": [effect_application(ctx, e["effect"], scope=e["effect_scope"], value=e["value"], source=source)
                        for e in effect_rows.get(key, [])],
        })
    return out


def _traits(ctx: Context) -> list[dict]:
    if not ctx.require("trait", "character_traits"):
        return []
    levels = _trait_levels(ctx)
    effect_rows = grouped(ctx, "trait_level_effects", "trait_level", "effect")
    antitraits = grouped(ctx, "trait_to_antitraits", "trait", "antitrait")

    out = []
    for r in ctx.rows("SELECT * FROM character_traits ORDER BY key"):
        key = r["key"]
        source = ("trait", key)
        out.append({
            "key": key,
            "name": ctx.links.name("trait", key),
            "hidden": r["hidden"],
            "precedence": r["precedence"],
            "icon": r["icon"],
            "no_going_back_level": r["no_going_back_level"],
            "levels": [{
                "key": l["key"],
                "level": l["level"],
                "name": ctx.loc.text(f"character_trait_levels_onscreen_name_{l['key']}"),
                "description": ctx.loc.text(f"character_trait_levels_colour_text_{l['key']}"),
                "threshold_points": l["threshold_points"],
                "effects": [effect_application(ctx, e["effect"], scope=e["effect_scope"], value=e["value"], source=source)
                            for e in effect_rows.get(l["key"], [])],
            } for l in levels.get(key, [])],
            "antitraits": [ctx.links.link("trait", a["antitrait"], source=source, relation="antitraits")
                           for a in antitraits.get(key, [])],
        })
    return out
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/model/test_items.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add twwiki/model/items.py twwiki/model/schemas.py tests/model/test_items.py
git commit -m "feat(model): build items and traits"
```

### Task 12: Factions, cultures, subcultures, difficulty levels and campaign variables

**Files:**
- Create: `twwiki/model/factions.py`
- Modify: `twwiki/model/schemas.py` (append factions section)
- Test: `tests/model/test_factions.py`

**Interfaces:**
- Consumes: `Context`, `opt`, `by_key`, `grouped` (Tasks 3, 6); `effects.effect_application` (Task 5).
- Produces:
  - `factions.catalog(ctx)` → names for `faction` (`factions_screen_name_<key>`), `culture` (`cultures_name_<key>`), `subculture` (`cultures_subcultures_name_<subculture>`), `difficulty_level` (key = level as string, name `None`, not counted as missing), `campaign_variable` (name = the variable key).
  - `factions.build(ctx)` → entity lists for those five types.
  - Link relations: faction → subculture `"subculture"`, faction → culture `"culture"`, subculture → culture `"culture"`. Task 13 uses them for `culture.subcultures` (source type subculture), `culture.factions` and `subculture.factions` (source type faction).
  - Schemas: `Faction`, `Culture`, `Subculture`, `DifficultyEffect`, `DifficultyLevel`, `CampaignVariableOverride`, `CampaignVariable`, each registered with `@entity`.

- [ ] **Step 1: Write the failing tests**

`tests/model/test_factions.py`:
```python
from twwiki.model import factions, schemas
from tests.model.fixtures import make_context


def factions_context():
    ctx = make_context({
        "factions": [{"key": "reikland", "subculture": "sc_empire", "category": "", "is_rebel": False,
                      "is_quest_faction": False, "flags_path": "ui/flags/reikland", "primary_colour_hex": "#ffcc00"}],
        "cultures": [{"key": "empire"}],
        "cultures_subcultures": [{"subculture": "sc_empire", "culture": "empire"}],
        "campaign_difficulty_handicap_effects": [
            {"campaign_difficulty_handicap": 2, "human": False, "effect": "e_research_cost", "effect_scope": "faction_to_faction_own_unseen",
             "effect_value": -100.0, "optional_campaign_key": ""},
            {"campaign_difficulty_handicap": 2, "human": True, "effect": "e_growth", "effect_scope": "faction_to_province_own",
             "effect_value": 5.0, "optional_campaign_key": "main_warhammer"},
        ],
        "campaign_variables": [{"variable_key": "base_research_points_per_turn", "value": 100.0},
                               {"variable_key": "minimum_research_rate", "value": 5.0}],
        "campaigns_campaign_variables_junctions": [{"variable_key": "minimum_research_rate", "campaign_name": "wh3_main_chaos",
                                                   "value": 7.0, "difficulty": "", "campaign_type": ""}],
    }, loc={
        "factions_screen_name_reikland": "Reikland",
        "cultures_name_empire": "The Empire",
        "cultures_subcultures_name_sc_empire": "The Empire",
    })
    for entity_type, names in factions.catalog(ctx).items():
        ctx.links.register(entity_type, names)
    ctx.links.register("effect", {"e_research_cost": "Research cost", "e_growth": "Growth"})
    return ctx


def test_faction_culture_and_subculture_links():
    ctx = factions_context()
    built = factions.build(ctx)
    reikland = built["faction"][0]
    assert reikland["name"] == "Reikland"
    assert reikland["subculture"]["key"] == "sc_empire" and reikland["culture"]["name"] == "The Empire"
    assert built["subculture"][0]["culture"]["key"] == "empire"
    assert [l["key"] for l in ctx.links.referrers("culture", "empire", "culture", source_type="faction")] == ["reikland"]
    for entity_type in ("faction", "culture", "subculture"):
        for entity in built[entity_type]:
            schemas.ENTITY_MODELS[entity_type].model_validate(entity)


def test_difficulty_levels_split_ai_and_human():
    ctx = factions_context()
    assert ctx.links.has("difficulty_level", "2") and ctx.missing_names["difficulty_level"] == 0
    level = factions.build(ctx)["difficulty_level"][0]
    assert level["key"] == "2" and level["level"] == 2
    assert level["ai"][0]["application"]["value"] == -100.0 and level["ai"][0]["campaign"] is None
    assert level["ai"][0]["application"]["source"] == {"type": "difficulty_level", "key": "2", "name": None, "missing": False}
    assert level["human"][0]["campaign"] == "main_warhammer"
    schemas.ENTITY_MODELS["difficulty_level"].model_validate(level)


def test_campaign_variables_with_overrides():
    variables = {v["key"]: v for v in factions.build(factions_context())["campaign_variable"]}
    assert variables["base_research_points_per_turn"]["value"] == 100.0
    assert variables["base_research_points_per_turn"]["overrides"] == []
    assert variables["minimum_research_rate"]["overrides"] == [
        {"campaign": "wh3_main_chaos", "difficulty": None, "campaign_type": None, "value": 7.0}]
    for v in variables.values():
        schemas.ENTITY_MODELS["campaign_variable"].model_validate(v)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/model/test_factions.py -v`
Expected: FAIL with `ImportError: cannot import name 'factions' from 'twwiki.model'`

- [ ] **Step 3: Append the factions section to `twwiki/model/schemas.py`**

```python
# ---- Factions, cultures, difficulty, campaign variables ---------------------

@entity("faction")
class Faction(Strict):
    key: str
    name: str | None
    adjective: str | None
    subculture: Link | None
    culture: Link | None
    category: str | None
    is_rebel: bool
    is_quest_faction: bool
    flags_path: str
    primary_colour: str | None
    units: list[Link] = []
    characters: list[Link] = []


@entity("culture")
class Culture(Strict):
    key: str
    name: str | None
    subcultures: list[Link] = []
    factions: list[Link] = []


@entity("subculture")
class Subculture(Strict):
    key: str
    name: str | None
    culture: Link | None
    factions: list[Link] = []


class DifficultyEffect(Strict):
    application: EffectApplication
    campaign: str | None


@entity("difficulty_level")
class DifficultyLevel(Strict):
    key: str
    level: int
    ai: list[DifficultyEffect]
    human: list[DifficultyEffect]


class CampaignVariableOverride(Strict):
    campaign: str
    difficulty: str | None
    campaign_type: str | None
    value: float


@entity("campaign_variable")
class CampaignVariable(Strict):
    key: str
    value: float
    overrides: list[CampaignVariableOverride]
```

- [ ] **Step 4: Implement `twwiki/model/factions.py`**

```python
"""Factions, cultures, subcultures, difficulty handicaps and campaign variables."""

from __future__ import annotations

from collections import defaultdict

from .context import Context, by_key, grouped, opt
from .effects import effect_application


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {
        "faction": {}, "culture": {}, "subculture": {}, "difficulty_level": {}, "campaign_variable": {}}
    if ctx.table_exists("factions"):
        for r in ctx.rows("SELECT key FROM factions"):
            out["faction"][r["key"]] = ctx.catalog_name("faction", f"factions_screen_name_{r['key']}")
    if ctx.table_exists("cultures"):
        for r in ctx.rows("SELECT key FROM cultures"):
            out["culture"][r["key"]] = ctx.catalog_name("culture", f"cultures_name_{r['key']}")
    if ctx.table_exists("cultures_subcultures"):
        for r in ctx.rows("SELECT subculture FROM cultures_subcultures"):
            out["subculture"][r["subculture"]] = ctx.catalog_name(
                "subculture", f"cultures_subcultures_name_{r['subculture']}")
    if ctx.table_exists("campaign_difficulty_handicap_effects"):
        for r in ctx.rows("SELECT DISTINCT campaign_difficulty_handicap AS level FROM campaign_difficulty_handicap_effects"):
            out["difficulty_level"][str(r["level"])] = None  # no display name in data; not counted as missing
    if ctx.table_exists("campaign_variables"):
        for r in ctx.rows("SELECT variable_key FROM campaign_variables"):
            out["campaign_variable"][r["variable_key"]] = r["variable_key"]
    return out


def build(ctx: Context) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {
        "faction": [], "culture": [], "subculture": [], "difficulty_level": [], "campaign_variable": []}
    subcultures = by_key(ctx, "cultures_subcultures", "subculture")

    if ctx.require("faction", "factions"):
        for r in ctx.rows("SELECT * FROM factions ORDER BY key"):
            key = r["key"]
            source = ("faction", key)
            sub = subcultures.get(r["subculture"])
            out["faction"].append({
                "key": key,
                "name": ctx.links.name("faction", key),
                "adjective": ctx.loc.text(f"factions_screen_adjective_{key}"),
                "subculture": ctx.links.link("subculture", opt(r["subculture"]), source=source, relation="subculture"),
                "culture": ctx.links.link("culture", sub["culture"] if sub else None, source=source, relation="culture"),
                "category": opt(r["category"]),
                "is_rebel": r["is_rebel"],
                "is_quest_faction": r["is_quest_faction"],
                "flags_path": r["flags_path"],
                "primary_colour": opt(r["primary_colour_hex"]),
                "units": [],
                "characters": [],
            })

    if ctx.require("culture", "cultures"):
        for r in ctx.rows("SELECT key FROM cultures ORDER BY key"):
            out["culture"].append({"key": r["key"], "name": ctx.links.name("culture", r["key"]),
                                   "subcultures": [], "factions": []})

    if ctx.require("subculture", "cultures_subcultures"):
        for key, r in sorted(subcultures.items()):
            out["subculture"].append({
                "key": key,
                "name": ctx.links.name("subculture", key),
                "culture": ctx.links.link("culture", opt(r["culture"]), source=("subculture", key), relation="culture"),
                "factions": [],
            })

    if ctx.require("difficulty_level", "campaign_difficulty_handicap_effects"):
        levels: dict[int, dict[str, list[dict]]] = defaultdict(lambda: {"ai": [], "human": []})
        for r in ctx.rows("SELECT * FROM campaign_difficulty_handicap_effects "
                          "ORDER BY campaign_difficulty_handicap, human, effect, optional_campaign_key"):
            level = r["campaign_difficulty_handicap"]
            levels[level]["human" if r["human"] else "ai"].append({
                "application": effect_application(ctx, r["effect"], scope=r["effect_scope"], value=r["effect_value"],
                                                  source=("difficulty_level", str(level))),
                "campaign": opt(r["optional_campaign_key"]),
            })
        for level in sorted(levels):
            out["difficulty_level"].append({"key": str(level), "level": level, **levels[level]})

    if ctx.require("campaign_variable", "campaign_variables"):
        overrides = grouped(ctx, "campaigns_campaign_variables_junctions", "variable_key", "campaign_name, difficulty")
        for r in ctx.rows("SELECT * FROM campaign_variables ORDER BY variable_key"):
            key = r["variable_key"]
            out["campaign_variable"].append({
                "key": key,
                "value": r["value"],
                "overrides": [{"campaign": o["campaign_name"], "difficulty": opt(o["difficulty"]),
                               "campaign_type": opt(o["campaign_type"]), "value": o["value"]}
                              for o in overrides.get(key, [])],
            })
    return out
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/model/test_factions.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add twwiki/model/factions.py twwiki/model/schemas.py tests/model/test_factions.py
git commit -m "feat(model): build factions, cultures, difficulty levels and campaign variables"
```

### Task 13: Build orchestration, output and CLI

**Files:**
- Create: `twwiki/model/build.py`, `twwiki/model/__main__.py`
- Modify: `config.yaml` (add `paths.model_dir`)
- Test: `tests/model/test_build.py`

**Interfaces:**
- Consumes: every module's `catalog(ctx)` and `build(ctx)` (Tasks 5–12); `Context` (Task 3); `schemas.ENTITY_MODELS`.
- Produces:
  - `build.MODULES`: `[effects, abilities, units, characters, technologies, buildings, items, factions]`.
  - `build.REVERSE`: list of `(target_type, field, relation, source_type)`.
  - `build.ModelBuildError(Exception)`.
  - `build.build_all(ctx, modules=MODULES) -> dict[str, list[dict]]`: registers catalogs, builds, fills reverse links, validates and returns JSON-ready dicts. Raises `ModelBuildError("<type> <key>: <validation error>")` on the first invalid entity.
  - `build.write_output(ctx, entities, out_root: Path, build_id: str) -> Path`.
  - `build.run(db_path: Path, out_root: Path) -> Path`: full build; raises `ModelBuildError` if any of the 17 entity types is absent.
  - CLI: `uv run python -m twwiki.model [--config config.yaml]`.

- [ ] **Step 1: Write the failing tests**

`tests/model/test_build.py`:
```python
import json
from types import SimpleNamespace

import pytest

from twwiki.model import build
from tests.model.fixtures import make_context


def fake_faction(ctx, **overrides):
    faction = {"key": "reikland", "name": "Reikland", "adjective": None, "subculture": None,
               "culture": ctx.links.link("culture", "empire", source=("faction", "reikland"), relation="culture"),
               "category": None, "is_rebel": False, "is_quest_faction": False, "flags_path": "flags/reikland",
               "primary_colour": None, "units": [], "characters": []}
    faction.update(overrides)
    return faction


def fake_module(**faction_overrides):
    return SimpleNamespace(
        catalog=lambda ctx: {"culture": {"empire": "The Empire"}, "faction": {"reikland": "Reikland"}},
        build=lambda ctx: {
            "culture": [{"key": "empire", "name": "The Empire", "subcultures": [], "factions": []}],
            "faction": [fake_faction(ctx, **faction_overrides)],
        },
    )


def test_build_all_fills_reverse_links_and_validates():
    ctx = make_context({"dummy": [{"a": 1}]})
    entities = build.build_all(ctx, modules=[fake_module()])
    assert entities["culture"][0]["factions"] == [
        {"type": "faction", "key": "reikland", "name": "Reikland", "missing": False}]
    assert entities["faction"][0]["culture"]["name"] == "The Empire"


def test_build_all_reports_invalid_entity():
    ctx = make_context({"dummy": [{"a": 1}]})
    with pytest.raises(build.ModelBuildError, match="faction reikland"):
        build.build_all(ctx, modules=[fake_module(is_rebel="not a bool")])


def test_write_output_layout_and_manifest(tmp_path):
    ctx = make_context({"dummy": [{"a": 1}]}, loc={"s": "{{tr:nowhere}}"})
    ctx.loc.text("s")
    ctx.partial["unit"] = ["land_units"]
    entities = build.build_all(ctx, modules=[fake_module()])
    (tmp_path / "abc123.partial").mkdir()
    (tmp_path / "abc123.partial" / "stale.txt").write_text("old")

    out = build.write_output(ctx, entities, tmp_path, "abc123")

    assert out == tmp_path / "abc123" and not (tmp_path / "abc123.partial").exists()
    lines = (out / "entities" / "faction.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0])["key"] == "reikland"
    assert json.loads((out / "index" / "culture.json").read_text(encoding="utf-8")) == [
        {"key": "empire", "name": "The Empire"}]
    assert (out / "schema" / "unit.schema.json").exists()
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["build_id"] == "abc123" and manifest["model_version"] == build.MODEL_VERSION
    assert manifest["counts"] == {"culture": 1, "faction": 1}
    assert manifest["unresolved_text_targets"] == 1
    assert manifest["partial"] == {"unit": ["land_units"]}
    assert not (out / "stale.txt").exists()


def test_write_output_replaces_previous_model(tmp_path):
    ctx = make_context({"dummy": [{"a": 1}]})
    entities = build.build_all(ctx, modules=[fake_module()])
    (tmp_path / "abc123").mkdir()
    (tmp_path / "abc123" / "old.json").write_text("{}")
    out = build.write_output(ctx, entities, tmp_path, "abc123")
    assert not (out / "old.json").exists() and (out / "manifest.json").exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/model/test_build.py -v`
Expected: FAIL with `ImportError: cannot import name 'build' from 'twwiki.model'`

- [ ] **Step 3: Implement `twwiki/model/build.py`**

```python
"""Run every model module, link, validate and write model/<build_id>/."""

from __future__ import annotations

import json
import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from . import abilities, buildings, characters, effects, factions, items, technologies, units
from .context import Context
from .schemas import ENTITY_MODELS

log = logging.getLogger(__name__)

MODEL_VERSION = 1
MODULES = [effects, abilities, units, characters, technologies, buildings, items, factions]

# (target type, field, relation, source type or None for any)
REVERSE = [
    ("effect", "sources", "effect", None),
    ("ability", "units", "abilities", "unit"),
    ("ability", "characters", "abilities", "character"),
    ("ability", "modified_by_effects", "bonus_target", "effect"),
    ("character", "items", "agent_subtypes", "item"),
    ("skill", "characters", "skill_tree", "character"),
    ("faction", "units", "custom_battle_factions", "unit"),
    ("faction", "characters", "factions", "character"),
    ("culture", "subcultures", "culture", "subculture"),
    ("culture", "factions", "culture", "faction"),
    ("subculture", "factions", "subculture", "faction"),
]

# Extra fields copied into index/<type>.json next to key and name.
INDEX_FIELDS = {
    "unit": ["caste", "category", "unit_class", "tier", "is_naval"],
    "character": ["agent_types", "is_caster"],
    "skill": ["unlocked_at_rank"],
    "ability": ["type", "source_type"],
    "effect": ["category"],
    "effect_bundle": ["target"],
    "building_level": ["level", "cultures"],
    "building_chain": ["category"],
    "technology": ["is_hidden"],
    "item": ["category", "legendary"],
    "trait": ["hidden"],
    "difficulty_level": ["level"],
    "campaign_variable": ["value"],
}


class ModelBuildError(Exception):
    pass


def build_all(ctx: Context, modules=MODULES) -> dict[str, list[dict]]:
    for module in modules:
        for entity_type, names in module.catalog(ctx).items():
            ctx.links.register(entity_type, names)

    entities: dict[str, list[dict]] = {}
    for module in modules:
        started = time.perf_counter()
        built = module.build(ctx)
        entities.update(built)
        log.info("%-14s %s in %.1fs", module.__name__.rsplit(".", 1)[-1] if hasattr(module, "__name__") else "module",
                 ", ".join(f"{t}={len(rows)}" for t, rows in built.items()), time.perf_counter() - started)

    for target, field, relation, source_type in REVERSE:
        for entity in entities.get(target, []):
            entity[field] = ctx.links.referrers(target, entity["key"], relation, source_type)

    validated: dict[str, list[dict]] = {}
    for entity_type, rows in entities.items():
        model = ENTITY_MODELS[entity_type]
        out = []
        for entity in rows:
            try:
                out.append(model.model_validate(entity).model_dump(mode="json"))
            except ValidationError as e:
                raise ModelBuildError(f"{entity_type} {entity.get('key')}: {e}") from e
        validated[entity_type] = out
    return validated


def write_output(ctx: Context, entities: dict[str, list[dict]], out_root: Path, build_id: str) -> Path:
    final = out_root / build_id
    staging = out_root / f"{build_id}.partial"
    if staging.exists():
        shutil.rmtree(staging)
    for sub in ("entities", "index", "schema"):
        (staging / sub).mkdir(parents=True)

    for entity_type, rows in sorted(entities.items()):
        with (staging / "entities" / f"{entity_type}.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        index = [{"key": r["key"], "name": ctx.links.name(entity_type, r["key"]),
                  **{f: r[f] for f in INDEX_FIELDS.get(entity_type, [])}} for r in rows]
        (staging / "index" / f"{entity_type}.json").write_text(
            json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")

    for entity_type, model in sorted(ENTITY_MODELS.items()):
        (staging / "schema" / f"{entity_type}.schema.json").write_text(
            json.dumps(model.model_json_schema(), indent=2), encoding="utf-8")

    manifest = {
        "build_id": build_id,
        "model_version": MODEL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {t: len(rows) for t, rows in sorted(entities.items())},
        "missing_names": dict(sorted(ctx.missing_names.items())),
        "missing_links": dict(sorted(ctx.links.missing.items())),
        "unresolved_text_targets": len(ctx.loc.unresolved_targets),
        "partial": ctx.partial,
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if final.exists():
        shutil.rmtree(final)  # a model is always rebuilt from the database, never patched
    staging.rename(final)
    return final


def run(db_path: Path, out_root: Path) -> Path:
    started = time.perf_counter()
    ctx = Context.open(db_path)
    try:
        build_id = ctx.con.execute("SELECT build_id FROM _build").fetchone()[0]
        entities = build_all(ctx)
        absent = sorted(set(ENTITY_MODELS) - set(entities))
        if absent:
            raise ModelBuildError(f"entity types not built: {absent}")
        out = write_output(ctx, entities, out_root, build_id)
    finally:
        ctx.con.close()
    log.info("model %s written to %s in %.0fs; missing names %d, missing links %d, partial types %s",
             build_id, out, time.perf_counter() - started, sum(ctx.missing_names.values()),
             sum(ctx.links.missing.values()), sorted(ctx.partial) or "none")
    return out
```

- [ ] **Step 4: Implement `twwiki/model/__main__.py`**

```python
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ..config import load_config
from .build import run


def main() -> None:
    ap = argparse.ArgumentParser(description="Build model/<build_id>/ from twwiki.duckdb")
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cfg = load_config(args.config)
    run(Path(cfg.paths.db_path), Path(getattr(cfg.paths, "model_dir", "./model")))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Add the model directory to `config.yaml`**

In the `paths:` block, after `site_dir: "./site"`, add:
```yaml
  model_dir: "./model"
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/model/test_build.py -v`
Expected: 4 passed

- [ ] **Step 7: Run the whole unit suite**

Run: `uv run pytest tests/model -v --ignore=tests/model/test_real_build.py`
Expected: all tests pass (54 tests across Tasks 1–13)

- [ ] **Step 8: Commit**

```bash
git add twwiki/model/build.py twwiki/model/__main__.py config.yaml tests/model/test_build.py
git commit -m "feat(model): orchestrate model build with reverse links, validation and output"
```

### Task 14: Real-database checks, missing-link baseline and README

**Files:**
- Create: `tests/model/test_real_build.py`, `tests/model/missing_links_baseline.json`
- Modify: `README.md`

**Interfaces:**
- Consumes: `build.build_all`, `build.run`, `Context.open` (Tasks 3, 13).
- Produces: nothing new; this task proves the model against build `fb20553df5af`.

- [ ] **Step 1: Run the full model build**

Run: `uv run python -m twwiki.model`
Expected: log ends with `model fb20553df5af written to model\fb20553df5af in <N>s`, with N under 120. If a `ModelBuildError` appears, fix the named module before continuing (it is a model bug, not a data gap).

- [ ] **Step 2: Record the missing-link baseline**

Run:
```bash
uv run python -c "import json; m = json.load(open('model/fb20553df5af/manifest.json', encoding='utf-8')); json.dump(m['missing_links'], open('tests/model/missing_links_baseline.json', 'w', encoding='utf-8'), indent=2, sort_keys=True); print(sum(m['missing_links'].values()), 'missing links recorded')"
```
Expected: prints a count and creates `tests/model/missing_links_baseline.json`. Inspect it; every key has the form `"<source>.<relation>-><target>"`.

- [ ] **Step 3: Write the real-database tests**

`tests/model/test_real_build.py`:
```python
"""Known entities and whole-build checks against the real twwiki.duckdb.

Expected values were verified against build fb20553df5af. After a game patch
some may change legitimately; update them deliberately, never to make a
failing build pass unexamined.
"""

import json
from pathlib import Path

import pytest

from twwiki.model.build import build_all
from twwiki.model.context import Context
from twwiki.model.schemas import ENTITY_MODELS

DB = Path("twwiki.duckdb")
BASELINE = Path(__file__).parent / "missing_links_baseline.json"

pytestmark = pytest.mark.skipif(not DB.exists(), reason="twwiki.duckdb not found; run extract and load first")

EXPECTED_COUNTS = {
    "unit": 2609, "character": 613, "skill": 5944, "ability": 2899, "effect": 15064,
    "effect_bundle": 5855, "building_level": 5259, "building_chain": 1943, "technology": 1869,
    "technology_tree": 33, "item": 2671, "trait": 744, "faction": 717, "culture": 27,
    "subculture": 32, "difficulty_level": 7, "campaign_variable": 1052,
}


@pytest.fixture(scope="module")
def model():
    ctx = Context.open(DB)
    entities = build_all(ctx)
    yield ctx, {t: {e["key"]: e for e in rows} for t, rows in entities.items()}
    ctx.con.close()


def test_every_entity_type_is_built_with_expected_counts(model):
    _, by_type = model
    assert set(by_type) == set(ENTITY_MODELS)
    assert {t: len(rows) for t, rows in by_type.items()} == EXPECTED_COUNTS


def test_greatswords(model):
    gs = model[1]["unit"]["wh_main_emp_inf_greatswords"]
    stats = gs["base_stats"]
    assert gs["name"] == "Greatswords"
    assert (stats["num_men"], stats["hit_points_per_entity"], stats["bonus_hit_points"]) == (120, 8, 68)
    assert (stats["melee_attack"], stats["melee_defence"], stats["armour"]) == (32, 30, 95)
    assert gs["melee_weapon"]["key"] == "wh_main_emp_greatsword"
    assert (gs["melee_weapon"]["damage"], gs["melee_weapon"]["ap_damage"]) == (10, 25)


def test_karl_franz(model):
    by_type = model[1]
    kf = by_type["character"]["wh_main_emp_karl_franz"]
    assert kf["name"] == "Emperor Karl Franz" and kf["title"] == "Legendary Lord"
    assert [t["key"] for t in kf["skill_trees"]] == ["wh_main_skill_node_set_emp_karl_franz"]
    nodes = kf["skill_trees"][0]["nodes"]
    assert len(nodes) == 51
    leader = next(by_type["skill"][n["skill"]["key"]] for n in nodes if n["skill"]["name"] == "Leader of Men")
    aura = [e for e in leader["levels"][0]["effects"] if e["value"] == 50.0]
    assert aura and aura[0]["effect"]["name"].startswith("Leadership aura size")


def test_hold_the_line(model):
    hold = model[1]["ability"]["wh_main_lord_passive_hold_the_line"]
    assert hold["activation"]["passive"] is True and hold["activation"]["effect_range"] == 35.0
    stats = {(s["stat"], s["value"], s["how"]) for p in hold["phases"] for s in p["stat_effects"]}
    assert {("stat_melee_defence", 5.0, "add"), ("stat_morale", 4.0, "add")} <= stats
    assert len(hold["units"]) == 18


def test_training_field(model):
    tf = model[1]["building_level"]["wh_main_emp_barracks_1"]
    assert tf["name"] == "Training Field"
    assert (tf["chain"]["key"], tf["level"], tf["create_cost"]) == ("wh_main_EMPIRE_barracks", 0, 750)
    assert tf["cultures"] == ["wh_main_emp_empire"]


def test_research_costs(model):
    by_type = model[1]
    tech = by_type["technology"]["wh2_dlc13_tech_emp_infantry_1_c"]
    assert tech["name"] == "Improved Heavy Weapons"
    assert {(p["tree"]["key"], p["research_points_required"]) for p in tech["placements"]} == {
        ("emp_civ_reworkd", 900), ("emp_wulfhart", 700)}
    costs = [p["resource_cost"] for t in by_type["technology"].values() for p in t["placements"]
             if p["resource_cost"] and p["resource_cost"]["key"] == "wh2_dlc09_tmb_tech_agent_unlock"]
    assert costs and costs[0]["treasury_cost"] == 0
    assert {"pooled_resource_factor": "canopic_jars_technology", "amount": -250, "context": "absolute"} in costs[0]["pooled_resources"]
    assert by_type["campaign_variable"]["base_research_points_per_turn"]["value"] == 100.0


def test_text_token_resolution(model):
    effect = model[1]["effect"]["wh_main_effect_technology_research_points"]
    assert effect["description"] == "Research rate: %+n"


def test_unit_set_membership(model):
    members = [u for u in model[1]["unit"].values()
               if any(s["key"] == "dlc14_all_units_excluding_characters" for s in u["unit_sets"])]
    assert len(members) == 1305


def test_factions_and_difficulty(model):
    by_type = model[1]
    reikland = by_type["faction"]["wh_main_emp_empire"]
    assert reikland["name"] == "Reikland" and reikland["culture"]["key"] == "wh_main_emp_empire"
    assert sorted(d["level"] for d in by_type["difficulty_level"].values()) == [-3, -2, -1, 0, 1, 2, 3]
    level2 = by_type["difficulty_level"]["2"]
    assert (len(level2["ai"]), len(level2["human"])) == (49, 0)


def test_missing_links_do_not_exceed_baseline(model):
    ctx, _ = model
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    worse = {k: (v, baseline.get(k, 0)) for k, v in ctx.links.missing.items() if v > baseline.get(k, 0)}
    assert worse == {}, f"missing links above baseline (now, baseline): {worse}"
```

- [ ] **Step 4: Run the real-database tests**

Run: `uv run pytest tests/model/test_real_build.py -v`
Expected: 10 passed (skipped with the reason message if `twwiki.duckdb` is absent)

- [ ] **Step 5: Document the stage in `README.md`**

Change the pipeline diagram to:
````markdown
```
rpfm_server (WS) → raw/<build_id>/files/**.jsonl → twwiki.duckdb → model/<build_id>/ → web app
     extract.py            (immutable)                load.py         model (Python)
```
````

In "Run order", after the `load` line, add:
```bash
uv run python -m twwiki.model   # curated entities for the web app
```

Add this section before "Mapping the server surface":
````markdown
## Game data model

`python -m twwiki.model` turns `twwiki.duckdb` into curated entities in
`model/<build_id>/` (design: `docs/superpowers/specs/2026-09-15-game-data-model-design.md`):

- `entities/<type>.jsonl`: one entity per line for 17 types (units, characters
  with skill trees, skills, abilities, effects and bundles, buildings,
  technologies and trees, items, traits, factions, cultures, subcultures,
  difficulty levels, campaign variables). References are links
  `{type, key, name, missing}`; effects are applied through one
  `EffectApplication` shape everywhere.
- `index/<type>.json`: key, name and filter fields for browsing.
- `schema/<type>.schema.json`: JSON Schemas exported from the Pydantic models
  in `twwiki/model/schemas.py`; the web app generates TypeScript types from them.
- `manifest.json`: counts, missing names, missing links, unresolved text tokens
  and partial entity types.

The model never calculates final stats or research turns; that is the stat
engine's job. Gaps in game data are counted in the manifest; an entity that
fails schema validation stops the build.

Tests: `uv run pytest`. Tests against the real database skip when
`twwiki.duckdb` is absent. After a game patch, rebuild, review any failing
expected values, and regenerate `tests/model/missing_links_baseline.json` only
after checking why links went missing.
````

- [ ] **Step 6: Run the full test suite**

Run: `uv run pytest -v`
Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add tests/model/test_real_build.py tests/model/missing_links_baseline.json README.md
git commit -m "test(model): verify known entities and counts against the real database"
```

