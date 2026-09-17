# Model Area A (Foundations and Text) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship model version 3: a campaign entity and campaign links, text cleanup, labels in place of raw keys, effect presentation fields, and reference documents. Update the web app in the same branch to show them.

**Architecture:** The Python builders in `twwiki/model/` gain one new module each for campaigns (`campaigns.py`) and reference documents (`reference.py`). Loc cleanup is added to `text.py`, and each existing builder is edited. Serialisation-time float rounding and new manifest sections live in `build.py`. The Astro app in `web/` reads the new fields and the `reference/` folder. It gains pure helper modules, each unit-tested: `gameValue.ts`, `subtitle.ts`, `campaignFilter.ts`, `coloursCss.ts` and `uiLabels.ts`. It also gains a campaign page type.

**Tech Stack:** Python 3 with DuckDB, Pydantic 2 and pytest (run through `uv`). Web: Astro 7, React 19 islands, TypeScript, Vitest 5 and Playwright.

**Spec:** `docs/superpowers/specs/2026-09-16-model-area-a-foundations-design.md` (roadmap: `docs/superpowers/specs/2026-09-16-model-v3-roadmap-design.md`).

## Global Constraints

- Work on branch `feature/model-area-a`, created from `docs/model-roadmap`. Do not push, open a pull request, merge or publish without the user's approval.
- `MODEL_VERSION` is `3` in both `twwiki/model/build.py` and `web/src/data/validate.ts`.
- Campaign references are `Link` objects of type `campaign`, never raw strings. In a `campaigns: list[Link]` tag, an empty list means every campaign.
- Text cleanup happens in the model. Game markup (`[[…]]`) passes through to the web renderer.
- The model keeps game values as they are, including `-1`. Display rules live only in `web/src/lib/gameValue.ts`.
- Floats are rounded to 6 significant digits when serialised (`float(f"{value:.6g}")`), in `write_output` only.
- Reference documents are written to `model/<build_id>/reference/`: `campaigns.json`, `colours.json` and `ui_labels.json`.
- The model build fails only on schema validation and image-copy failures. Everything else is counted in the manifest.
- Never hand-edit `model/` or `raw/`. Rebuild with `uv run python -m twwiki.model`. Regenerate `web/test/fixtures/model` only with `npm run fixtures`.
- Unnamed records:
  - Their pages are titled `Unnamed <singular type label>`.
  - They are left out of browse lists, the search index and the region culture picker.
- Campaign filter: the default is `wh3_main_combi` (Immortal Empires), and the empty value is labelled `All`.
- Hidden effects:
  - Disclosure summary: `Hidden effects (n)`.
  - Note: `The game does not display these effects.`
- Commands:
  - Python: `uv run pytest tests -q`, from the repository root.
  - Web unit tests: `npm test`, from `web/`.
  - End-to-end: `npm run build && npm run test:e2e`, from `web/`.
- Every commit message ends with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

## Plan rulings (gaps the spec leaves open)

1. **Placeholder prefix.** Loc keys don't mark where the record starts, so `placeholders_by_prefix` groups keys by their first three `_`-separated words (`building_chains_encyclopedia`).
2. **`round_float` leaves whole-number floats unchanged.** Six significant digits would otherwise turn `123456789.0` into `123457000.0`.
3. **Token and placeholder counts are distinct keys, targets or tokens.** Builders look the same text up more than once.
4. **`campaign_to_agent_subtypes` lists every campaign a subtype appears in.** Karl Franz has rows for both `wh3_main_combi` and `wh3_main_chaos`, and no subtype is listed for `wh3_main_prologue`. The spec's rule stands: no rows means no data, and the web app treats that as every campaign. The model code records this.
5. **Agent type fallback name.** It is the name most cultures use, with ties going to the earliest culture key; the spec said the first culture's name.
   - This gives "Lord" for `general` rather than one culture's own title.
   - Items use the same generic label. The spec doesn't cover items, but without it they would keep showing raw agent keys.
6. **Difficulty levels have no pages,** so they get no browse filter. Their campaign links stay in the model.
7. **`UI_LABEL_KEYS`** maps a short name to a loc key. Trailing `:` and whitespace are trimmed. Labels with no text are counted as `ui_labels_without_text`.
8. **Unknown `col:` names** render as `<span class="gt-col" data-unknown-colour="…">`. `scripts/build-report.ts` counts that attribute.
9. **One effect-list renderer.** `effectsHtml` in `web/src/lib/detailHtml.ts` renders effect lists for both `EffectList.astro` and the tree panels. The polarity class goes on the effect text span.
10. **Missing building availability links.** An unresolved key becomes a missing link whose type is the variant column it came from (`culture`, `subculture` or `faction`).
11. **`SkillTree.campaign` also becomes a link,** alongside the node-level campaign.
12. **Browse columns.** Region and province lose their "Campaign" column (the campaign filter replaces it), and building levels lose "Cultures". Character "Agent types" shows names.
13. **Search subtitles.** The subtitle is a stored field of each search document, not a searchable field.
14. **`subtitleFor` also takes `site`:** `subtitleFor(site, type, entity)`. A character's culture comes from its first faction's entity. Markup is stripped from subtitle text.
15. **Tree node campaigns.** Skill and technology tree nodes have no pages, so their tree detail panels show "Only in <campaign links>" instead of a badge.
16. **Unnamed titles** use the lower-case singular, e.g. "Unnamed building chain".

## File structure

**Python, created:**
- `twwiki/model/campaigns.py`: campaign catalog and entities.
- `twwiki/model/reference.py`: reference documents, `dark_hex` and `UI_LABEL_KEYS`.
- `tests/model/test_campaigns.py`
- `tests/model/test_reference.py`

**Python, modified:**
- `twwiki/model/text.py`: placeholder rules, token dropping, `split_title_body`, `round_float` and `text_report`.
- `twwiki/model/context.py`: `tally` and `effect_display`.
- `twwiki/model/build.py`: version, module list, reverse links, rounding, manifest and reference output.
- `twwiki/model/schemas.py`: new and changed fields, plus the reference models.
- Builders:
  - `effects.py`
  - `factions.py`
  - `regions.py`
  - `characters.py`
  - `buildings.py`
  - `technologies.py`
  - `items.py`
  - `units.py`
- Tests: the matching files in `tests/model/`, plus `tests/publish/helpers.py`.
- Baselines: `tests/model/missing_links_baseline.json` and `tests/model/missing_images_baseline.json`.

**Web, created:**
- Library modules in `web/src/lib/`:
  - `gameValue.ts`
  - `subtitle.ts`
  - `campaignFilter.ts`
  - `coloursCss.ts`
- `web/src/data/uiLabels.ts`
- Components:
  - `web/src/components/CampaignBadge.astro`
  - `web/src/components/pages/CampaignPage.astro`
- Unit tests in `web/test/unit/`:
  - `gameValue.test.ts`
  - `subtitle.test.ts`
  - `campaignFilter.test.ts`
  - `coloursCss.test.ts`
  - `detailHtml.test.ts`

**Web, modified:**
- Data layer, in `web/src/data/`:
  - `validate.ts`
  - `load.ts`
  - `pageTypes.ts`
  - `site.ts`
  - `browse.ts`
  - `searchIndex.ts`
- Library, in `web/src/lib/`:
  - `gameText.ts`
  - `effectText.ts`
  - `detailHtml.ts`
  - `search.ts`
  - `regionCultures.ts`
- Components, in `web/src/components/`:
  - `EffectList.astro`
  - `StatTable.astro`
  - `LinkList.astro`
  - `EntityHeader.astro`
  - `GameText.astro`
  - `pages/registry.ts`
- Entity pages, in `web/src/components/pages/`:
  - `UnitPage.astro`
  - `ItemPage.astro`
  - `BuildingLevelPage.astro`
  - `BuildingChainPage.astro`
  - `CharacterPage.astro`
  - `FactionPage.astro`
  - `AbilityPage.astro`
  - `RegionPage.astro`
  - `ProvincePage.astro`
  - `TechnologyTreePage.astro`
- Routes:
  - `web/src/pages/[segment]/index.astro`
  - `web/src/pages/[segment]/[slug].astro`
- Islands, in `web/src/islands/`:
  - `BrowseFilter.tsx`
  - `SearchBox.tsx`
- `web/src/styles/theme.css`
- Scripts, in `web/scripts/`:
  - `prebuild.ts`
  - `make-fixtures.ts`
  - `build-report.ts`
- Tests:
  - `web/test/fixtures/model/` (regenerated)
  - the unit tests in `web/test/unit/`
  - `web/test/e2e/wiki.spec.ts`

## Task order

Tasks 1–9 build the model and end with a local rebuild of the real model. Task 10 moves the web app to model version 3 and regenerates its types and fixtures from that model. Tasks 11–18 then build the web features on top.

---

### Task 1: Loc text rules

**Files:**
- Modify: `twwiki/model/text.py` (whole file)
- Test: `tests/model/test_text.py` (whole file)

**Interfaces:**
- Produces:
  - `LocResolver.raw(key) -> str | None` and `LocResolver.text(key) -> str | None`. Both treat placeholder text as missing.
  - `LocResolver.unresolved_targets: set[str]`
  - `LocResolver.placeholder_keys: set[str]`
  - `LocResolver.dropped_tt_targets: set[str]`
  - `LocResolver.dropped_cco_tokens: set[str]`
  - `LocResolver.text_report() -> dict`, with keys `placeholders_by_prefix`, `dropped_tt_tokens`, `dropped_cco_tokens` and `dropped_tr_tokens`.
  - Module functions:
    - `is_placeholder(text: str) -> bool`
    - `loc_prefix(key: str) -> str`
    - `split_title_body(text: str | None) -> tuple[str | None, str | None]`
    - `round_float(value: float) -> float`

- [ ] **Step 1: Write the failing tests.** Replace `tests/model/test_text.py` with:

```python
import pytest

from twwiki.model.text import LocResolver, loc_prefix, round_float, split_title_body


def test_raw_returns_none_for_missing_or_empty():
    loc = LocResolver({"a": "", "b": "Bee"})
    assert loc.raw("a") is None
    assert loc.raw("missing") is None
    assert loc.raw("b") == "Bee"


def test_placeholder_text_counts_as_missing_and_is_recorded_once_per_key():
    loc = LocResolver({
        "building_chains_encyclopedia_name_a": "placeholder",
        "building_chains_encyclopedia_name_b": "  PlaceHolder ",
        "cultures_name_*": "%PLACEHOLDER%",
        "cultures_name_x": "Real",
    })
    assert loc.text("building_chains_encyclopedia_name_a") is None
    assert loc.text("building_chains_encyclopedia_name_a") is None
    assert loc.raw("building_chains_encyclopedia_name_b") is None
    assert loc.text("cultures_name_*") is None
    assert loc.text("cultures_name_x") == "Real"
    assert loc.text_report()["placeholders_by_prefix"] == {"building_chains_encyclopedia": 2, "cultures_name_*": 1}


def test_loc_prefix_is_first_three_words():
    assert loc_prefix("building_chains_encyclopedia_name_wh_main_x") == "building_chains_encyclopedia"
    assert loc_prefix("p") == "p"


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


def test_unresolved_tr_token_is_dropped_and_recorded():
    loc = LocResolver({"s": "Pay {{tr:nothing_here}} now"})
    assert loc.text("s") == "Pay  now"
    assert loc.unresolved_targets == {"nothing_here"}
    assert loc.text_report()["dropped_tr_tokens"] == 1


def test_self_referencing_token_is_dropped_after_max_depth():
    loc = LocResolver({"s": "a{{tr:loop}}b", "loop": "{{tr:loop}}"})
    assert loc.text("s") == "ab"
    assert loc.unresolved_targets == {"loop"}


def test_tooltip_and_cco_tokens_are_dropped_and_markup_is_kept():
    loc = LocResolver({"s": "[[tooltip:{{tt:x}}]]word[[/tooltip]] {{CcoCampaignFaction:Name}}! [[col:red]]%n[[/col]]"})
    assert loc.text("s") == "[[tooltip:]]word[[/tooltip]] ! [[col:red]]%n[[/col]]"
    assert loc.text_report() == {"placeholders_by_prefix": {}, "dropped_tt_tokens": 1,
                                 "dropped_cco_tokens": 1, "dropped_tr_tokens": 0}


@pytest.mark.parametrize("text, expected", [
    ("Just a body", (None, "Just a body")),
    ("Title||Body", ("Title", "Body")),
    (" Title || Body||more ", ("Title", "Body||more")),
    ("||Body", (None, "Body")),
    ("Title||", ("Title", None)),
    ("[[col:yellow]]Rampage[[/col]]||[[b]]Charges[[/b]]", ("[[col:yellow]]Rampage[[/col]]", "[[b]]Charges[[/b]]")),
    (None, (None, None)),
])
def test_split_title_body(text, expected):
    assert split_title_body(text) == expected


@pytest.mark.parametrize("value, expected", [
    (0.90000004, 0.9), (1.0000001, 1.0), (-0.30000001, -0.3), (3.0, 3.0), (123456789.0, 123456789.0), (1e-7, 1e-7),
])
def test_round_float(value, expected):
    assert round_float(value) == expected
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `uv run pytest tests/model/test_text.py -q`
Expected: collection error `ImportError: cannot import name 'loc_prefix'`.

- [ ] **Step 3: Implement.** Replace `twwiki/model/text.py` with:

```python
"""Loc lookups with {{tr:...}} text-replacement substitution and text cleanup.

Placeholder text counts as missing. {{tt:...}} tokens (tooltip targets that
don't exist), {{Cco...}} live UI expressions and {{tr:...}} tokens that never
resolve are removed and recorded for the manifest. Game markup ([[col:...]],
[[img:...]]) is left unchanged; the web app renders it.
"""

from __future__ import annotations

import re
from collections import Counter

# Where a {{tr:<target>}} token's text is looked up, in order.
TR_PREFIXES = (
    "",
    "ui_text_replacements_localised_text_",
    "campaign_localised_strings_string_",
    "cultures_subcultures_",
    "random_localisation_strings_string_",
)
TR_TOKEN = re.compile(r"\{\{tr:([^}]+)\}\}")
TT_TOKEN = re.compile(r"\{\{tt:([^}]*)\}\}")
CCO_TOKEN = re.compile(r"\{\{Cco[^:}]*:[^}]*\}\}")
MAX_DEPTH = 5


def is_placeholder(text: str) -> bool:
    return text.strip().lower() == "placeholder" or "%PLACEHOLDER%" in text


def loc_prefix(key: str) -> str:
    """A loc key's table-and-field part, for reporting. Keys don't mark where the
    record starts, so this is the first three underscore-separated words."""
    return "_".join(key.split("_")[:3])


def split_title_body(text: str | None) -> tuple[str | None, str | None]:
    """Split game text on its first || into a trimmed title and body; empty parts become None."""
    if text is None:
        return None, None
    if "||" not in text:
        return None, text
    title, body = text.split("||", 1)
    return title.strip() or None, body.strip() or None


def round_float(value: float) -> float:
    """Six significant digits, which hides float32 artefacts such as 0.90000004.
    Whole numbers are returned unchanged so large values keep every digit."""
    if value.is_integer():
        return value
    return float(f"{value:.6g}")


class LocResolver:
    def __init__(self, entries: dict[str, str]):
        self._entries = entries
        self.unresolved_targets: set[str] = set()
        self.placeholder_keys: set[str] = set()
        self.dropped_tt_targets: set[str] = set()
        self.dropped_cco_tokens: set[str] = set()

    @classmethod
    def from_duckdb(cls, con) -> "LocResolver":
        return cls(dict(con.execute("SELECT key, text FROM loc").fetchall()))

    def raw(self, key: str) -> str | None:
        """Loc text without substitution; empty and placeholder text count as missing."""
        text = self._entries.get(key)
        if not text:
            return None
        if is_placeholder(text):
            self.placeholder_keys.add(key)
            return None
        return text

    def text(self, key: str) -> str | None:
        raw = self.raw(key)
        return None if raw is None else self.substitute(raw)

    def substitute(self, text: str) -> str:
        for _ in range(MAX_DEPTH):
            changed = False

            def replace(match: re.Match) -> str:
                nonlocal changed
                for prefix in TR_PREFIXES:
                    value = self._entries.get(prefix + match.group(1))
                    if value is not None:
                        changed = True
                        return value
                return match.group(0)

            text = TR_TOKEN.sub(replace, text)
            if not changed:
                break
        text = TR_TOKEN.sub(self._drop_tr, text)
        text = TT_TOKEN.sub(self._drop_tt, text)
        return CCO_TOKEN.sub(self._drop_cco, text)

    def _drop_tr(self, match: re.Match) -> str:
        self.unresolved_targets.add(match.group(1))
        return ""

    def _drop_tt(self, match: re.Match) -> str:
        self.dropped_tt_targets.add(match.group(1))
        return ""

    def _drop_cco(self, match: re.Match) -> str:
        self.dropped_cco_tokens.add(match.group(0))
        return ""

    def text_report(self) -> dict:
        return {
            "placeholders_by_prefix": dict(sorted(Counter(loc_prefix(k) for k in self.placeholder_keys).items())),
            "dropped_tt_tokens": len(self.dropped_tt_targets),
            "dropped_cco_tokens": len(self.dropped_cco_tokens),
            "dropped_tr_tokens": len(self.unresolved_targets),
        }
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `uv run pytest tests/model/test_text.py -q`
Expected: all pass.

Then run: `uv run pytest tests/model -q --ignore=tests/model/test_real_build.py`
Expected: pass. No other unit test depends on kept tokens.

- [ ] **Step 5: Commit**

```bash
git add twwiki/model/text.py tests/model/test_text.py
git commit -m "feat(model): treat placeholder loc as missing and drop dead text tokens" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Build output foundations (version, rounding, manifest counts)

**Files:**
- Modify: `twwiki/model/context.py` (the `Context` dataclass fields)
- Modify: `twwiki/model/build.py` (`MODEL_VERSION`, new helpers, `write_output`)
- Modify: `tests/publish/helpers.py:12` (default `model_version`)
- Test: `tests/model/test_build.py`

**Interfaces:**
- Consumes: `LocResolver.text_report()` and `round_float` (Task 1).
- Produces:
  - `Context.tally: Counter[str]`, a quality counter that builders increment.
  - `Context.effect_display: dict[str, dict]`, filled in Task 6.
  - `build.MODEL_VERSION = 3`
  - `build.QUALITY_COUNTS: tuple[str, ...]`
  - `build.round_floats(value)`
  - `build.unnamed_by_type(entities) -> dict[str, int]`
  - New manifest keys: `text`, `unnamed_by_type`, and one top-level integer per name in `QUALITY_COUNTS`.

- [ ] **Step 1: Write the failing tests.** Append to `tests/model/test_build.py`:

```python
def test_round_floats_rounds_nested_floats_only():
    data = {"a": 0.90000004, "b": [1.0000001, {"c": 2}], "d": True, "e": "0.90000004", "f": None}
    assert build.round_floats(data) == {"a": 0.9, "b": [1.0, {"c": 2}], "d": True, "e": "0.90000004", "f": None}
    assert type(build.round_floats({"c": 2})["c"]) is int


def test_write_output_rounds_floats_and_reports_text_and_quality_counts(tmp_path):
    ctx = make_context({"dummy": [{"a": 1}]}, loc={"s": "{{tt:x}} text", "p": "placeholder"})
    ctx.loc.text("s")
    ctx.loc.text("p")
    ctx.tally["unmatched_rarity_scores"] = 2
    module = SimpleNamespace(
        catalog=lambda ctx: {"campaign_variable": {"v": "v"}, "culture": {"nameless": None}},
        build=lambda ctx: {
            "campaign_variable": [{"key": "v", "value": 0.90000004, "overrides": []}],
            "culture": [{"key": "nameless", "name": None, "subcultures": [], "factions": []}],
        },
    )
    out = build.write_output(ctx, build.build_all(ctx, modules=[module]), tmp_path, "abc123")

    row = json.loads((out / "entities" / "campaign_variable.jsonl").read_text(encoding="utf-8"))
    assert row["value"] == 0.9
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["model_version"] == 3
    assert manifest["text"] == {"placeholders_by_prefix": {"p": 1}, "dropped_tt_tokens": 1,
                                "dropped_cco_tokens": 0, "dropped_tr_tokens": 0}
    assert manifest["unnamed_by_type"] == {"culture": 1}
    assert manifest["unmatched_rarity_scores"] == 2
    assert all(isinstance(manifest[name], int) for name in build.QUALITY_COUNTS)
```

At line 201 of the same file, change `manifest["model_version"] == 2` to `manifest["model_version"] == build.MODEL_VERSION`.

- [ ] **Step 2: Run the tests to see them fail**

Run: `uv run pytest tests/model/test_build.py -q`
Expected: FAIL with `AttributeError: module 'twwiki.model.build' has no attribute 'round_floats'`.

- [ ] **Step 3: Implement.**

In `twwiki/model/context.py`, add two fields to `Context`, after `manifest_sections`:

```python
    # Quality counters written to the manifest (see build.QUALITY_COUNTS).
    tally: Counter = field(default_factory=Counter)
    # effect key -> priority, polarity and icons, filled by effects.build for effect_application.
    effect_display: dict[str, dict] = field(default_factory=dict)
```

In `twwiki/model/build.py`:
- Change `MODEL_VERSION = 2` to `MODEL_VERSION = 3`.
- Add `from .text import round_float` to the imports.
- Below `INDEX_FIELDS`, add:

```python
# Counters builders add to ctx.tally; each is written to the manifest, 0 when never touched.
QUALITY_COUNTS = (
    "effect_applications_without_scope_text",
    "unmatched_rarity_scores",
    "unresolved_agent_type_names",
    "campaign_exclusive_permissions_excluded",
    "unresolved_building_availability_keys",
    "ui_labels_without_text",
)


def round_floats(value):
    """Round every float in a JSON-like value; ints, bools and strings are unchanged."""
    if isinstance(value, float):
        return round_float(value)
    if isinstance(value, dict):
        return {k: round_floats(v) for k, v in value.items()}
    if isinstance(value, list):
        return [round_floats(v) for v in value]
    return value


def unnamed_by_type(entities: dict[str, list[dict]]) -> dict[str, int]:
    counts = {t: sum(1 for r in rows if "name" in r and r["name"] is None) for t, rows in sorted(entities.items())}
    return {t: n for t, n in counts.items() if n}
```

In `write_output`, write rounded rows and a rounded index:

```python
            for row in rows:
                fh.write(json.dumps(round_floats(row), ensure_ascii=False) + "\n")
        index = [{"key": r["key"], "name": ctx.links.name(entity_type, r["key"]),
                  **{f: r[f] for f in INDEX_FIELDS.get(entity_type, [])}} for r in rows]
        (staging / "index" / f"{entity_type}.json").write_text(
            json.dumps(round_floats(index), ensure_ascii=False, indent=1), encoding="utf-8")
```

Extend the `manifest` dict literal. After `"unresolved_text_targets": len(ctx.loc.unresolved_targets),` add:

```python
        "text": ctx.loc.text_report(),
        "unnamed_by_type": unnamed_by_type(entities),
        **{name: ctx.tally[name] for name in QUALITY_COUNTS},
```

In `tests/publish/helpers.py`:
- Add `from twwiki.model.build import MODEL_VERSION`.
- Change the `make_model` parameter to `model_version: int = MODEL_VERSION`.

- [ ] **Step 4: Run the tests to see them pass**

Run: `uv run pytest tests/model/test_build.py tests/publish -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add twwiki/model/context.py twwiki/model/build.py tests/model/test_build.py tests/publish/helpers.py
git commit -m "feat(model): model version 3 output with float rounding and quality counts" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Campaign entity and faction start positions

**Files:**
- Create: `twwiki/model/campaigns.py`
- Modify: `twwiki/model/schemas.py` (new `Campaign` model; new `Faction` fields)
- Modify: `twwiki/model/factions.py` (`build`, faction rows)
- Modify: `twwiki/model/build.py` (imports, `MODULES`, `REVERSE`, `INDEX_FIELDS`)
- Regenerate: `firestore.indexes.json` (a new `campaign` collection group; `tests/publish/test_indexes.py` compares it with the generator)
- Test: `tests/model/test_campaigns.py`

**Interfaces:**
- Produces:
  - Entity type `campaign` with fields `key`, `name`, `map`, `script_folder`, `factions`, `playable_factions`, `major_factions` and `regions` (the last filled by `REVERSE`).
  - Faction fields `start_campaigns`, `playable_in` and `major_in`, each `list[Link]`.
  - Link type `campaign` registered by `campaigns.catalog`.

- [ ] **Step 1: Write the failing tests.** Create `tests/model/test_campaigns.py`:

```python
from twwiki.model import build, campaigns, factions, schemas
from tests.model.fixtures import make_context, register_catalogs


def spf(faction, campaign, playable=False, is_major=False):
    return {"faction": faction, "campaign": campaign, "playable": playable, "is_major": is_major}


def faction_row(key):
    return {"key": key, "subculture": "", "category": "", "is_rebel": False, "is_quest_faction": False,
            "flags_path": "", "primary_colour_hex": ""}


def campaign_context():
    ctx = make_context({
        "campaigns": [
            {"campaign_name": "wh3_main_combi", "map_name": "wh3_main_combi_map_5",
             "script_path": "script/campaign/main_warhammer"},
            {"campaign_name": "wh3_main_chaos", "map_name": "wh3_main_chaos_map_4", "script_path": ""},
        ],
        "start_pos_factions": [
            spf("reikland", "wh3_main_combi", playable=True, is_major=True),
            spf("reikland", "wh3_main_chaos", is_major=True),
            spf("marienburg", "wh3_main_combi"),
            spf("reikland", "wh3_main_combi", playable=True, is_major=True),
        ],
        "factions": [faction_row("reikland"), faction_row("marienburg"), faction_row("nowhere")],
    }, loc={"campaigns_onscreen_name_wh3_main_combi": "Immortal Empires"})
    register_catalogs(ctx, campaigns, factions)
    return ctx


def test_campaigns_list_factions_by_start_position():
    ctx = campaign_context()
    built = {c["key"]: c for c in campaigns.build(ctx)["campaign"]}
    combi = built["wh3_main_combi"]
    assert combi["name"] == "Immortal Empires" and combi["map"] == "wh3_main_combi_map_5"
    assert combi["script_folder"] == "script/campaign/main_warhammer"
    assert [f["key"] for f in combi["factions"]] == ["marienburg", "reikland"]
    assert [f["key"] for f in combi["playable_factions"]] == ["reikland"]
    assert [f["key"] for f in combi["major_factions"]] == ["reikland"]
    chaos = built["wh3_main_chaos"]
    assert chaos["name"] is None and chaos["script_folder"] is None and chaos["playable_factions"] == []
    assert ctx.missing_names["campaign"] == 1
    for campaign in built.values():
        schemas.ENTITY_MODELS["campaign"].model_validate(campaign)


def test_factions_record_start_playable_and_major_campaigns():
    ctx = campaign_context()
    built = {f["key"]: f for f in factions.build(ctx)["faction"]}
    keys = lambda links: [link["key"] for link in links]
    reikland = built["reikland"]
    assert keys(reikland["start_campaigns"]) == ["wh3_main_chaos", "wh3_main_combi"]
    assert keys(reikland["playable_in"]) == ["wh3_main_combi"]
    assert keys(reikland["major_in"]) == ["wh3_main_chaos", "wh3_main_combi"]
    assert reikland["start_campaigns"][1]["name"] == "Immortal Empires"
    assert (built["nowhere"]["start_campaigns"], built["nowhere"]["playable_in"], built["nowhere"]["major_in"]) == ([], [], [])
    for faction in built.values():
        schemas.ENTITY_MODELS["faction"].model_validate(faction)


def test_campaign_module_is_built_and_regions_are_reverse_linked():
    assert campaigns in build.MODULES
    assert ("campaign", "regions", "campaign", "region") in build.REVERSE


def test_missing_campaigns_table_is_partial():
    ctx = make_context({"dummy": [{"a": 1}]})
    assert campaigns.build(ctx) == {"campaign": []}
    assert ctx.partial["campaign"] == ["campaigns"]
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `uv run pytest tests/model/test_campaigns.py -q`
Expected: FAIL with `ImportError: cannot import name 'campaigns'`.

- [ ] **Step 3: Implement.**

Create `twwiki/model/campaigns.py`:

```python
"""Campaigns (Immortal Empires, The Realm of Chaos, ...) and which factions start in each."""

from __future__ import annotations

from .context import Context, grouped, opt


def catalog(ctx: Context) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {"campaign": {}}
    if ctx.table_exists("campaigns"):
        for r in ctx.rows("SELECT campaign_name FROM campaigns"):
            key = r["campaign_name"]
            out["campaign"][key] = ctx.catalog_name("campaign", f"campaigns_onscreen_name_{key}")
    return out


def build(ctx: Context) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {"campaign": []}
    if not ctx.require("campaign", "campaigns"):
        return out
    starts = grouped(ctx, "start_pos_factions", "campaign", "faction")
    for r in ctx.rows("SELECT * FROM campaigns ORDER BY campaign_name"):
        key = r["campaign_name"]
        source = ("campaign", key)
        rows = starts.get(key, [])

        def factions(relation: str, flag: str | None = None) -> list[dict]:
            keys = sorted({s["faction"] for s in rows if flag is None or s[flag]})
            return [ctx.links.link("faction", f, source=source, relation=relation) for f in keys]

        out["campaign"].append({
            "key": key,
            "name": ctx.links.name("campaign", key),
            "map": opt(r["map_name"]),
            "script_folder": opt(r["script_path"]),
            "factions": factions("factions"),
            "playable_factions": factions("playable_factions", "playable"),
            "major_factions": factions("major_factions", "is_major"),
            "regions": [],
        })
    return out
```

In `twwiki/model/schemas.py`, add this section before `# ---- Factions, cultures, difficulty, campaign variables`:

```python
# ---- Campaigns -------------------------------------------------------------

@entity("campaign")
class Campaign(Strict):
    key: str
    name: str | None
    map: str | None
    script_folder: str | None
    factions: list[Link]
    playable_factions: list[Link]
    major_factions: list[Link]
    regions: list[Link] = []
```

Add these to `Faction`, after `primary_colour`:

```python
    start_campaigns: list[Link]
    playable_in: list[Link]
    major_in: list[Link]
```

In `twwiki/model/factions.py`, add this helper above `build`:

```python
def _campaign_links(ctx: Context, rows: list[dict], source: tuple[str, str], relation: str,
                    flag: str | None = None) -> list[dict]:
    keys = sorted({r["campaign"] for r in rows if flag is None or r[flag]})
    return [ctx.links.link("campaign", k, source=source, relation=relation) for k in keys]
```

In `build`, under `if ctx.require("faction", "factions"):` and before the loop, add `starts = grouped(ctx, "start_pos_factions", "faction", "campaign")`. Add to the faction dict, after `"primary_colour"`:

```python
                "start_campaigns": _campaign_links(ctx, starts.get(key, []), source, "start_campaigns"),
                "playable_in": _campaign_links(ctx, starts.get(key, []), source, "playable_in", "playable"),
                "major_in": _campaign_links(ctx, starts.get(key, []), source, "major_in", "is_major"),
```

In `tests/model/test_build.py`, the `fake_faction` helper builds a faction without these fields. Add `"start_campaigns": [], "playable_in": [], "major_in": []` to its dict literal.

In `twwiki/model/build.py`:
- Import `campaigns`: `from . import abilities, buildings, campaigns, characters, effects, factions, items, regions, technologies, units`.
- Set `MODULES = [effects, campaigns, abilities, units, characters, technologies, buildings, items, factions, regions]`.
- Append `("campaign", "regions", "campaign", "region"),` to `REVERSE`.
- Add `"campaign": ["map"],` to `INDEX_FIELDS`.

- [ ] **Step 4: Run the tests to see them pass**

Regenerate the Firestore field overrides for the new entity type: `uv run python -m twwiki.publish --write-indexes`. The log shows `wrote …firestore.indexes.json`, and `git diff firestore.indexes.json` adds only the `campaign` override.

Run: `uv run pytest tests/model/test_campaigns.py tests/model/test_factions.py tests/model/test_build.py tests/publish -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add twwiki/model/campaigns.py twwiki/model/schemas.py twwiki/model/factions.py twwiki/model/build.py tests/model/test_campaigns.py tests/model/test_build.py firestore.indexes.json
git commit -m "feat(model): campaign entity and faction start, playable and major campaigns" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Campaign strings become links; campaign tags; campaign-exclusive permissions

**Files:**
- Modify: `twwiki/model/schemas.py`:
  - `SkillTreeNode`
  - `SkillTree`
  - `Character`
  - `Placement`
  - `TreeNode`
  - `TechnologyTree`
  - `ChainAvailability`
  - `Region`
  - `Province`
  - `DifficultyEffect`
  - `CampaignVariableOverride`
- Modify: `twwiki/model/regions.py` (region and province `campaign`)
- Modify: `twwiki/model/characters.py` (`_characters`, `_tree`)
- Modify: `twwiki/model/buildings.py` (`chain_availability`)
- Modify: `twwiki/model/factions.py` (difficulty effects, variable overrides)
- Modify: `twwiki/model/technologies.py` (placements, tree nodes, tree campaign)
- Modify: `twwiki/model/units.py` (custom battle factions)
- Test:
  - `tests/model/test_regions.py`
  - `tests/model/test_characters.py`
  - `tests/model/test_buildings.py`
  - `tests/model/test_factions.py`
  - `tests/model/test_technologies.py`
  - `tests/model/test_units.py`

**Interfaces:**
- Consumes: the `campaign` link type (Task 3) and `ctx.tally` (Task 2).
- Produces:
  - `campaign: Link | None` on:
    - `Region`
    - `Province`
    - `SkillTree`
    - `SkillTreeNode`
    - `ChainAvailability`
    - `DifficultyEffect`
    - `CampaignVariableOverride`
    - `TechnologyTree`
  - `campaigns: list[Link]` on `Character`, `TreeNode` and `Placement`.
  - Tally `campaign_exclusive_permissions_excluded`.

- [ ] **Step 1: Write the failing tests.**

`tests/model/test_regions.py`:
- In `regions_context()`, just before `return ctx`, add `ctx.links.register("campaign", {"wh3_main_combi": "Immortal Empires", "wh3_main_chaos": "The Realm of Chaos", "wh3_main_prologue": "The Lost God"})`.
- Change the campaign assertions:
  - `altdorf["campaign"] == "wh3_main_combi"` becomes `altdorf["campaign"]["key"] == "wh3_main_combi" and altdorf["campaign"]["name"] == "Immortal Empires"`.
  - `reikland["campaign"] == "wh3_main_combi"` becomes `reikland["campaign"]["key"] == "wh3_main_combi"`.
  - `ice["campaign"] == "wh3_main_prologue"` becomes `ice["campaign"]["key"] == "wh3_main_prologue"`.
  - The sea tuple assertion keeps `None` for `sea["campaign"]`.

`tests/model/test_buildings.py`, in `test_chain_availability_scopes_sorted_and_deduplicated`:
- Add `ctx.links.register("campaign", {"wh3_main_combi": "Immortal Empires"})` next to the other `register` calls.
- Change the comprehension's `a["campaign"]` to `a["campaign"]["key"] if a["campaign"] else None`.

`tests/model/test_factions.py`:
- In `test_difficulty_levels_split_ai_and_human`, change `level["human"][0]["campaign"] == "main_warhammer"` to `level["human"][0]["campaign"] == {"type": "campaign", "key": "main_warhammer", "name": None, "missing": True}`.
- In `test_campaign_variables_with_overrides`, change the expected override to `{"campaign": {"type": "campaign", "key": "wh3_main_chaos", "name": None, "missing": True}, "difficulty": None, "campaign_type": None, "value": 7.0}`.

`tests/model/test_technologies.py`:
- Give `node(...)` a `campaign_key=""` parameter and use it in the row: `"campaign_key": campaign_key`.
- Append:

```python
def test_campaign_restricted_nodes_and_placements():
    ctx = tech_context()
    ctx.links.register("campaign", {"wh3_main_chaos": "The Realm of Chaos"})
    ctx.con.execute("UPDATE technology_nodes SET campaign_key = 'wh3_main_chaos' WHERE key = 'hw_wulf_node'")
    built = technologies.build(ctx)
    trees = {t["key"]: t for t in built["technology_tree"]}
    wulf_nodes = {n["key"]: n for n in trees["emp_wulfhart"]["nodes"]}
    assert [c["key"] for c in wulf_nodes["hw_wulf_node"]["campaigns"]] == ["wh3_main_chaos"]
    assert all(n["campaigns"] == [] for n in trees["emp_civ_reworkd"]["nodes"])
    assert trees["emp_wulfhart"]["campaign"] is None
    placements = {p["node_key"]: p for p in {t["key"]: t for t in built["technology"]}["heavy_weapons"]["placements"]}
    assert placements["hw_node"]["campaigns"] == []
    assert [c["name"] for c in placements["hw_wulf_node"]["campaigns"]] == ["The Realm of Chaos"]
    for tree in trees.values():
        schemas.ENTITY_MODELS["technology_tree"].model_validate(tree)
```

`tests/model/test_characters.py`, append:

```python
def test_character_campaigns_and_skill_node_campaign_links():
    ctx = character_context()
    ctx.con.execute("CREATE TABLE campaign_to_agent_subtypes AS SELECT * FROM (VALUES "
                    "('kf', 'wh3_main_combi'), ('kf', 'wh3_main_chaos')) t(agent_subtype, campaign_type)")
    ctx.con.execute("UPDATE character_skill_nodes SET campaign_key = 'wh3_main_combi' WHERE key = 'n_mentor'")
    ctx.links.register("campaign", {"wh3_main_combi": "Immortal Empires", "wh3_main_chaos": "The Realm of Chaos"})
    built = {c["key"]: c for c in characters.build(ctx)["character"]}
    kf = built["kf"]
    assert [c["key"] for c in kf["campaigns"]] == ["wh3_main_chaos", "wh3_main_combi"]
    assert built["wizard"]["campaigns"] == []
    tree = kf["skill_trees"][0]
    assert tree["campaign"] is None
    assert tree["nodes"][0]["campaign"] is None and tree["nodes"][1]["campaign"]["name"] == "Immortal Empires"
    schemas.ENTITY_MODELS["character"].model_validate(kf)
```

`tests/model/test_units.py`:
- In `unit_context`, replace the `units_custom_battle_permissions` rows with:

```python
        "units_custom_battle_permissions": [{"faction": "reikland", "unit": "gs", "campaign_exclusive": False},
                                            {"faction": "reikland", "unit": "gs", "campaign_exclusive": False},
                                            {"faction": "norsca", "unit": "gs", "campaign_exclusive": True}],
```

- Append:

```python
def test_campaign_exclusive_permissions_are_excluded_and_counted():
    ctx, built = built_units()
    assert [f["key"] for f in built["gs"]["custom_battle_factions"]] == ["reikland"]
    assert ctx.tally["campaign_exclusive_permissions_excluded"] == 1
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `uv run pytest tests/model/test_regions.py tests/model/test_buildings.py tests/model/test_factions.py tests/model/test_technologies.py tests/model/test_characters.py tests/model/test_units.py -q`
Expected: failures such as `TypeError: string indices must be integers` and `KeyError: 'campaigns'`.

- [ ] **Step 3: Implement.**

`twwiki/model/schemas.py`:
- Change `campaign: str | None` to `campaign: Link | None` in `SkillTreeNode`, `SkillTree`, `TechnologyTree`, `ChainAvailability`, `Region`, `Province` and `DifficultyEffect`.
- In `CampaignVariableOverride`, change `campaign: str` to `campaign: Link | None`.
- Add `campaigns: list[Link]` to:
  - `Character`, after `factions`;
  - `Placement`, after `resource_cost`;
  - `TreeNode`, after `pixel_offset_y`.

`twwiki/model/regions.py`:
- Region dict: `"campaign": ctx.links.link("campaign", opt(s["campaign"]), source=source, relation="campaign") if s else None,`
- Province dict: `"campaign": ctx.links.link("campaign", next((start[j["region"]]["campaign"] for j in rows if j["region"] in start), None), source=source, relation="campaign"),`

`twwiki/model/characters.py`:
- In `_characters`, add this after `trees = _skill_trees(ctx)`:

```python
    # campaign_to_agent_subtypes lists every campaign a subtype appears in (Karl Franz has
    # rows for both Immortal Empires and The Realm of Chaos). No rows means no data; the
    # web app treats an empty list as every campaign.
    campaign_rows = grouped(ctx, "campaign_to_agent_subtypes", "agent_subtype", "campaign_type")
```

- Add to the character dict, after `"factions"`:

```python
            "campaigns": [ctx.links.link("campaign", c, source=source, relation="campaigns")
                          for c in sorted({row["campaign_type"] for row in campaign_rows.get(key, [])})],
```

- In `_tree`, change the tree's `"campaign"` to `ctx.links.link("campaign", opt(s["campaign_key"]), source=source, relation="skill_tree_campaign")`, and the node's `"campaign"` to `ctx.links.link("campaign", opt(n["campaign_key"]), source=source, relation="skill_tree_campaign")`.

`twwiki/model/buildings.py`, in `chain_availability`: `"campaign": ctx.links.link("campaign", campaign, source=source, relation="availability"),`

`twwiki/model/factions.py`:
- Difficulty entries: `"campaign": ctx.links.link("campaign", opt(r["optional_campaign_key"]), source=("difficulty_level", str(level)), relation="campaign"),`
- Variable overrides:

```python
                "overrides": [{"campaign": ctx.links.link("campaign", opt(o["campaign_name"]), source=("campaign_variable", key),
                                                          relation="overrides"),
                               "difficulty": opt(o["difficulty"]), "campaign_type": opt(o["campaign_type"]), "value": o["value"]}
                              for o in overrides.get(key, [])],
```

`twwiki/model/technologies.py`:
- In `build`, above the `placements` loop, add:

```python
    def node_campaigns(n: dict, source: tuple[str, str]) -> list[dict]:
        key = opt(n["campaign_key"])
        return [ctx.links.link("campaign", key, source=source, relation="campaigns")] if key else []
```

- Add `"campaigns": node_campaigns(n, ("technology", n["technology_key"])),` to each placement dict.
- Add `"campaigns": node_campaigns(n, ("technology_tree", n["technology_node_set"])),` to each tree node dict.
- Change the tree's `"campaign"` to `ctx.links.link("campaign", opt(r["campaign_key"]), source=source, relation="campaign")`.

`twwiki/model/units.py`:
- Add this function after `_distinct`:

```python
def _custom_battle_factions(ctx: Context) -> dict[str, list[str]]:
    """Factions that field each unit in custom battles; campaign-exclusive rows are left out and counted."""
    out: dict[str, list[str]] = defaultdict(list)
    if not ctx.table_exists("units_custom_battle_permissions"):
        return out
    for r in ctx.rows("SELECT DISTINCT unit, faction, campaign_exclusive FROM units_custom_battle_permissions "
                      "ORDER BY unit, faction, campaign_exclusive"):
        if r["campaign_exclusive"]:
            ctx.tally["campaign_exclusive_permissions_excluded"] += 1
        elif opt(r["faction"]) and r["faction"] not in out[r["unit"]]:
            out[r["unit"]].append(r["faction"])
    return out
```

- Replace `factions = _distinct(ctx, "units_custom_battle_permissions", "unit", "faction")` with `factions = _custom_battle_factions(ctx)`.

- [ ] **Step 4: Run the tests to see them pass**

Run: `uv run pytest tests/model -q --ignore=tests/model/test_real_build.py`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add twwiki/model tests/model
git commit -m "feat(model): campaign links and tags; drop campaign-exclusive custom battle permissions" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---
### Task 5: Agent type names and item category and rarity

**Files:**
- Modify: `twwiki/model/schemas.py` (new `AgentType`, `ItemCategory` and `Rarity`; `Character.agent_types`; `Item`)
- Modify: `twwiki/model/characters.py` (label helpers, `_characters`)
- Modify: `twwiki/model/items.py` (`_items`, new `_rarity`)
- Test: `tests/model/test_characters.py`, `tests/model/test_items.py`

**Interfaces:**
- Consumes: `ctx.tally` (Task 2).
- Produces:
  - `characters.agent_type_labels(ctx) -> dict[str, dict[str, str]]`, mapping agent to culture to name.
  - `characters.agent_type(ctx, labels, agent: str, culture: str | None) -> {"key", "name"}`
  - `characters.faction_cultures(ctx) -> dict[str, str]`
  - `Character.agent_types: list[AgentType]`
  - `Item`:
    - `category: ItemCategory`
    - `rarity: Rarity | None`
    - `agent_types: list[AgentType]`
    - `applies_to` removed
  - Tallies `unresolved_agent_type_names` and `unmatched_rarity_scores`.

- [ ] **Step 1: Write the failing tests.**

In `tests/model/test_characters.py`:
- Add these entries to the `loc={...}` dict in `character_context()`:

```python
        "agent_culture_details_onscreen_name_11": "General of the Empire",
        "agent_culture_details_onscreen_name_12": "Lord",
        "agent_culture_details_onscreen_name_13": "Lord",
        "agent_culture_details_onscreen_name_14": "Damsel",
        "agent_culture_details_onscreen_name_15": "Runesmith",
```

- In `test_karl_franz_character_and_tree`, change `assert kf["agent_types"] == ["general"]` to `assert kf["agent_types"] == [{"key": "general", "name": None}]`.
- Append:

```python
def test_agent_type_names_use_the_character_culture_then_the_common_name():
    ctx = character_context()
    ctx.con.execute("CREATE TABLE agent_culture_details AS SELECT * FROM (VALUES "
                    "('general', 'wh_main_emp_empire', 11, 0), ('general', 'wh_main_brt_bretonnia', 12, 0), "
                    "('general', 'wh_main_dwf_dwarfs', 13, 0), ('wizard', 'wh_main_brt_bretonnia', 14, 0), "
                    "('wizard', 'wh_main_dwf_dwarfs', 15, 0)) t(agent, culture, key, level)")
    ctx.con.execute("CREATE TABLE factions AS SELECT * FROM (VALUES ('reikland', 'sc_empire'), "
                    "('golden_order', 'sc_empire')) t(key, subculture)")
    ctx.con.execute("CREATE TABLE cultures_subcultures AS SELECT * FROM (VALUES ('sc_empire', 'wh_main_emp_empire')) "
                    "t(subculture, culture)")
    built = {c["key"]: c for c in characters.build(ctx)["character"]}
    assert built["kf"]["agent_types"] == [{"key": "general", "name": "General of the Empire"}]
    # No Empire wizard label: Damsel and Runesmith tie, and Bretonnia's culture key sorts first.
    assert built["wizard"]["agent_types"] == [{"key": "wizard", "name": "Damsel"}]
    labels = characters.agent_type_labels(ctx)
    assert characters.agent_type(ctx, labels, "general", None) == {"key": "general", "name": "Lord"}
    assert characters.agent_type(ctx, labels, "spy", None) == {"key": "spy", "name": None}
    assert ctx.tally["unresolved_agent_type_names"] == 1
    schemas.ENTITY_MODELS["character"].model_validate(built["kf"])
```

In `tests/model/test_items.py`:
- In `ancillary(**o)`, add `"uniqueness_score": 80` to the row.
- In `items_context()`, pass `uniqueness_score=999` to the `banner` ancillary, and add the table:

```python
        "ancillary_uniqueness_groupings": [
            {"group_key": "uncommon", "uniqueness_min": 80, "uniqueness_max": 100, "col_hex": "5DADE2"},
            {"group_key": "common", "uniqueness_min": 35, "uniqueness_max": 50, "col_hex": ""},
        ],
```

- Add these loc entries:

```python
        "ancillaries_categories_onscreen_name_arcane_item": "{{tr:arcane_item_title}}",
        "arcane_item_title": "Arcane Item",
        "ancillary_uniqueness_groupings_onscreen_name_uncommon": "[[col:ancillary_uncommon]]Uncommon[[/col]]",
```

- In `test_item_fields_and_links`, replace `assert khepra["agent_types"] == ["general", "wizard"]` with:

```python
    assert khepra["agent_types"] == [{"key": "general", "name": None}, {"key": "wizard", "name": None}]
    assert khepra["category"] == {"key": "arcane_item", "name": "Arcane Item"}
    assert khepra["rarity"] == {"key": "uncommon", "name": "[[col:ancillary_uncommon]]Uncommon[[/col]]", "colour": "#5DADE2"}
    assert "applies_to" not in khepra
```

- After `banner = built["banner"]`, add `assert banner["rarity"] is None and ctx.tally["unmatched_rarity_scores"] == 1`.

- [ ] **Step 2: Run the tests to see them fail**

Run: `uv run pytest tests/model/test_characters.py tests/model/test_items.py -q`
Expected: FAIL. `kf["agent_types"]` is `["general"]`, and `khepra` has no `rarity` key.

- [ ] **Step 3: Implement.**

`twwiki/model/schemas.py`:
- In the characters section, before `SkillTreeNode`, add:

```python
class AgentType(Strict):
    key: str
    name: str | None
```

- Change `Character.agent_types: list[str]` to `agent_types: list[AgentType]`.
- In the items section, before `RequiredSkill`, add:

```python
class ItemCategory(Strict):
    key: str
    name: str | None


class Rarity(Strict):
    key: str
    name: str | None      # game markup kept, e.g. [[col:ancillary_rare]]Rare[[/col]]
    colour: str | None    # "#RRGGBB"
```

- In `Item`:
  - Change `category: str` to `category: ItemCategory`.
  - Add `rarity: Rarity | None` after `category`.
  - Delete `applies_to: str`.
  - Change `agent_types: list[str]` to `agent_types: list[AgentType]`.

`twwiki/model/characters.py`:
- Change the imports to `from collections import Counter, defaultdict`.
- Add after `_land_units`:

```python
def agent_type_labels(ctx: Context) -> dict[str, dict[str, str]]:
    """agent -> culture -> onscreen name, from agent_culture_details rows that have text."""
    labels: dict[str, dict[str, str]] = defaultdict(dict)
    if ctx.table_exists("agent_culture_details"):
        for r in ctx.rows("SELECT agent, culture, key FROM agent_culture_details ORDER BY agent, culture, level, key"):
            name = ctx.loc.text(f"agent_culture_details_onscreen_name_{r['key']}")
            if name and r["culture"] not in labels[r["agent"]]:
                labels[r["agent"]][r["culture"]] = name
    return labels


def agent_type(ctx: Context, labels: dict[str, dict[str, str]], agent: str, culture: str | None) -> dict:
    """The culture's own name for an agent type, else the name most cultures use
    (ties go to the earliest culture key). A type with no name at all is counted."""
    names = labels.get(agent, {})
    name = names.get(culture) if culture else None
    if name is None and names:
        counts = Counter(names.values())
        first_culture: dict[str, str] = {}
        for c in sorted(names):
            first_culture.setdefault(names[c], c)
        name = min(counts, key=lambda n: (-counts[n], first_culture[n]))
    if name is None:
        ctx.tally["unresolved_agent_type_names"] += 1
    return {"key": agent, "name": name}


def faction_cultures(ctx: Context) -> dict[str, str]:
    """faction key -> culture key, through the faction's subculture."""
    subcultures = by_key(ctx, "cultures_subcultures", "subculture")
    out = {}
    for key, faction in by_key(ctx, "factions", "key").items():
        sub = subcultures.get(faction["subculture"])
        if sub and opt(sub["culture"]):
            out[key] = sub["culture"]
    return out
```

- In `_characters`, add `labels = agent_type_labels(ctx)` and `cultures = faction_cultures(ctx)` next to `trees = _skill_trees(ctx)`.
- In the loop, after `rows = permitted.get(key, [])`, add:

```python
        faction_keys = sorted({p["faction"] for p in rows})
        culture = cultures.get(faction_keys[0]) if faction_keys else None
```

- In the dict:
  - `"agent_types": [agent_type(ctx, labels, a, culture) for a in sorted({p["agent"] for p in rows})],`
  - `"factions": [ctx.links.link("faction", f, source=source, relation="factions") for f in faction_keys],`

`twwiki/model/items.py`:
- Add `from .characters import agent_type, agent_type_labels`.
- Add this function after `_trait_levels`:

```python
def _rarity(ctx: Context, groupings: list[dict], score: int) -> dict | None:
    """The uniqueness grouping whose range holds the score; a score outside every range is counted."""
    if not groupings:
        return None
    group = next((g for g in groupings if g["uniqueness_min"] <= score <= g["uniqueness_max"]), None)
    if group is None:
        ctx.tally["unmatched_rarity_scores"] += 1
        return None
    return {
        "key": group["group_key"],
        "name": ctx.loc.text(f"ancillary_uniqueness_groupings_onscreen_name_{group['group_key']}"),
        "colour": f"#{group['col_hex']}" if opt(group["col_hex"]) else None,
    }
```

- In `_items`, next to `types = by_key(...)`, add:

```python
    groupings = ctx.rows("SELECT * FROM ancillary_uniqueness_groupings ORDER BY uniqueness_min, group_key") \
        if ctx.table_exists("ancillary_uniqueness_groupings") else []
    labels = agent_type_labels(ctx)
```

- In the item dict:
  - Replace `"category": r["category"],` with:

```python
            "category": {"key": r["category"],
                         "name": ctx.loc.text(f"ancillaries_categories_onscreen_name_{r['category']}")},
            "rarity": _rarity(ctx, groupings, r["uniqueness_score"]),
```

  - Delete the `"applies_to"` line.
  - Replace `agent_types` with `"agent_types": [agent_type(ctx, labels, a, None) for a in sorted({a["agent"] for a in agents.get(key, [])})],`.

- [ ] **Step 4: Run the tests to see them pass**

Run: `uv run pytest tests/model -q --ignore=tests/model/test_real_build.py`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add twwiki/model tests/model
git commit -m "feat(model): agent type names, item category names and item rarity" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Building level availability, derived technology tree names, attribute titles

**Files:**
- Modify: `twwiki/model/schemas.py` (`BuildingLevel`, `TechnologyTree`)
- Modify: `twwiki/model/buildings.py` (new `level_availability`; the level dict)
- Modify: `twwiki/model/technologies.py` (new `derived_tree_name`; `catalog`; the tree dict)
- Modify: `twwiki/model/units.py` (new `_attribute`)
- Modify: `twwiki/model/build.py` (`INDEX_FIELDS["building_level"]`)
- Test:
  - `tests/model/test_buildings.py`
  - `tests/model/test_technologies.py`
  - `tests/model/test_units.py`

**Interfaces:**
- Consumes: `split_title_body` (Task 1) and `ctx.tally` (Task 2).
- Produces:
  - `BuildingLevel.availability: list[Link]`, replacing `cultures`, with link relation `level_availability`.
  - Tally `unresolved_building_availability_keys`.
  - `TechnologyTree.name_derived: bool`
  - Unit attributes `{key, name, description}`, where `description` is the bullet body only.

- [ ] **Step 1: Write the failing tests.**

In `tests/model/test_buildings.py`, delete the line `assert tf["cultures"] == ["wh_main_emp_empire"]` from `test_training_field_level` and append:

```python
def test_level_availability_resolves_culture_subculture_faction_and_unresolved_keys():
    ctx = building_context()
    ctx.con.execute("INSERT INTO building_culture_variants (building, culture, subculture, faction, short_description, "
                    "icon, disables) VALUES ('barracks_2', '', 'sc_teb', '', '', '', false), "
                    "('barracks_2', 'ghost', '', '', '', '', false)")
    ctx.links.register("culture", {"wh_main_emp_empire": "The Empire"})
    ctx.links.register("subculture", {"sc_teb": "Tilea"})
    ctx.links.register("faction", {"followers": "Followers of Nagash"})
    levels = {l["key"]: l for l in buildings.build(ctx)["building_level"]}
    assert levels["barracks_1"]["availability"] == [
        {"type": "culture", "key": "wh_main_emp_empire", "name": "The Empire", "missing": False}]
    assert levels["tower"]["availability"] == [
        {"type": "faction", "key": "followers", "name": "Followers of Nagash", "missing": False}]
    assert levels["barracks_2"]["availability"] == [
        {"type": "culture", "key": "ghost", "name": None, "missing": True},
        {"type": "subculture", "key": "sc_teb", "name": "Tilea", "missing": False}]
    assert ctx.tally["unresolved_building_availability_keys"] == 1
    for level in levels.values():
        schemas.ENTITY_MODELS["building_level"].model_validate(level)
```

In `tests/model/test_technologies.py`, change the fixtures import to `from tests.model.fixtures import make_context, register_catalogs` and append:

```python
def test_unnamed_trees_derive_a_name_from_faction_then_culture():
    def tree(key, culture, faction=""):
        return {"key": key, "culture": culture, "subculture": "", "faction_key": faction, "campaign_key": "",
                "colour_hex": ""}

    ctx = make_context({
        "technology_node_sets": [tree("named", "cathay"), tree("wulf", "empire", "wulfhart"),
                                 tree("cth_mil", "cathay"), tree("rogue_mil", "rogue")],
        "technology_nodes": [node("n1", "t1", "named", 100)],
    }, loc={
        "technology_node_sets_localised_name_named": "Cathay Civil",
        "factions_screen_name_wulfhart": "The Huntsmarshal's Expedition",
        "cultures_name_empire": "The Empire",
        "cultures_name_cathay": "Grand Cathay",
    })
    register_catalogs(ctx, technologies)
    trees = {t["key"]: t for t in technologies.build(ctx)["technology_tree"]}
    assert (trees["named"]["name"], trees["named"]["name_derived"]) == ("Cathay Civil", False)
    assert (trees["wulf"]["name"], trees["wulf"]["name_derived"]) == ("The Huntsmarshal's Expedition Technologies", True)
    assert (trees["cth_mil"]["name"], trees["cth_mil"]["name_derived"]) == ("Grand Cathay Technologies", True)
    assert (trees["rogue_mil"]["name"], trees["rogue_mil"]["name_derived"]) == (None, False)
    assert ctx.missing_names["technology_tree"] == 1
    for t in trees.values():
        schemas.ENTITY_MODELS["technology_tree"].model_validate(t)
```

In `tests/model/test_units.py`:
- In `test_greatswords_stats_weapons_and_links`, change the attributes assertion to `assert gs["attributes"] == [{"key": "hide_forest", "name": "Hide (forest)", "description": "Can hide in forests."}]`.
- Append:

```python
def test_attribute_name_falls_back_to_the_bullet_title():
    ctx = make_context({"dummy": [{"a": 1}]}, loc={
        "unit_attributes_bullet_text_stalk": "Stalk||Can move while hidden.",
        "unit_attributes_bullet_text_plain": "Just text",
    })
    assert units._attribute(ctx, "stalk") == {"key": "stalk", "name": "Stalk", "description": "Can move while hidden."}
    assert units._attribute(ctx, "plain") == {"key": "plain", "name": None, "description": "Just text"}
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `uv run pytest tests/model/test_buildings.py tests/model/test_technologies.py tests/model/test_units.py -q`
Expected: FAIL with `KeyError: 'availability'`, `KeyError: 'name_derived'` and `AttributeError: ... '_attribute'`.

- [ ] **Step 3: Implement.**

`twwiki/model/schemas.py`:
- In `BuildingLevel`, replace `cultures: list[str]` with `availability: list[Link]`.
- In `TechnologyTree`, add `name_derived: bool` after `name`.

`twwiki/model/buildings.py`:
- Add after `level_name`:

```python
AVAILABILITY_TYPES = ("culture", "subculture", "faction")


def level_availability(ctx: Context, variants: list[dict], source: tuple[str, str]) -> list[dict]:
    """Links for the culture, subculture and faction keys on a level's culture variants.
    Each key is looked up as a culture, then a subculture, then a faction; a key that
    is none of them becomes a missing link of its own column's type and is counted."""
    found: dict[str, str] = {}
    for v in variants:
        for column in AVAILABILITY_TYPES:
            value = opt(v[column])
            if value:
                found.setdefault(value, column)
    out = []
    for value, column in sorted(found.items()):
        entity_type = next((t for t in AVAILABILITY_TYPES if ctx.links.has(t, value)), None)
        if entity_type is None:
            ctx.tally["unresolved_building_availability_keys"] += 1
            entity_type = column
        out.append(ctx.links.link(entity_type, value, source=source, relation="level_availability"))
    return out
```

- In `build`, replace the `"cultures"` line of the level dict with `"availability": level_availability(ctx, own_variants, source),`.

`twwiki/model/technologies.py`:
- Add before `catalog`:

```python
def derived_tree_name(ctx: Context, tree: dict) -> str | None:
    """'<faction or culture name> Technologies' for a tree the game leaves unnamed."""
    owner = ctx.loc.text(f"factions_screen_name_{tree['faction_key']}") if opt(tree["faction_key"]) else None
    if owner is None and opt(tree["culture"]):
        owner = ctx.loc.text(f"cultures_name_{tree['culture']}")
    return f"{owner} Technologies" if owner else None
```

- In `catalog`, replace the `technology_node_sets` block with:

```python
    if ctx.table_exists("technology_node_sets"):
        for r in ctx.rows("SELECT key, culture, faction_key FROM technology_node_sets"):
            name = ctx.loc.text(f"technology_node_sets_localised_name_{r['key']}") or derived_tree_name(ctx, r)
            if name is None:
                ctx.missing_names["technology_tree"] += 1
            out["technology_tree"][r["key"]] = name
```

- In the tree dict, after `"name"`, add:

```python
                "name_derived": ctx.loc.text(f"technology_node_sets_localised_name_{key}") is None
                                and ctx.links.name("technology_tree", key) is not None,
```

`twwiki/model/units.py`:
- Add `from .text import split_title_body`.
- Add this function after `_custom_battle_factions`:

```python
def _attribute(ctx: Context, key: str) -> dict:
    """An attribute's name and description; the bullet text's title names it when it has no name of its own."""
    title, body = split_title_body(ctx.loc.text(f"unit_attributes_bullet_text_{key}"))
    return {"key": key, "name": ctx.loc.text(f"unit_attributes_imued_effect_text_{key}") or title, "description": body}
```

- Replace the `"attributes": [...]` comprehension with:

```python
            "attributes": [
                _attribute(ctx, a)
                for a in (attributes.get(lu["attribute_group"], []) if lu and opt(lu["attribute_group"]) else [])
            ],
```

  Keep the existing loop source expression unchanged. Only the dict body is replaced.

`twwiki/model/build.py`: set `"building_level": ["level"],` in `INDEX_FIELDS`.

- [ ] **Step 4: Run the tests to see them pass**

Run: `uv run pytest tests/model -q --ignore=tests/model/test_real_build.py`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add twwiki/model tests/model
git commit -m "feat(model): building availability links, derived tree names, attribute titles" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: Effect application presentation fields

**Files:**
- Modify: `twwiki/model/schemas.py` (`EffectApplication`)
- Modify: `twwiki/model/effects.py` (`scope_text`, `effect_application`, `build`)
- Test: `tests/model/test_effects.py`

**Interfaces:**
- Consumes: `ctx.effect_display` and `ctx.tally` (Task 2).
- Produces:
  - `EffectApplication`, in this field order:
    - `effect`
    - `scope`
    - `scope_text: str | None`
    - `value`
    - `priority: int | None`
    - `hidden: bool`
    - `favourable: bool | None`
    - `icon_image: str | None`
    - `source`
    - the optional fields
  - `effects.scope_text(ctx, scope) -> str | None`
  - Tally `effect_applications_without_scope_text`.
  - `effects.build` fills `ctx.effect_display[effect_key]` with `{priority, is_positive_value_good, icon_image, icon_negative_image}` before building bundles. Every module listed after `effects` in `MODULES` sees it.

- [ ] **Step 1: Write the failing tests.** Append to `tests/model/test_effects.py`:

```python
def test_effect_application_presentation_fields():
    ctx = make_context({"dummy": [{"a": 1}]}, loc={
        "campaign_effect_scopes_localised_text_army_own": "\\\\n([[img:icon_general]][[/img]]Lord's army)",
        "campaign_effect_scopes_localised_text_faction_own": "\\n",
    })
    ctx.links.register("effect", {"good": "Good", "cost": "Cost", "quiet": "Quiet"})
    ctx.links.register("skill", {"s": "Skill"})
    ctx.effect_display.update({
        "good": {"priority": 1, "is_positive_value_good": True, "icon_image": "g.png", "icon_negative_image": "g_neg.png"},
        "cost": {"priority": 2, "is_positive_value_good": False, "icon_image": "c.png", "icon_negative_image": None},
        "quiet": {"priority": 0, "is_positive_value_good": True, "icon_image": None, "icon_negative_image": None},
    })

    def app(key, value, scope="army_own"):
        return effects.effect_application(ctx, key, scope=scope, value=value, source=("skill", "s"))

    lord = app("good", 5)
    assert (lord["scope_text"], lord["priority"], lord["hidden"], lord["favourable"], lord["icon_image"]) == \
        ("([[img:icon_general]][[/img]]Lord's army)", 1, False, True, "g.png")
    assert (app("good", -5)["favourable"], app("good", -5)["icon_image"]) == (False, "g_neg.png")
    assert (app("cost", 5)["favourable"], app("cost", 5)["icon_image"]) == (False, "c.png")
    assert app("cost", -5)["favourable"] is True
    assert app("good", 0)["favourable"] is None
    assert app("quiet", 1)["hidden"] is True
    unknown = app("not_an_effect", 3, scope="faction_own")
    assert (unknown["scope_text"], unknown["priority"], unknown["hidden"], unknown["favourable"], unknown["icon_image"]) == \
        (None, None, False, None, None)
    assert app("good", 1, scope="")["scope_text"] is None
    assert ctx.tally["effect_applications_without_scope_text"] == 1
    schemas.EffectApplication.model_validate(lord)


def test_build_fills_effect_display_before_bundles():
    ctx = effects_context()
    bundle = effects.build(ctx)["effect_bundle"][0]
    assert ctx.effect_display["e_attack"] == {"priority": 1, "is_positive_value_good": True,
                                              "icon_image": None, "icon_negative_image": None}
    assert bundle["effects"][0]["priority"] == 2 and bundle["effects"][0]["favourable"] is True
```

If `make_context` is not yet imported in this file, add `from tests.model.fixtures import make_context, register_catalogs`.

- [ ] **Step 2: Run the tests to see them fail**

Run: `uv run pytest tests/model/test_effects.py -q`
Expected: FAIL with `KeyError: 'scope_text'`.

- [ ] **Step 3: Implement.**

`twwiki/model/schemas.py`: replace `EffectApplication` with:

```python
class EffectApplication(Strict):
    effect: Link
    scope: str | None
    scope_text: str | None          # e.g. "([[img:icon_general]][[/img]]Lord's army)"
    value: float
    priority: int | None            # None when the effect is not in the game data
    hidden: bool                    # priority 0: the game does not display it
    favourable: bool | None         # None for a zero value or an unknown effect
    icon_image: str | None          # the negative icon when unfavourable and one exists
    source: Link
    value_damaged: float | None = None      # buildings only
    value_ruined: float | None = None       # buildings only
    context_requirement: str | None = None  # buildings only
    advancement_stage: str | None = None    # effect bundles only
```

`twwiki/model/effects.py`:
- Add `import re` to the imports.
- Below `BONUS_COLUMNS`, add `SCOPE_LEADING_NEWLINES = re.compile(r"^(?:\s|\\+n)+")`.
- Replace `effect_application` with:

```python
def scope_text(ctx: Context, scope: str | None) -> str | None:
    """The suffix the game prints after an effect for its scope; a scope with no text is counted."""
    if not scope:
        return None
    text = ctx.loc.text(f"campaign_effect_scopes_localised_text_{scope}")
    text = SCOPE_LEADING_NEWLINES.sub("", text) if text else ""
    if not text:
        ctx.tally["effect_applications_without_scope_text"] += 1
        return None
    return text


def effect_application(ctx: Context, effect_key: str, *, scope: str | None, value: float,
                       source: tuple[str, str], **extra) -> dict:
    value = float(value)
    display = ctx.effect_display.get(effect_key)
    priority = display["priority"] if display else None
    favourable = None if display is None or value == 0 else (value > 0) == display["is_positive_value_good"]
    icon = None
    if display:
        negative = favourable is False and display["icon_negative_image"]
        icon = display["icon_negative_image"] if negative else display["icon_image"]
    app = {
        "effect": ctx.links.link("effect", effect_key, source=source, relation="effect"),
        "scope": opt(scope),
        "scope_text": scope_text(ctx, opt(scope)),
        "value": value,
        "priority": priority,
        "hidden": priority == 0,
        "favourable": favourable,
        "icon_image": icon,
        "source": ctx.links.link(source[0], source[1], source=None, relation="source"),
    }
    app.update(extra)
    return app
```

- In `build`, replace the body of the `for r in ctx.rows("SELECT * FROM effects ORDER BY effect"):` loop with:

```python
            key = r["effect"]
            effect = {
                "key": key,
                "description": ctx.links.name("effect", key),
                "additional_tooltip": ctx.loc.text(
                    f"effects_additional_tooltip_details_localised_description_{key}"),
                "category": r["category"],
                "icon": opt(r["icon"]),
                "icon_negative": opt(r["icon_negative"]),
                "icon_image": ctx.images.resolve("effect.icon_image", r["icon"], EFFECT_ICONS),
                "icon_negative_image": ctx.images.resolve("effect.icon_negative_image", r["icon_negative"], EFFECT_ICONS),
                "priority": r["priority"],
                "is_positive_value_good": r["is_positive_value_good"],
                "bonus_targets": targets.get(key, []),
                "sources": [],
            }
            out["effect"].append(effect)
            ctx.effect_display[key] = {
                "priority": effect["priority"], "is_positive_value_good": effect["is_positive_value_good"],
                "icon_image": effect["icon_image"], "icon_negative_image": effect["icon_negative_image"]}
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `uv run pytest tests/model -q --ignore=tests/model/test_real_build.py`
Expected: all pass. `test_schema_marks_reverse_links_and_conditional_fields_required` still passes because the optional building fields are unchanged.

- [ ] **Step 5: Commit**

```bash
git add twwiki/model tests/model
git commit -m "feat(model): effect scope text, priority, hidden, polarity and icon on applications" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Reference documents

**Files:**
- Create: `twwiki/model/reference.py`
- Modify: `twwiki/model/schemas.py` (reference models)
- Modify: `twwiki/model/build.py` (`write_output`: the `reference/` folder and the manifest `reference` section)
- Test: `tests/model/test_reference.py`, `tests/model/test_build.py`

**Interfaces:**
- Consumes: campaign entities (Task 3) and `ctx.tally` (Task 2).
- Produces:
  - `reference.UI_LABEL_KEYS: dict[str, str]`
  - `reference.dark_hex(hex_value: str) -> str`
  - `reference.build_reference(ctx, entities) -> dict[str, list | dict]`
  - Files `reference/campaigns.json`, `reference/colours.json` and `reference/ui_labels.json`.
  - Manifest `reference: {name: entry count}`.
  - Document shapes, as read by the web app:
    - campaigns: `[{key, name, map, playable_factions: int, major_factions: int}]`
    - colours: `[{key, description, hex: "#RRGGBB", dark_hex: "#RRGGBB", profiles: {deuteranopia, protanopia, tritanopia}}]`
    - ui_labels: `{name: text | null}`

- [ ] **Step 1: Write the failing tests.** Create `tests/model/test_reference.py`:

```python
import pytest

from twwiki.model import reference
from tests.model.fixtures import make_context


@pytest.mark.parametrize("value, expected", [
    ("#999999", "#999999"),   # lightness exactly 60%: unchanged
    ("#989898", "#999999"),   # just under 60%: raised
    ("#000080", "#3333FF"),   # navy: same hue and saturation, lightness 60%
    ("#41E1E1", "#41E1E1"),   # already light
])
def test_dark_hex_raises_lightness_to_sixty_percent(value, expected):
    assert reference.dark_hex(value) == expected


def test_build_reference_documents():
    ctx = make_context({
        "ui_colours": [
            {"key": "magic", "description": "Magic text", "unnamed colour group_1": "41e1e1"},
            {"key": "dark_red", "description": "", "unnamed colour group_1": "800000"},
            {"key": "blank", "description": "No colour", "unnamed colour group_1": ""},
        ],
        "ui_colour_profile_colour_overrides": [
            {"colour": "magic", "colour_profile": "deuteranopia", "colour_hex": "364099"},
        ],
    }, loc={
        reference.UI_LABEL_KEYS["duration"]: "Duration:",
        reference.UI_LABEL_KEYS["effects"]: " Effects ",
    })
    campaign = {"key": "wh3_main_combi", "name": "Immortal Empires", "map": "wh3_main_combi_map_5",
                "script_folder": None, "factions": [], "regions": [],
                "playable_factions": [{"type": "faction", "key": "a", "name": None, "missing": False}],
                "major_factions": []}
    docs = reference.build_reference(ctx, {"campaign": [campaign]})

    assert docs["campaigns"] == [{"key": "wh3_main_combi", "name": "Immortal Empires", "map": "wh3_main_combi_map_5",
                                  "playable_factions": 1, "major_factions": 0}]
    assert docs["colours"] == [
        {"key": "dark_red", "description": "", "hex": "#800000", "dark_hex": "#FF3333",
         "profiles": {"deuteranopia": None, "protanopia": None, "tritanopia": None}},
        {"key": "magic", "description": "Magic text", "hex": "#41E1E1", "dark_hex": "#41E1E1",
         "profiles": {"deuteranopia": "#364099", "protanopia": None, "tritanopia": None}},
    ]
    assert docs["ui_labels"]["duration"] == "Duration" and docs["ui_labels"]["effects"] == "Effects"
    assert docs["ui_labels"]["cooldown"] is None
    assert set(docs["ui_labels"]) == set(reference.UI_LABEL_KEYS)
    assert ctx.tally["ui_labels_without_text"] == len(reference.UI_LABEL_KEYS) - 2


def test_reference_documents_are_empty_without_tables():
    ctx = make_context({"dummy": [{"a": 1}]})
    docs = reference.build_reference(ctx, {})
    assert docs["campaigns"] == [] and docs["colours"] == []
```

`#800000`: hue 0, saturation 1, lightness 0.251. At 60% lightness that is RGB (1.0, 0.2, 0.2), or `#FF3333`.

Append to `tests/model/test_build.py`:

```python
def test_write_output_writes_reference_documents(tmp_path):
    ctx = make_context({"dummy": [{"a": 1}]})
    out = build.write_output(ctx, build.build_all(ctx, modules=[fake_module()]), tmp_path, "abc123")
    for name in ("campaigns", "colours", "ui_labels"):
        assert (out / "reference" / f"{name}.json").exists()
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["reference"] == {"campaigns": 0, "colours": 0, "ui_labels": 8}
    assert manifest["ui_labels_without_text"] == 8
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `uv run pytest tests/model/test_reference.py tests/model/test_build.py -q`
Expected: FAIL with `ImportError: cannot import name 'reference'`.

- [ ] **Step 3: Implement.**

`twwiki/model/schemas.py`: add this section at the end of the file:

```python
# ---- Reference documents (model/<build_id>/reference/) ---------------------

class CampaignSummary(Strict):
    key: str
    name: str | None
    map: str | None
    playable_factions: int
    major_factions: int


class ColourProfiles(Strict):
    deuteranopia: str | None
    protanopia: str | None
    tritanopia: str | None


class Colour(Strict):
    key: str
    description: str
    hex: str
    dark_hex: str
    profiles: ColourProfiles
```

Create `twwiki/model/reference.py`:

```python
"""Reference documents written next to the entities: campaigns, UI colours and UI labels."""

from __future__ import annotations

import colorsys

from pydantic import TypeAdapter

from .context import Context, grouped, opt
from .schemas import CampaignSummary, Colour

COLOUR_PROFILES = ("deuteranopia", "protanopia", "tritanopia")
DARK_MIN_LIGHTNESS = 0.6

# Label name -> uied_component_texts loc key for game UI labels the web app shows.
UI_LABEL_KEYS = {
    "abilities": "uied_component_texts_localised_string_tab_title_active_Text_1f005b",
    "cooldown": "uied_component_texts_localised_string_ComponentText_9180a7ac",
    "duration": "uied_component_texts_localised_string_tx_duration_default_Text_130017",
    "effects": "uied_component_texts_localised_string_tx_effects_NewState_Text_770033",
    "range": "uied_component_texts_localised_string_range_NewState_Text_60059",
    "research_rate": "uied_component_texts_localised_string_label_research_rate_NewState_Text_60007",
    "stats": "uied_component_texts_localised_string_dy_title_NewState_Text_41",
    "uses": "uied_component_texts_localised_string_tx_charges_default_Text_20000a",
}

REFERENCE_TYPES: dict[str, TypeAdapter] = {
    "campaigns": TypeAdapter(list[CampaignSummary]),
    "colours": TypeAdapter(list[Colour]),
    "ui_labels": TypeAdapter(dict[str, str | None]),
}


def hex_colour(value) -> str | None:
    value = opt(value)
    return f"#{value.upper()}" if value else None


def dark_hex(hex_value: str) -> str:
    """The colour for a dark background: lightness raised to 60% when it is lower, same hue and saturation."""
    r, g, b = (int(hex_value[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, lightness, s = colorsys.rgb_to_hls(r, g, b)
    if lightness >= DARK_MIN_LIGHTNESS:
        return hex_value
    return "#" + "".join(f"{round(c * 255):02X}" for c in colorsys.hls_to_rgb(h, DARK_MIN_LIGHTNESS, s))


def campaigns_doc(entities: dict[str, list[dict]]) -> list[dict]:
    return [{"key": c["key"], "name": c["name"], "map": c["map"],
             "playable_factions": len(c["playable_factions"]), "major_factions": len(c["major_factions"])}
            for c in entities.get("campaign", [])]


def colours_doc(ctx: Context) -> list[dict]:
    if not ctx.table_exists("ui_colours"):
        return []
    overrides = grouped(ctx, "ui_colour_profile_colour_overrides", "colour", "colour_profile")
    out = []
    for r in ctx.rows('SELECT key, description, "unnamed colour group_1" AS hex FROM ui_colours ORDER BY key'):
        value = hex_colour(r["hex"])
        if value is None:
            continue
        profiles = {o["colour_profile"]: hex_colour(o["colour_hex"]) for o in overrides.get(r["key"], [])}
        out.append({"key": r["key"], "description": r["description"] or "", "hex": value, "dark_hex": dark_hex(value),
                    "profiles": {p: profiles.get(p) for p in COLOUR_PROFILES}})
    return out


def ui_labels_doc(ctx: Context) -> dict[str, str | None]:
    labels: dict[str, str | None] = {}
    for name, key in sorted(UI_LABEL_KEYS.items()):
        text = ctx.loc.text(key)
        text = text.strip().rstrip(":").strip() if text else ""
        if not text:
            ctx.tally["ui_labels_without_text"] += 1
        labels[name] = text or None
    return labels


def build_reference(ctx: Context, entities: dict[str, list[dict]]) -> dict[str, list | dict]:
    docs = {"campaigns": campaigns_doc(entities), "colours": colours_doc(ctx), "ui_labels": ui_labels_doc(ctx)}
    return {name: REFERENCE_TYPES[name].dump_python(REFERENCE_TYPES[name].validate_python(doc), mode="json")
            for name, doc in docs.items()}
```

`twwiki/model/build.py`:
- Add `from .reference import build_reference`.
- Change `for sub in ("entities", "index", "schema", "images"):` to `for sub in ("entities", "index", "schema", "images", "reference"):`.
- After `files_copied = ctx.images.copy_used(staging / "images")`, insert:

```python
    reference_docs = build_reference(ctx, entities)
    for name, doc in reference_docs.items():
        (staging / "reference" / f"{name}.json").write_text(
            json.dumps(round_floats(doc), ensure_ascii=False, indent=1), encoding="utf-8")
```

- In the manifest dict, after `"images": ctx.images.manifest(files_copied),`, add `"reference": {name: len(doc) for name, doc in reference_docs.items()},`.

- [ ] **Step 4: Run the tests to see them pass**

Run: `uv run pytest tests/model tests/publish -q --ignore=tests/model/test_real_build.py`
Expected: all pass. `model_files` in `twwiki/publish/local_model.py` uses `rglob`, so snapshots include `reference/` without changes.

- [ ] **Step 5: Commit**

```bash
git add twwiki/model tests/model
git commit -m "feat(model): campaigns, colours and UI label reference documents" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: Real build checks, baselines and a local rebuild

**Files:**
- Create: `tests/model/regenerate_baselines.py`
- Modify: `tests/model/test_real_build.py`
- Regenerate: `tests/model/missing_links_baseline.json`, `tests/model/missing_images_baseline.json`
- Rebuild (not committed): `model/<build_id>/`

**Interfaces:**
- Consumes: everything from Tasks 1–8.
- Produces: a version 3 model in `model/<build_id>/` for the web tasks, and `MAX_UNNAMED_BUILDING_CHAINS` in the real-build test.

- [ ] **Step 1: Write the new real-build checks.**

In `tests/model/test_real_build.py`:
- Add `import re` and `from twwiki.model.build import build_all, round_floats` (replacing the existing `build_all` import).
- Add `"campaign": 3` to `EXPECTED_COUNTS`.
- In `test_training_field`, replace `assert tf["cultures"] == ["wh_main_emp_empire"]` with `assert "wh_main_emp_empire" in [l["key"] for l in tf["availability"]]`.
- In `test_karl_franz`, add:

```python
    assert {"key": "general", "name": "Lord"} in kf["agent_types"]
    assert [c["key"] for c in kf["campaigns"]] == ["wh3_main_chaos", "wh3_main_combi"]
```

- Append:

```python
# Unnamed building chains left after placeholder text counts as missing; set from the
# first version 3 build. Raise it only after checking the new chains really have no name.
MAX_UNNAMED_BUILDING_CHAINS = 0


def iter_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from iter_strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from iter_strings(v)


def test_campaigns_and_campaign_links(model):
    by_type = model[1]
    assert {k: c["name"] for k, c in by_type["campaign"].items()} == {
        "wh3_main_chaos": "The Realm of Chaos", "wh3_main_combi": "Immortal Empires", "wh3_main_prologue": "The Lost God"}
    combi = by_type["campaign"]["wh3_main_combi"]
    assert len(combi["playable_factions"]) == 104
    assert "wh3_main_combi_region_altdorf" in {r["key"] for r in combi["regions"]}
    assert by_type["region"]["wh3_main_combi_region_altdorf"]["campaign"] == {
        "type": "campaign", "key": "wh3_main_combi", "name": "Immortal Empires", "missing": False}
    assert "wh3_main_combi" in {c["key"] for c in by_type["faction"]["wh_main_emp_empire"]["playable_in"]}


def test_placeholder_names_are_replaced(model):
    by_type = model[1]
    name = by_type["building_chain"]["wh2_dlc09_special_settlement_khemri_tmb"]["name"]
    assert name and name.strip().lower() != "placeholder"
    unnamed = sum(1 for c in by_type["building_chain"].values() if c["name"] is None)
    assert unnamed <= MAX_UNNAMED_BUILDING_CHAINS


def test_item_rarity_and_category(model):
    ghal = model[1]["item"]["wh_main_anc_weapon_ghal_maraz"]
    assert ghal["rarity"] is not None and ghal["rarity"]["key"] == "wh_main_anc_group_unique"
    assert ghal["category"]["key"] == "weapon" and ghal["category"]["name"] == "Weapon"


def iter_dicts(value):
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from iter_dicts(v)
    elif isinstance(value, list):
        for v in value:
            yield from iter_dicts(v)


def test_lords_army_scope_text(model):
    apps = (d for rows in model[1].values() for entity in rows.values() for d in iter_dicts(entity)
            if d.get("scope") == "army_to_army_own" and "scope_text" in d)
    assert any("Lord's army" in (a["scope_text"] or "") for a in apps)


def test_derived_technology_tree_name(model):
    tree = model[1]["technology_tree"]["cth_mil"]
    assert tree["name_derived"] is True and tree["name"].endswith(" Technologies")


def test_no_dead_tokens_placeholders_or_float_artefacts(model):
    by_type = model[1]
    bad = [(t, key, s) for t, rows in by_type.items() for key, entity in rows.items() for s in iter_strings(entity)
           if "{{tt:" in s or "{{Cco" in s or s.strip().lower() == "placeholder"]
    assert bad[:5] == []
    artefact = re.compile(r"\d\.\d*0{5,}\d")
    floats = [(t, key) for t, rows in by_type.items() for key, entity in rows.items()
              if artefact.search(json.dumps(round_floats(entity)))]
    assert floats[:5] == []
```

- [ ] **Step 2: Measure the unnamed chains, then set the threshold.**

Run:

```bash
uv run python -c "from twwiki.model.context import Context; from twwiki.model.build import build_all; ctx = Context.open('twwiki.duckdb'); e = build_all(ctx); print(sum(1 for c in e['building_chain'] if c['name'] is None))"
```

Expected: one integer. Set `MAX_UNNAMED_BUILDING_CHAINS` to that exact number.

Check that the unnamed chains really have no name text (empty or placeholder loc under both `building_chains_encyclopedia_name_` and `building_chains_chain_tooltip_`). Print five of their keys:

```bash
uv run python -c "from twwiki.model.context import Context; from twwiki.model.build import build_all; ctx = Context.open('twwiki.duckdb'); e = build_all(ctx); print([c['key'] for c in e['building_chain'] if c['name'] is None][:5])"
```

Record the count and the sample in the task report.

- [ ] **Step 3: Add the baseline regeneration helper.** Create `tests/model/regenerate_baselines.py`:

```python
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
```

Before running it, save the old baselines so you can compare: `git show HEAD:tests/model/missing_links_baseline.json`. Then run `uv run python -m tests.model.regenerate_baselines` and `git diff tests/model/*baseline.json`.

For every count that rose, write in the task report which change caused it. Expected new keys:
- `difficulty_level.campaign->campaign`: `main_warhammer`-style keys that aren't campaigns.
- `building_level.level_availability->…`
- `campaign_variable.overrides->campaign`, if any.

- [ ] **Step 4: Run the whole Python suite and rebuild the model**

Run: `uv run pytest tests -q`
Expected: all pass, including `tests/model/test_real_build.py`.

Run: `uv run python -m twwiki.model`
Expected: the log ends with `model <build_id> written to model\<build_id>`.

Then run:

```bash
uv run python -c "import json,glob; m=json.load(open(sorted(glob.glob('model/*/manifest.json'))[-1])); print(m['model_version'], m['text'], m['reference'], {k: m[k] for k in ('effect_applications_without_scope_text','unmatched_rarity_scores','unresolved_agent_type_names','campaign_exclusive_permissions_excluded','unresolved_building_availability_keys','ui_labels_without_text')})"
```

Expected: `3`, a `text` section, `reference` with `campaigns: 3`, `colours: 163` and `ui_labels: 8`, and the six counts. Paste the output into the task report.

- [ ] **Step 5: Commit**

```bash
git add tests/model
git commit -m "test(model): real-build checks for area A and regenerated baselines" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---
### Task 10: Web app reads model version 3 (version, reference loader, campaign type, fixtures)

**Files:**
- Modify: `web/src/data/validate.ts`
- Modify: `web/src/data/load.ts`
- Modify: `web/src/data/pageTypes.ts`
- Modify: `web/src/data/browse.ts` (`BROWSE_FIELDS` and value accessors)
- Modify: `web/src/data/searchIndex.ts` (`searchCulture`, `searchCategory`)
- Modify: `web/scripts/make-fixtures.ts`
- Regenerate: `web/test/fixtures/model/`, which includes a new `reference/` folder
- Test:
  - `web/test/unit/validate.test.ts`
  - `web/test/unit/load.test.ts`
  - `web/test/unit/pageTypes.test.ts`
  - `web/test/unit/browse.test.ts`

**Interfaces:**
- Consumes: the version 3 model rebuilt in Task 9. The shapes used are listed in Tasks 3–8.
- Produces:
  - `MODEL_VERSION = 3`
  - `REFERENCE_FILES = ["campaigns", "colours", "ui_labels"]`
  - `Model.reference: Reference`, where `Reference` is `{ campaigns: CampaignSummary[]; colours: ColourEntry[]; ui_labels: Record<string, string | null> }`
  - Page type `campaign` (segment `campaigns`, label `Campaigns`, singular `Campaign`)
  - `BrowseField` is `{ field: string; label: string; value?: (entity) => unknown }`
  - A fixture model containing:
    - all three campaigns
    - a skill with a hidden effect application
    - a skill with an unfavourable one
    - an item with a rarity
    - the chain `wh2_dlc09_special_settlement_khemri_tmb`
    - a technology tree with a campaign-restricted node

- [ ] **Step 1: Regenerate types from the real model**

Run: `cd web && npm run prebuild`
Expected: `prebuild: model <build_id> at …`, then this failure: `prebuild failed: …model_version 3, expected 2…`.

This confirms that the version check gates the prebuild. Types are generated only after Step 3.

- [ ] **Step 2: Write the failing tests.**

`web/test/unit/validate.test.ts`:
- Change `tempModel` so it can create reference files:

```ts
async function tempModel(manifest: object | null, entityTypes: string[], referenceFiles: string[] = []): Promise<string> {
  const dir = await mkdtemp(path.join(tmpdir(), "model-"));
  await mkdir(path.join(dir, "entities"));
  await mkdir(path.join(dir, "reference"));
  if (manifest) await writeFile(path.join(dir, "manifest.json"), JSON.stringify(manifest));
  for (const t of entityTypes) await writeFile(path.join(dir, "entities", `${t}.jsonl`), "");
  for (const r of referenceFiles) await writeFile(path.join(dir, "reference", `${r}.json`), "[]");
  return dir;
}
```

- Change `/model_version 1, expected 2/` to `/model_version 1, expected 3/`.
- In "lists missing entity files", change `model_version: 2` to `model_version: 3`.
- Import `ENTITY_TYPES` from `../../src/data/pageTypes` and append:

```ts
  it("lists missing reference files", async () => {
    const dir = await tempModel({ build_id: "x", model_version: 3, generated_at: "", counts: {} }, [...ENTITY_TYPES], ["campaigns"]);
    await expect(validateModelDir(dir)).rejects.toThrow(/missing reference files: reference\/colours\.json, reference\/ui_labels\.json/);
  });
```

`web/test/unit/pageTypes.test.ts`:
- Rename the first test to `"lists 20 entity types and 16 page types"`.
- Change `toHaveLength(19)` to `toHaveLength(20)`.
- Append `"campaigns"` to the expected segment list, after `"provinces"`.

`web/test/unit/load.test.ts`: in "loads the fixture model", change `toBe(2)` to `toBe(3)` and add:

```ts
    expect(model.reference.campaigns.map((c) => c.key)).toEqual(["wh3_main_chaos", "wh3_main_combi", "wh3_main_prologue"]);
    expect(model.reference.colours.find((c) => c.key === "magic")?.dark_hex).toMatch(/^#[0-9A-F]{6}$/);
    expect(model.reference.ui_labels.duration).toBe("Duration");
    expect(model.entities.campaign.size).toBe(3);
```

`web/test/unit/browse.test.ts`: append to `describe("browseRows")`:

```ts
  it("shows labels, not objects, for label fields", () => {
    const rows = browseRows(site, "character");
    const karl = rows.find((r) => r.key === "wh_main_emp_karl_franz")!;
    expect(karl.values[BROWSE_FIELDS.character.findIndex((f) => f.field === "agent_types")]).toBe("Lord");
    const item = browseRows(site, "item")[0];
    expect(item.values.join(" ")).not.toContain("[object Object]");
  });
```

- [ ] **Step 3: Implement.**

`web/src/data/validate.ts`:
- Set `MODEL_VERSION = 3` and add `export const REFERENCE_FILES = ["campaigns", "colours", "ui_labels"] as const;`.
- After the entity-file check, add:

```ts
  const missingReference: string[] = [];
  for (const name of REFERENCE_FILES) {
    try {
      await access(path.join(dir, "reference", `${name}.json`));
    } catch {
      missingReference.push(`reference/${name}.json`);
    }
  }
  if (missingReference.length) throw new ModelLoadError(`${dir}: missing reference files: ${missingReference.join(", ")}`);
```

`web/src/data/load.ts`:
- Add the interfaces:

```ts
export interface CampaignSummary {
  key: string;
  name: string | null;
  map: string | null;
  playable_factions: number;
  major_factions: number;
}

export interface ColourEntry {
  key: string;
  description: string;
  hex: string;
  dark_hex: string;
  profiles: Record<"deuteranopia" | "protanopia" | "tritanopia", string | null>;
}

export interface Reference {
  campaigns: CampaignSummary[];
  colours: ColourEntry[];
  ui_labels: Record<string, string | null>;
}
```

- Add `reference: Reference;` to `Model`.
- Add this function and use it in `loadModel`:

```ts
async function readReference(dir: string): Promise<Reference> {
  const read = async (name: string) => {
    const file = path.join(dir, "reference", `${name}.json`);
    try {
      return JSON.parse(await readFile(file, "utf-8"));
    } catch (e) {
      throw new ModelLoadError(`${file}: missing or invalid (${(e as Error).message})`);
    }
  };
  return { campaigns: await read("campaigns"), colours: await read("colours"), ui_labels: await read("ui_labels") };
}
```

- Change the return to `return { dir, manifest, inline, reference: await readReference(dir), entities: … };`.

`web/src/data/pageTypes.ts`:
- Add `"campaign"` to the end of the `EntityType` union and the end of `ENTITY_TYPES`.
- Append `{ type: "campaign", segment: "campaigns", label: "Campaigns", singular: "Campaign" },` to `PAGE_TYPES`.

`web/src/data/browse.ts`:
- Add `export interface BrowseField { field: string; label: string; value?: (entity: Record<string, any>) => unknown }` and type `BROWSE_FIELDS` as `Record<PageType, BrowseField[]>`.
- Change these entries:

```ts
  character: [
    { field: "agent_types", label: "Agent types", value: (e) => e.agent_types.map((a: { key: string; name: string | null }) => a.name ?? a.key) },
    { field: "is_caster", label: "Caster" },
  ],
  building_level: [{ field: "level", label: "Level" }],
  item: [
    { field: "category", label: "Category", value: (e) => e.category.name ?? e.category.key },
    { field: "legendary", label: "Legendary" },
  ],
  region: [
    { field: "is_settlement", label: "Settlement" },
    { field: "template_source", label: "Templates" },
  ],
  province: [],
  campaign: [],
```

- In `browseRows`, change the values line to `values: fields.map((f) => cellText(f.value ? f.value(entity) : entity[f.field])),`.

`web/src/data/searchIndex.ts`:
- In `searchCulture`, replace the `building_level` case with:

```ts
    case "building_level":
      return cultureNames(site, (e.availability ?? []).filter((l: { type: string }) => l.type === "culture").map((l: { key: string }) => l.key));
```

- In `searchCategory`, split `item` from `building_chain`:

```ts
    case "item":
      return e.category?.name ?? e.category?.key ?? "";
    case "building_chain":
      return e.category ?? "";
```

`web/scripts/make-fixtures.ts`:
- After `add("faction", "wh_main_emp_empire");`, add:

```ts
  for (const key of all.campaign.keys()) add("campaign", key);
  add("building_chain", "wh2_dlc09_special_settlement_khemri_tmb");
  const firstWith = (type: EntityType, test: (row: Row) => boolean, what: string): Row => {
    for (const row of all[type].values()) if (test(row)) return add(type, row.key);
    throw new Error(`the model has no ${type} with ${what}`);
  };
  const skillApps = (s: Row) => s.levels.flatMap((l: Row) => l.effects);
  firstWith("skill", (s) => skillApps(s).some((a: Row) => a.hidden), "a hidden effect");
  firstWith("skill", (s) => skillApps(s).some((a: Row) => a.favourable === false), "an unfavourable effect");
  firstWith("item", (i) => i.rarity !== null && i.rarity.colour !== null, "a coloured rarity");
  const restricted = firstWith("technology_tree", (t) => t.nodes.some((n: Row) => n.campaigns.length > 0), "a campaign-restricted node");
  for (const node of restricted.nodes) add("technology", node.technology.key);
```

- After the `cp(... "schema" ...)` line, add `await cp(path.join(source, "reference"), path.join(outDir, "reference"), { recursive: true });`.

- [ ] **Step 4: Generate types and fixtures, then run the tests**

Run: `cd web && npm run prebuild && npm run fixtures && npm test`

Expected:
- The prebuild succeeds (`prebuild: search index … MB`).
- The fixtures step prints `counts`.
- Vitest fails only in `load.test.ts` sizes (`skill`, `technology`, `region`, `building_level`), and in `search.test.ts` or `regionCultures.test.ts` if fixture contents moved.

Update the size numbers in `load.test.ts` to the `counts` the fixtures script printed. For any other failure, read the assertion: if it pinned a fixture count that legitimately grew, update the number; otherwise fix the code. Re-run `npm test` until it passes.

- [ ] **Step 5: Commit**

```bash
git add web/src web/scripts web/test
git commit -m "feat(web): read model version 3, reference documents and the campaign type" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 11: Generated game colour CSS

**Files:**
- Create: `web/src/lib/coloursCss.ts`
- Modify: `web/scripts/prebuild.ts` (write `src/generated/colours.css`)
- Modify: `web/src/styles/theme.css` (import generated colours; remove the seven hand-set colours)
- Modify: `web/scripts/build-report.ts` (count unknown colour names)
- Test: `web/test/unit/coloursCss.test.ts`, `web/test/unit/buildReport.test.ts`

**Interfaces:**
- Consumes: `Reference.colours` (Task 10).
- Produces:
  - `colourClassName(key: string): string`, e.g. `gt-col-fe-white`.
  - `colourVariable(key: string): string`, e.g. `--col-fe-white`.
  - `coloursCss(colours: { key: string; dark_hex: string }[]): string`
  - The file `src/generated/colours.css`.
  - `DistSummary.unknownColours: number`

- [ ] **Step 1: Write the failing tests.** Create `web/test/unit/coloursCss.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { colourClassName, colourVariable, coloursCss } from "../../src/lib/coloursCss";

describe("coloursCss", () => {
  it("names classes and variables from lower-cased, hyphenated keys", () => {
    expect(colourClassName("Ancillary_Rare")).toBe("gt-col-ancillary-rare");
    expect(colourVariable("fe_white")).toBe("--col-fe-white");
  });

  it("writes one variable and one rule per colour, sorted by key, using the dark-background hex", () => {
    expect(coloursCss([{ key: "red", dark_hex: "#FF3333" }, { key: "fe_white", dark_hex: "#F4EFE4" }])).toBe(
      "/* Generated from reference/colours.json by scripts/prebuild.ts. Do not edit. */\n" +
        ":root {\n  --col-fe-white: #F4EFE4;\n  --col-red: #FF3333;\n}\n" +
        ".gt-col-fe-white { color: var(--col-fe-white); }\n.gt-col-red { color: var(--col-red); }\n",
    );
  });
});
```

In `web/test/unit/buildReport.test.ts`:
- Change the `units/b` page to `'<span data-placeholder-image></span><span class="gt-col" data-unknown-colour="blue">x</span>'`.
- Add `expect(summary.unknownColours).toBe(1);`.

- [ ] **Step 2: Run the tests to see them fail**

Run: `cd web && npx vitest run test/unit/coloursCss.test.ts test/unit/buildReport.test.ts`
Expected: FAIL. The module is not found, and `unknownColours` is `undefined`.

- [ ] **Step 3: Implement.**

Create `web/src/lib/coloursCss.ts`:

```ts
/** CSS for game text colours ([[col:…]]), generated from reference/colours.json by the prebuild. */
export interface ColourDefinition {
  key: string;
  dark_hex: string;
}

function slug(key: string): string {
  return key.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

export function colourClassName(key: string): string {
  return `gt-col-${slug(key)}`;
}

export function colourVariable(key: string): string {
  return `--col-${slug(key)}`;
}

export function coloursCss(colours: ColourDefinition[]): string {
  const sorted = [...colours].sort((a, b) => a.key.localeCompare(b.key));
  const variables = sorted.map((c) => `  ${colourVariable(c.key)}: ${c.dark_hex};`).join("\n");
  const rules = sorted.map((c) => `.${colourClassName(c.key)} { color: var(${colourVariable(c.key)}); }`).join("\n");
  return `/* Generated from reference/colours.json by scripts/prebuild.ts. Do not edit. */\n:root {\n${variables}\n}\n${rules}\n`;
}
```

`web/scripts/prebuild.ts`:
- Add `import { coloursCss } from "../src/lib/coloursCss";`.
- Add this function:

```ts
async function writeColoursCss(modelDir: string): Promise<void> {
  const colours = JSON.parse(await readFile(path.join(modelDir, "reference", "colours.json"), "utf-8"));
  await writeFile(path.join(generatedDir, "colours.css"), coloursCss(colours));
  console.log(`prebuild: ${colours.length} game text colours`);
}
```

- Call `await writeColoursCss(modelDir);` in `prebuild()` right after `await generateTypes(modelDir);`. `generateTypes` empties the generated folder first, so the order matters.

`web/src/styles/theme.css`:
- Insert `@import "../generated/colours.css";` as the first line of the file.
- Delete the seven `--col-*` custom properties from `:root`: `--col-yellow`, `--col-white`, `--col-red`, `--col-green`, `--col-magic`, `--col-fe-white` and `--col-ancillary-unique`.
- Delete the seven `.gt-col-*` rules (`.gt-col-yellow` through `.gt-col-ancillary-unique`).
- Keep `.gt-title` and `.gt-help`.

`web/scripts/build-report.ts`:
- Add `unknownColours: number;` to `DistSummary`, and `let unknownColours = 0;`.
- In the loop, add `unknownColours += (html.match(/data-unknown-colour/g) ?? []).length;`.
- Return it, and print `console.log(\`  ${"unknown colours".padEnd(18)} ${summary.unknownColours}\`);` after the placeholder images line.

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd web && npm run prebuild && npm test`
Expected: `prebuild: 163 game text colours`, and all tests pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/coloursCss.ts web/scripts/prebuild.ts web/scripts/build-report.ts web/src/styles/theme.css web/test/unit/coloursCss.test.ts web/test/unit/buildReport.test.ts
git commit -m "feat(web): generate game text colour CSS from the model's colour reference" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 12: Game text renderer handles every tag

**Files:**
- Modify: `web/src/lib/gameText.ts` (whole file)
- Modify: `web/src/data/site.ts` (`Site.colourKeys`)
- Modify: `web/src/components/GameText.astro`, and `web/src/lib/detailHtml.ts` (`images` helper)
- Test: `web/test/unit/gameText.test.ts`

**Interfaces:**
- Consumes: `colourClassName` (Task 11) and `Reference.colours` (Task 10).
- Produces:
  - `GameNode` span nodes: `{ kind: "span"; tag: string; style: "bold" | "italic" | "colour" | "hidden" | "plain"; colour: string | null; children }`.
  - `GameTextImages.colours?: ReadonlySet<string>`, holding lower-case colour keys.
  - `stripGameMarkup(text: string): string`
  - `Site.colourKeys: Set<string>`

- [ ] **Step 1: Write the failing tests.** In `web/test/unit/gameText.test.ts`:

In the "builds a node tree" test, change the expected span to `{ kind: "span", tag: "b", style: "bold", colour: null, children: [{ kind: "text", text: "x" }] }`.

Replace the tests "renders bold, italic, help and colour tags", "tolerates nesting, mismatched, stray and unclosed tags" and "shows unresolved and unknown tokens as text" with:

```ts
  it("renders bold, italic and colour tags", () => {
    expect(html("[[b]]x[[/b]] [[i]]y[[/i]] [[col:red]]r[[/col]]")).toBe(
      '<strong>x</strong> <em>y</em> <span class="gt-col gt-col-red">r</span>',
    );
    expect(html("[[overridecol:fe_white]]w[[/overridecol]]")).toBe('<span class="gt-col gt-col-fe-white">w</span>');
  });

  it("leaves colours uncoloured and marked when they are not in the colour list", () => {
    const known: GameTextImages = { ...images, colours: new Set(["red"]) };
    expect(renderGameTextHtml("[[col:Red]]a[[/col]][[col:blue]]b[[/col]]", known)).toBe(
      '<span class="gt-col gt-col-red">a</span><span class="gt-col" data-unknown-colour="blue">b</span>',
    );
  });

  it("renders only the inner text of link, tooltip, fragment and unknown tags", () => {
    expect(
      html("[[sl:campaign_armies]]a[[/sl]] [[url:https://x]]b[[/url]] [[tooltip:]]c[[/tooltip]] [[sl_tooltip:t]]d[[/sl_tooltip]] " +
        "[[fragment:f]]e[[/fragment]] [[sl_link:l]]f[[/sl_link]] [[foo:bar]]g[[/foo]] [[baz]]h"),
    ).toBe("a b c d e f g h");
  });

  it("hides text at opacity 0 and shows it otherwise", () => {
    expect(html("x[[opacity:0]]gone[[/opacity]]y[[opacity:0.5]]seen[[/opacity]]")).toBe("xyseen");
  });

  it("closes only the most recent open tag with the same name", () => {
    expect(html("A [[b]][[col:red]]Rampaging[[/col]][[/b]] unit")).toBe(
      'A <strong><span class="gt-col gt-col-red">Rampaging</span></strong> unit',
    );
    expect(html("[[b]]Corrupt Units[[/i]] allows")).toBe("<strong>Corrupt Units allows</strong>");
    expect(html("[[b]]a[[i]]b[[/b]]c")).toBe("<strong>a<em>b</em></strong>c");
    expect(html("[[b]]open")).toBe("<strong>open</strong>");
    expect(html("x[[/b]]y")).toBe("xy");
  });

  it("drops {{…}} tokens", () => {
    expect(html("{{tr:research}}: x {{CcoFoo:bar}}")).toBe(": x ");
  });
```

Add a new `describe` block:

```ts
describe("stripGameMarkup", () => {
  it("removes tags and tokens and keeps the text", () => {
    expect(stripGameMarkup("[[col:ancillary_rare]]Rare[[/col]] {{tt:x}}item")).toBe("Rare item");
  });
});
```

Update the import to `import { type GameTextImages, parseGameText, renderGameTextHtml, stripGameMarkup } from "../../src/lib/gameText";`.

- [ ] **Step 2: Run the tests to see them fail**

Run: `cd web && npx vitest run test/unit/gameText.test.ts`
Expected: FAIL. `stripGameMarkup` is not exported, and the span nodes have no `tag`.

- [ ] **Step 3: Implement.** Replace `web/src/lib/gameText.ts` with:

```ts
/** Game UI markup: [[b]], [[i]], [[col:…]], [[overridecol:…]], [[img:…]], [[opacity:…]], other tags, {{…}}, \n and title||body. */
import { colourClassName } from "./coloursCss";
import { escapeHtml } from "./html";

export type SpanStyle = "bold" | "italic" | "colour" | "hidden" | "plain";

export type GameNode =
  | { kind: "text"; text: string }
  | { kind: "br" }
  | { kind: "img"; target: string }
  | { kind: "span"; tag: string; style: SpanStyle; colour: string | null; children: GameNode[] };

type SpanNode = Extract<GameNode, { kind: "span" }>;

export interface ParsedGameText {
  title: GameNode[] | null;
  body: GameNode[];
}

export interface GameTextImages {
  inline: Record<string, string | null>;
  src: (path: string) => string | null;
  /** Lower-case ui_colours keys. When given, other col: names render uncoloured and marked. */
  colours?: ReadonlySet<string>;
}

// [[/name:arg]] tags, {{…}} tokens, a literal backslash-n, or a real newline.
const TOKEN = /\[\[(\/?)([A-Za-z_]+)(?::([^\]]*))?\]\]|\{\{[^}]*\}\}|\\n|\r?\n/g;

function spanStyle(tag: string, arg: string | undefined): SpanStyle {
  if (tag === "b") return "bold";
  if (tag === "i") return "italic";
  if (tag === "col" || tag === "overridecol") return "colour";
  if (tag === "opacity" && arg !== undefined && arg.trim() !== "" && Number(arg) === 0) return "hidden";
  // sl, sl_link, sl_tooltip, url, tooltip, fragment, opacity > 0 and unknown tags show their inner text.
  return "plain";
}

function parseNodes(text: string): GameNode[] {
  const root: GameNode[] = [];
  const stack: SpanNode[] = [];
  const current = () => (stack.length ? stack[stack.length - 1].children : root);
  const pushText = (value: string) => {
    if (!value) return;
    const nodes = current();
    const last = nodes[nodes.length - 1];
    if (last && last.kind === "text") last.text += value;
    else nodes.push({ kind: "text", text: value });
  };

  let pos = 0;
  for (const match of text.matchAll(TOKEN)) {
    pushText(text.slice(pos, match.index));
    pos = match.index! + match[0].length;
    const [whole, closing, name, arg] = match;
    if (whole.startsWith("{{")) continue;
    if (name === undefined) {
      current().push({ kind: "br" });
      continue;
    }
    const tag = name.toLowerCase();
    if (closing) {
      // Close the most recent open tag with the same name; a close with no match is ignored.
      for (let i = stack.length - 1; i >= 0; i -= 1) {
        if (stack[i].tag === tag) {
          stack.length = i;
          break;
        }
      }
      continue;
    }
    if (tag === "img") {
      if (arg) current().push({ kind: "img", target: arg });
      continue;
    }
    const style = spanStyle(tag, arg);
    const span: SpanNode = { kind: "span", tag, style, colour: style === "colour" ? (arg ?? null) : null, children: [] };
    current().push(span);
    stack.push(span);
  }
  pushText(text.slice(pos));
  return root;
}

export function parseGameText(text: string): ParsedGameText {
  const separator = text.indexOf("||");
  if (separator === -1) return { title: null, body: parseNodes(text) };
  const title = text.slice(0, separator);
  return { title: title.trim() ? parseNodes(title) : null, body: parseNodes(text.slice(separator + 2)) };
}

function renderColour(node: SpanNode, inner: string, images: GameTextImages): string {
  const colour = node.colour?.trim().toLowerCase() ?? "";
  if (!colour) return `<span class="gt-col">${inner}</span>`;
  if (images.colours && !images.colours.has(colour)) {
    return `<span class="gt-col" data-unknown-colour="${escapeHtml(colour)}">${inner}</span>`;
  }
  return `<span class="gt-col ${colourClassName(colour)}">${inner}</span>`;
}

function renderNodes(nodes: GameNode[], images: GameTextImages): string {
  return nodes
    .map((node) => {
      switch (node.kind) {
        case "text":
          return escapeHtml(node.text);
        case "br":
          return "<br>";
        case "img": {
          const imagePath = images.inline[node.target];
          const src = imagePath ? images.src(imagePath) : null;
          return src
            ? `<img class="game-img game-img-inline" src="${escapeHtml(src)}" alt="" loading="lazy" decoding="async">`
            : '<span class="game-img game-img-inline placeholder" data-placeholder-image aria-hidden="true"></span>';
        }
        case "span": {
          if (node.style === "hidden") return "";
          const inner = renderNodes(node.children, images);
          if (node.style === "bold") return `<strong>${inner}</strong>`;
          if (node.style === "italic") return `<em>${inner}</em>`;
          if (node.style === "plain") return inner;
          return renderColour(node, inner, images);
        }
      }
    })
    .join("");
}

export function renderGameTextHtml(text: string | null | undefined, images: GameTextImages): string {
  if (!text) return "";
  const { title, body } = parseGameText(text);
  const bodyHtml = renderNodes(body, images);
  return title ? `<span class="gt-title">${renderNodes(title, images)}</span>${bodyHtml}` : bodyHtml;
}

/** Plain text for places that can't show markup: tags and {{…}} tokens removed. */
export function stripGameMarkup(text: string): string {
  return text.replace(/\[\[[^\]]*\]\]|\{\{[^}]*\}\}/g, "").replace(/\s+/g, " ").trim();
}
```

`web/src/data/site.ts`:
- Add `colourKeys: Set<string>;` to `Site`.
- In `createSite`, return `colourKeys: new Set(model.reference.colours.map((c) => c.key.toLowerCase())),` next to `images`.

`web/src/components/GameText.astro`: pass `colours: site.colourKeys` in the options object.

`web/src/lib/detailHtml.ts`: change `images(site)` to return `{ inline: site.model.inline, src: (p: string) => imageSrc(site, p), colours: site.colourKeys }`.

In `web/test/unit/search.test.ts`, `minimalSite` builds a `Site` by hand. Add `colourKeys: new Set(),` to its object.

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd web && npm test`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add web/src web/test
git commit -m "feat(web): render every game text tag and generated colours" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 13: Game value display rules and UI labels on the ability page

**Files:**
- Create: `web/src/lib/gameValue.ts`, `web/src/data/uiLabels.ts`
- Modify: `web/src/components/StatTable.astro` (per-row formatter)
- Modify: `web/src/components/pages/AbilityPage.astro` (activation rows)
- Test: `web/test/unit/gameValue.test.ts`

**Interfaces:**
- Consumes: `Reference.ui_labels` (Task 10).
- Produces:
  - `type GameValueFormat = (value: number) => string | null`
  - `formatRange`, `formatDuration`, `formatUses` and `hideIfZero`
  - `uiLabel(site: Site, name: string, fallback: string): string`
  - `StatTable` rows are `[label, value]` or `[label, value, GameValueFormat]`

- [ ] **Step 1: Write the failing tests.** Create `web/test/unit/gameValue.test.ts`:

```ts
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadModel } from "../../src/data/load";
import { createSite } from "../../src/data/site";
import { uiLabel } from "../../src/data/uiLabels";
import { formatDuration, formatRange, formatUses, hideIfZero } from "../../src/lib/gameValue";

describe("game value display rules", () => {
  it("formats ranges: negative is unlimited, zero hides the row", () => {
    expect(formatRange(-1)).toBe("∞");
    expect(formatRange(0)).toBeNull();
    expect(formatRange(35)).toBe("35");
  });

  it("formats durations: zero or less is unlimited", () => {
    expect(formatDuration(-1)).toBe("∞");
    expect(formatDuration(0)).toBe("∞");
    expect(formatDuration(12.5)).toBe("12.5s");
  });

  it("formats uses: negative hides the row", () => {
    expect(formatUses(-1)).toBeNull();
    expect(formatUses(0)).toBe("0");
    expect(formatUses(3)).toBe("3");
  });

  it("hides zero", () => {
    expect(hideIfZero(0)).toBeNull();
    expect(hideIfZero(0.25)).toBe("0.25");
  });
});

describe("uiLabel", () => {
  it("uses the game label and falls back when there is none", async () => {
    const site = await createSite(await loadModel(path.resolve(__dirname, "../fixtures/model")));
    expect(uiLabel(site, "duration", "Fallback")).toBe("Duration");
    expect(uiLabel(site, "not_a_label", "Fallback")).toBe("Fallback");
  });
});
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `cd web && npx vitest run test/unit/gameValue.test.ts`
Expected: FAIL, because the modules are not found.

- [ ] **Step 3: Implement.**

Create `web/src/lib/gameValue.ts`:

```ts
/** Display rules for raw game values. Each returns the text to show, or null to hide the row. */
import { formatNumber } from "./effectText";

export type GameValueFormat = (value: number) => string | null;

export const formatRange: GameValueFormat = (v) => (v < 0 ? "∞" : v === 0 ? null : formatNumber(v));
export const formatDuration: GameValueFormat = (v) => (v <= 0 ? "∞" : `${formatNumber(v)}s`);
export const formatUses: GameValueFormat = (v) => (v < 0 ? null : formatNumber(v));
export const hideIfZero: GameValueFormat = (v) => (v === 0 ? null : formatNumber(v));
```

Create `web/src/data/uiLabels.ts`:

```ts
import type { Site } from "./site";

/** A game UI label from reference/ui_labels.json, or the fallback when the game has no text for it. */
export function uiLabel(site: Site, name: string, fallback: string): string {
  return site.model.reference.ui_labels[name] ?? fallback;
}
```

Replace the frontmatter and markup of `web/src/components/StatTable.astro` with:

```astro
---
import { formatNumber } from "../lib/effectText";
import type { GameValueFormat } from "../lib/gameValue";

type Value = string | number | boolean | null | undefined;

interface Props {
  rows: ([string, Value] | [string, Value, GameValueFormat])[];
}

const display = (value: string | number | boolean) =>
  typeof value === "number" ? formatNumber(value) : typeof value === "boolean" ? (value ? "Yes" : "No") : value;
const shown = Astro.props.rows.flatMap(([label, value, format]) => {
  if (value === null || value === undefined || value === "") return [];
  if (format && typeof value === "number") {
    const text = format(value);
    return text === null ? [] : [[label, text] as const];
  }
  return [[label, display(value)] as const];
});
---
{shown.length > 0 && (
  <table class="stats">
    <tbody>
      {shown.map(([label, text]) => (
        <tr><th scope="row">{label}</th><td>{text}</td></tr>
      ))}
    </tbody>
  </table>
)}
```

`web/src/components/pages/AbilityPage.astro`:
- Import `uiLabel` from `../../data/uiLabels` and `{ formatDuration, formatRange, formatUses, hideIfZero }` from `../../lib/gameValue`.
- Replace the Activation rows from `["Active time", …]` through `["Miscast chance", …]` with:

```astro
      [uiLabel(site, "duration", "Duration"), act.active_time, formatDuration],
      [uiLabel(site, "cooldown", "Cooldown"), act.recharge_time, hideIfZero],
      ["Initial cooldown", act.initial_recharge, hideIfZero],
      [uiLabel(site, "uses", "Uses"), act.num_uses, formatUses],
      [uiLabel(site, "range", "Range"), act.effect_range, formatRange],
      ["Minimum range", act.min_range, hideIfZero],
      ["Mana cost", act.mana_cost, hideIfZero],
      ["Wind-up time", act.wind_up_time, hideIfZero],
      ["Miscast chance", act.miscast_chance, hideIfZero],
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd web && npm test`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add web/src web/test
git commit -m "feat(web): game value display rules and game UI labels on ability pages" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 14: Effect lists — scope text, polarity and hidden effects

**Files:**
- Modify: `web/src/lib/detailHtml.ts` (`effectsHtml` becomes the only effect-list renderer; new `campaignNoteHtml`; `technologyDetailHtml` shows node campaigns)
- Modify: `web/src/lib/effectText.ts` (remove `scopeLabel`; add `polarityClass`)
- Modify: `web/src/components/EffectList.astro` (render through `effectsHtml`)
- Modify: `web/src/data/trees.ts` (skill tree node panels show the node's campaign)
- Modify: `web/src/styles/theme.css` (effect styles)
- Test: `web/test/unit/detailHtml.test.ts`, `web/test/unit/effectText.test.ts`

**Interfaces:**
- Consumes: the `EffectApplication` fields from Task 7 and `Site.colourKeys` (Task 12).
- Produces:
  - `export interface EffectApplicationRef { effect: { key: string }; scope_text: string | null; value: number; hidden: boolean; favourable: boolean | null; icon_image: string | null; value_damaged?: number | null; value_ruined?: number | null; context_requirement?: string | null; advancement_stage?: string | null }`
  - `effectsHtml(site, applications, options?: { icons?: boolean }): string`
  - `polarityClass(favourable: boolean | null | undefined): "fx-good" | "fx-bad" | null`
  - `campaignNoteHtml(site, campaigns: { key: string; name: string | null }[]): string`, which returns `""` for an empty list, otherwise `<p class="muted campaign-note">Only in <a href="/campaigns/…/">Name</a> · …</p>`

- [ ] **Step 1: Write the failing tests.**

`web/test/unit/effectText.test.ts`:
- Change the import to `import { formatEffect, formatNumber, polarityClass, signed } from "../../src/lib/effectText";`.
- Replace the `describe("scopeLabel", …)` block with:

```ts
describe("polarityClass", () => {
  it("colours favourable and unfavourable values and leaves others neutral", () => {
    expect(polarityClass(true)).toBe("fx-good");
    expect(polarityClass(false)).toBe("fx-bad");
    expect(polarityClass(null)).toBeNull();
    expect(polarityClass(undefined)).toBeNull();
  });
});
```

Create `web/test/unit/detailHtml.test.ts`:

```ts
import path from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import { loadModel } from "../../src/data/load";
import { type Site, createSite } from "../../src/data/site";
import { type EffectApplicationRef, campaignNoteHtml, effectsHtml } from "../../src/lib/detailHtml";

let site: Site;

beforeAll(async () => {
  site = await createSite(await loadModel(path.resolve(__dirname, "../fixtures/model")));
});

const app = (o: Partial<EffectApplicationRef>): EffectApplicationRef => ({
  effect: { key: "not_in_model" }, scope_text: null, value: 5, hidden: false, favourable: null, icon_image: null, ...o,
});

describe("effectsHtml", () => {
  it("marks polarity, shows scope text and sets hidden effects aside", () => {
    const html = effectsHtml(site, [
      app({ favourable: true, scope_text: "([[b]]Lords army[[/b]])" }),
      app({ favourable: false, value: -5 }),
      app({ hidden: true }),
      app({ hidden: true, value: 0 }),
    ]);
    expect(html).toContain(
      '<span class="effect-text fx-good">not_in_model (+5)</span><span class="effect-scope">(<strong>Lords army</strong>)</span>',
    );
    expect(html).toContain('<span class="effect-text fx-bad">not_in_model (-5)</span>');
    expect(html.match(/<li>/g)).toHaveLength(4);
    expect(html).toContain(
      '<details class="hidden-effects"><summary>Hidden effects (2)</summary><p class="muted">The game does not display these effects.</p>',
    );
    expect(html.indexOf("fx-bad")).toBeLessThan(html.indexOf("<details"));
  });

  it("renders nothing without applications and no disclosure without hidden effects", () => {
    expect(effectsHtml(site, [])).toBe("");
    expect(effectsHtml(site, [app({})])).not.toContain("<details");
    expect(effectsHtml(site, [app({})])).toContain('<span class="effect-text">');
  });

  it("adds icons only when asked", () => {
    expect(effectsHtml(site, [app({})], { icons: true })).toContain("game-img game-img-icon placeholder");
    expect(effectsHtml(site, [app({})])).not.toContain("game-img");
  });

  it("notes and links the campaigns a tree node is limited to", () => {
    expect(campaignNoteHtml(site, [])).toBe("");
    expect(campaignNoteHtml(site, [{ key: "wh3_main_chaos", name: "The Realm of Chaos" }])).toBe(
      '<p class="muted campaign-note">Only in <a href="/campaigns/wh3_main_chaos/">The Realm of Chaos</a></p>',
    );
  });

  it("keeps building notes", () => {
    const html = effectsHtml(site, [app({ value_damaged: 2, value_ruined: 0, context_requirement: "port", advancement_stage: "start_turn" })]);
    expect(html).toContain("damaged 2");
    expect(html).toContain("ruined 0");
    expect(html).toContain("when port");
    expect(html).toContain("start turn");
  });
});
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `cd web && npx vitest run test/unit/detailHtml.test.ts test/unit/effectText.test.ts`
Expected: FAIL. `polarityClass` is not exported, and the output has no `effect-text` class.

- [ ] **Step 3: Implement.**

`web/src/lib/effectText.ts`:
- Delete `scopeLabel`.
- Append:

```ts
export function polarityClass(favourable: boolean | null | undefined): "fx-good" | "fx-bad" | null {
  return favourable === true ? "fx-good" : favourable === false ? "fx-bad" : null;
}
```

`web/src/lib/detailHtml.ts`:
- Change the imports to `import { formatEffect, formatNumber, polarityClass } from "./effectText";`.
- Replace `ApplicationRef` and `effectsHtml` with:

```ts
export interface EffectApplicationRef {
  effect: { key: string };
  scope_text: string | null;
  value: number;
  hidden: boolean;
  favourable: boolean | null;
  icon_image: string | null;
  value_damaged?: number | null;
  value_ruined?: number | null;
  context_requirement?: string | null;
  advancement_stage?: string | null;
}

const note = (text: string) => `<span class="muted effect-note">${escapeHtml(text)}</span>`;

function iconHtml(site: Site, imagePath: string | null): string {
  const src = imageSrc(site, imagePath);
  return src
    ? `<img class="game-img game-img-icon" src="${escapeHtml(src)}" alt="" loading="lazy" decoding="async">`
    : '<span class="game-img game-img-icon placeholder" data-placeholder-image aria-hidden="true"></span>';
}

function effectItemHtml(site: Site, a: EffectApplicationRef, icons: boolean): string {
  const effect = site.model.entities.effect.get(a.effect.key);
  const text = renderGameTextHtml(formatEffect(effect?.description ?? null, a.effect.key, a.value), images(site));
  const polarity = polarityClass(a.favourable);
  const parts = [
    icons ? iconHtml(site, a.icon_image) : "",
    `<span class="${polarity ? `effect-text ${polarity}` : "effect-text"}">${text}</span>`,
  ];
  if (a.scope_text) parts.push(`<span class="effect-scope">${renderGameTextHtml(a.scope_text, images(site))}</span>`);
  if (a.value_damaged != null) parts.push(note(`damaged ${formatNumber(a.value_damaged)}`));
  if (a.value_ruined != null) parts.push(note(`ruined ${formatNumber(a.value_ruined)}`));
  if (a.context_requirement) parts.push(note(`when ${a.context_requirement}`));
  if (a.advancement_stage) parts.push(note(a.advancement_stage.replace(/_/g, " ")));
  return `<li>${parts.join("")}</li>`;
}

/** Effect lines as the game shows them; priority-0 effects go in a closed "Hidden effects" disclosure. */
export function effectsHtml(site: Site, applications: EffectApplicationRef[], { icons = false }: { icons?: boolean } = {}): string {
  if (!applications.length) return "";
  const list = (apps: EffectApplicationRef[]) =>
    `<ul class="effect-list">${apps.map((a) => effectItemHtml(site, a, icons)).join("")}</ul>`;
  const visible = applications.filter((a) => !a.hidden);
  const hidden = applications.filter((a) => a.hidden);
  let html = visible.length ? list(visible) : "";
  if (hidden.length) {
    html +=
      `<details class="hidden-effects"><summary>Hidden effects (${hidden.length})</summary>` +
      `<p class="muted">The game does not display these effects.</p>${list(hidden)}</details>`;
  }
  return html;
}
```

- Import `urlFor` alongside `imageSrc` from `../data/site`, and add:

```ts
/** "Only in <campaign> · <campaign>" for tree nodes limited to some campaigns; empty when unrestricted. */
export function campaignNoteHtml(site: Site, campaigns: { key: string; name: string | null }[]): string {
  if (!campaigns.length) return "";
  const links = campaigns.map((c) => {
    const url = urlFor(site, "campaign", c.key);
    const label = escapeHtml(c.name ?? c.key);
    return url ? `<a href="${escapeHtml(url)}">${label}</a>` : label;
  });
  return `<p class="muted campaign-note">Only in ${links.join(" · ")}</p>`;
}
```

- In `technologyDetailHtml`:
  - Add `campaigns: { key: string; name: string | null }[];` to `TechNodeRef`.
  - After the research points line, add `parts.push(campaignNoteHtml(site, node.campaigns));`.

  `web/src/data/trees.ts` already passes the whole node.

In `web/src/data/trees.ts`:
- Import `campaignNoteHtml` next to `skillDetailHtml`.
- In `skillTreeLayout`, change the node's detail to `detailHtml: skillDetailHtml(site, n.skill.key) + campaignNoteHtml(site, n.campaign ? [n.campaign] : []),`.

Replace `web/src/components/EffectList.astro` with:

```astro
---
import { getSite } from "../data/model";
import { type EffectApplicationRef, effectsHtml } from "../lib/detailHtml";

interface Props {
  applications: EffectApplicationRef[];
}

const site = await getSite();
const html = effectsHtml(site, Astro.props.applications, { icons: true });
---
{html && <Fragment set:html={html} />}
```

Append to `web/src/styles/theme.css`:

```css
.effect-scope { color: var(--muted); }
.fx-good { color: var(--col-green); }
.fx-bad { color: var(--col-red); }
.hidden-effects { margin-top: 0.5rem; }
.hidden-effects summary { cursor: pointer; color: var(--muted); }
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd web && npm test`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add web/src web/test
git commit -m "feat(web): effect scope text, good and bad colouring and hidden effects" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---
### Task 15: Campaigns in the web app — page, badge, browse filter and links

**Files:**
- Create: `web/src/lib/campaignFilter.ts`
- Create: `web/src/components/CampaignBadge.astro`
- Create: `web/src/components/pages/CampaignPage.astro`
- Modify: `web/src/components/pages/registry.ts`
- Modify: `web/src/components/EntityHeader.astro`, and `web/src/pages/[segment]/[slug].astro`
- Modify: `web/src/data/browse.ts` (`BrowseRow.campaigns`)
- Modify: `web/src/pages/[segment]/index.astro`
- Modify: `web/src/islands/BrowseFilter.tsx`
- Modify the pages in `web/src/components/pages/`:
  - `RegionPage.astro`
  - `ProvincePage.astro`
  - `TechnologyTreePage.astro`
  - `BuildingChainPage.astro`
  - `FactionPage.astro`
- Modify: `web/src/styles/theme.css`
- Test: `web/test/unit/campaignFilter.test.ts`, `web/test/unit/browse.test.ts`

**Interfaces:**
- Consumes: campaign fields from Tasks 3–4 and `Reference.campaigns` (Task 10).
- Produces:
  - Constants:
    - `DEFAULT_CAMPAIGN = "wh3_main_combi"`
    - `EVERY_CAMPAIGN = "*"`
    - `CAMPAIGN_FILTER_TYPES: ReadonlySet<string>`, containing faction, character, region, province and technology_tree.
  - Functions:
    - `campaignTag(type, entity): string | null`
    - `campaignMatches(tag, selected): boolean`
    - `campaignRestriction(type, entity, totalCampaigns): CampaignLink[]`
  - `BrowseRow.campaigns: string | null`
  - `EntityHeader` gains a required `entity` prop.
  - `BrowseFilter` gains an optional `campaigns: { key: string; name: string }[]` prop.

- [ ] **Step 1: Write the failing tests.** Create `web/test/unit/campaignFilter.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { campaignMatches, campaignRestriction, campaignTag } from "../../src/lib/campaignFilter";

const combi = { key: "wh3_main_combi", name: "Immortal Empires" };
const chaos = { key: "wh3_main_chaos", name: "The Realm of Chaos" };
const prologue = { key: "wh3_main_prologue", name: "The Lost God" };

describe("campaignTag", () => {
  it("tags factions by start position and other types by campaign, empty meaning every campaign", () => {
    expect(campaignTag("faction", { start_campaigns: [chaos, combi] })).toBe("wh3_main_chaos wh3_main_combi");
    expect(campaignTag("faction", { start_campaigns: [] })).toBe("");
    expect(campaignTag("character", { campaigns: [] })).toBe("*");
    expect(campaignTag("character", { campaigns: [chaos] })).toBe("wh3_main_chaos");
    expect(campaignTag("region", { campaign: combi })).toBe("wh3_main_combi");
    expect(campaignTag("province", { campaign: null })).toBe("*");
    expect(campaignTag("technology_tree", { campaign: null })).toBe("*");
    expect(campaignTag("unit", {})).toBeNull();
  });
});

describe("campaignMatches", () => {
  it("matches a listed campaign or every campaign, and everything when no campaign is selected", () => {
    expect(campaignMatches("wh3_main_chaos wh3_main_combi", "wh3_main_combi")).toBe(true);
    expect(campaignMatches("wh3_main_chaos", "wh3_main_combi")).toBe(false);
    expect(campaignMatches("*", "wh3_main_combi")).toBe(true);
    expect(campaignMatches("", "wh3_main_combi")).toBe(false);
    expect(campaignMatches("", "")).toBe(true);
  });
});

describe("campaignRestriction", () => {
  it("names campaigns only for entities in some but not all campaigns", () => {
    expect(campaignRestriction("character", { campaigns: [chaos, combi] }, 3)).toEqual([chaos, combi]);
    expect(campaignRestriction("character", { campaigns: [chaos, combi, prologue] }, 3)).toEqual([]);
    expect(campaignRestriction("character", { campaigns: [] }, 3)).toEqual([]);
    expect(campaignRestriction("faction", { start_campaigns: [prologue] }, 3)).toEqual([prologue]);
    expect(campaignRestriction("region", { campaign: combi }, 3)).toEqual([combi]);
    expect(campaignRestriction("unit", {}, 3)).toEqual([]);
  });
});
```

Append to `describe("browseRows")` in `web/test/unit/browse.test.ts`:

```ts
  it("tags rows with campaigns for filterable types only", () => {
    const reikland = browseRows(site, "faction").find((r) => r.key === "wh_main_emp_empire")!;
    expect(reikland.campaigns?.split(" ")).toContain("wh3_main_combi");
    expect(browseRows(site, "unit")[0].campaigns).toBeNull();
    expect(browseRows(site, "campaign").map((r) => r.key)).toContain("wh3_main_combi");
  });
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `cd web && npx vitest run test/unit/campaignFilter.test.ts test/unit/browse.test.ts`
Expected: FAIL. The module is not found, and `campaigns` is `undefined`.

- [ ] **Step 3: Implement.**

Create `web/src/lib/campaignFilter.ts`. The browser island imports it, so it must not import Node modules.

```ts
/** Campaign tags on browse rows, the rule the Campaign filter applies, and when a page shows a campaign badge. */
export const DEFAULT_CAMPAIGN = "wh3_main_combi";
export const EVERY_CAMPAIGN = "*";
export const CAMPAIGN_FILTER_TYPES: ReadonlySet<string> = new Set(["faction", "character", "region", "province", "technology_tree"]);

export interface CampaignLink {
  key: string;
  name: string | null;
}

type Entity = Record<string, any>;

function campaignLinks(type: string, entity: Entity): CampaignLink[] {
  if (type === "character") return entity.campaigns ?? [];
  if (type === "faction") return entity.start_campaigns ?? [];
  if (type === "region" || type === "province" || type === "technology_tree") return entity.campaign ? [entity.campaign] : [];
  return [];
}

/**
 * A row's data-campaigns value: space-separated campaign keys, "*" for every campaign, or null
 * for types without the filter. A faction in no start position has an empty tag and only shows under "All".
 */
export function campaignTag(type: string, entity: Entity): string | null {
  if (!CAMPAIGN_FILTER_TYPES.has(type)) return null;
  const keys = campaignLinks(type, entity).map((c) => c.key).join(" ");
  return keys || (type === "faction" ? "" : EVERY_CAMPAIGN);
}

export function campaignMatches(tag: string, selected: string): boolean {
  if (!selected) return true;
  return tag === EVERY_CAMPAIGN || tag.split(" ").includes(selected);
}

/** The campaigns a page badge names: only when the entity is in some, but not all, campaigns. */
export function campaignRestriction(type: string, entity: Entity, totalCampaigns: number): CampaignLink[] {
  const links = campaignLinks(type, entity);
  return links.length > 0 && links.length < totalCampaigns ? links : [];
}
```

Create `web/src/components/CampaignBadge.astro`:

```astro
---
import { getSite } from "../data/model";
import { campaignRestriction } from "../lib/campaignFilter";

interface Props {
  type: string;
  entity: Record<string, any>;
}

const site = await getSite();
const campaigns = campaignRestriction(Astro.props.type, Astro.props.entity, site.model.entities.campaign.size);
---
{campaigns.length > 0 && <p class="campaign-badge">{campaigns.map((c) => c.name ?? c.key).join(" · ")}</p>}
```

Create `web/src/components/pages/CampaignPage.astro`:

```astro
---
import { getSite } from "../../data/model";
import LinkList from "../LinkList.astro";
import Section from "../Section.astro";
import StatTable from "../StatTable.astro";

interface Props {
  entityKey: string;
}

const site = await getSite();
const campaign = site.model.entities.campaign.get(Astro.props.entityKey)!;
---
<Section title="Overview">
  <StatTable rows={[
    ["Map", campaign.map],
    ["Factions", campaign.factions.length],
    ["Regions", campaign.regions.length],
  ]} />
</Section>
<Section title="Playable factions" show={campaign.playable_factions.length > 0}><LinkList links={campaign.playable_factions} /></Section>
<Section title="Major factions" show={campaign.major_factions.length > 0}><LinkList links={campaign.major_factions} /></Section>
<Section title="Regions" show={campaign.regions.length > 0}><LinkList links={campaign.regions} /></Section>
```

`web/src/components/pages/registry.ts`: import `CampaignPage` and add `campaign: CampaignPage,` to `PAGE_BODIES`.

`web/src/components/EntityHeader.astro`:
- Import `CampaignBadge from "./CampaignBadge.astro"`.
- Add `entity: Record<string, any>;` to `Props` and to the destructuring.
- Render `<CampaignBadge type={type} entity={entity} />` between the `<h1>` and the `entity-meta` paragraph.

`web/src/pages/[segment]/[slug].astro`: pass `entity={entity}` to `EntityHeader`.

`web/src/data/browse.ts`:
- Import `{ campaignTag }` from `../lib/campaignFilter`.
- Add `campaigns: string | null;` to `BrowseRow`.
- Set `campaigns: campaignTag(type, entity),` in `browseRows`.

`web/src/pages/[segment]/index.astro`:
- Import `{ CAMPAIGN_FILTER_TYPES }` from `../../lib/campaignFilter`.
- After `const filters = …`, add:

```ts
const campaigns = CAMPAIGN_FILTER_TYPES.has(type)
  ? site.model.reference.campaigns.map((c) => ({ key: c.key, name: c.name ?? c.key }))
  : [];
```

- Pass `campaigns={campaigns}` to `BrowseFilter`, and add `data-campaigns={row.campaigns ?? undefined}` to each `<tr>`.

`web/src/islands/BrowseFilter.tsx`:
- Import `{ DEFAULT_CAMPAIGN, EVERY_CAMPAIGN, campaignMatches }` from `../lib/campaignFilter`.
- Add `campaigns?: { key: string; name: string }[];` to `Props` and destructure it as `campaigns = []`.
- Add state: `const [campaign, setCampaign] = useState(campaigns.some((c) => c.key === DEFAULT_CAMPAIGN) ? DEFAULT_CAMPAIGN : "");`.
- In the row loop, change `matches` to:

```ts
        const matches =
          (!needle || (row.dataset.search ?? "").includes(needle)) &&
          (!campaigns.length || campaignMatches(row.dataset.campaigns ?? EVERY_CAMPAIGN, campaign)) &&
          Object.entries(selected).every(([index, value]) => !value || row.getAttribute(`data-f${index}`) === value);
```

- Change the effect dependencies to `[debouncedText, selected, campaign, campaigns.length, tableId]`.
- Render the campaign select before `{filters.map(…)}`:

```tsx
      {campaigns.length > 0 && (
        <label>
          Campaign{" "}
          <select value={campaign} onChange={(e) => setCampaign(e.target.value)}>
            <option value="">All</option>
            {campaigns.map((c) => (
              <option key={c.key} value={c.key}>{c.name}</option>
            ))}
          </select>
        </label>
      )}
```

Page links:
- `RegionPage.astro`: remove `["Campaign", region.campaign],` from the stat rows. Add `{region.campaign && <p>Campaign: <EntityLink link={region.campaign} /></p>}` before the province line.
- `ProvincePage.astro`: change the rows to `[["Regions", province.regions.length]]`. Add `{province.campaign && <p>Campaign: <EntityLink link={province.campaign} /></p>}`.
- `TechnologyTreePage.astro`: change the rows to `[["Technologies", tree.nodes.length]]`. Add `{tree.campaign && <p>Campaign: <EntityLink link={tree.campaign} /></p>}`.
- `BuildingChainPage.astro`: change the campaign cell to `<td><EntityLink link={a.campaign} /></td>`.
- `FactionPage.astro`: after the subculture line in Overview, add:

```astro
  {faction.start_campaigns.length > 0 && (
    <p>Starts in: {faction.start_campaigns.map((c, i) => <>{i > 0 && " · "}<EntityLink link={c} showIcon={false} /></>)}</p>
  )}
  {faction.playable_in.length > 0 && (
    <p>Playable in: {faction.playable_in.map((c, i) => <>{i > 0 && " · "}<EntityLink link={c} showIcon={false} /></>)}</p>
  )}
```

Append to `web/src/styles/theme.css`:

```css
.campaign-badge { display: inline-block; margin: 0.3rem 0 0; padding: 0.05rem 0.5rem; border: 1px solid var(--border-accent); color: var(--gold); font-size: 0.8rem; }
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd web && npm test`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add web/src web/test
git commit -m "feat(web): campaign pages, badges, browse filter defaulting to Immortal Empires, and campaign links" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 16: Subtitles and unnamed records

**Files:**
- Create: `web/src/lib/subtitle.ts`
- Modify: `web/src/components/EntityHeader.astro`, and `web/src/pages/[segment]/[slug].astro` (subtitle, unnamed title)
- Modify: `web/src/data/browse.ts`, and `web/src/pages/[segment]/index.astro` (skip unnamed; Details column)
- Modify: `web/src/data/searchIndex.ts`, `web/src/lib/search.ts` and `web/src/islands/SearchBox.tsx` (skip unnamed; subtitle)
- Modify: `web/src/components/LinkList.astro` (subtitles for repeated names)
- Modify: `web/src/lib/regionCultures.ts` (skip unnamed cultures and chains)
- Modify: `web/src/styles/theme.css`
- Test:
  - `web/test/unit/subtitle.test.ts`
  - `web/test/unit/browse.test.ts`
  - `web/test/unit/search.test.ts`
  - `web/test/unit/regionCultures.test.ts`

**Interfaces:**
- Consumes:
  - `stripGameMarkup` (Task 12)
  - `AgentType` and `Rarity` (Task 5)
  - `start_campaigns` (Task 3)
- Produces:
  - `subtitleFor(site: Site, type: string, entity: Record<string, any>): string | null`. This takes `site` as well as `type` and `entity`, because a character's culture comes from its first faction.
  - `repeatedNames(links): Set<string>`
  - `BrowseRow.subtitle: string`; `BrowseRow.unnamed` is removed.
  - `SearchDocument.subtitle: string`, which is stored but not searched.
  - `SearchHit.subtitle: string`

- [ ] **Step 1: Write the failing tests.** Create `web/test/unit/subtitle.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import type { Site } from "../../src/data/site";
import { repeatedNames, subtitleFor } from "../../src/lib/subtitle";

const link = (key: string, name: string | null) => ({ type: "x", key, name, missing: false });
const site = {
  model: { entities: { faction: new Map([["reikland", { key: "reikland", culture: link("emp", "The Empire") }]]) } },
} as unknown as Site;

describe("subtitleFor", () => {
  it("describes units by category", () => {
    expect(subtitleFor(site, "unit", { category_name: "Melee Infantry" })).toBe("Melee Infantry");
  });

  it("describes characters by agent type and the culture of their first faction", () => {
    expect(subtitleFor(site, "character", { agent_types: [{ key: "general", name: "Lord" }], factions: [link("reikland", "Reikland")] }))
      .toBe("Lord · The Empire");
    expect(subtitleFor(site, "character", { agent_types: [], factions: [] })).toBeNull();
  });

  it("describes building levels by chain", () => {
    expect(subtitleFor(site, "building_level", { chain: link("c", "Barracks") })).toBe("Barracks");
  });

  it("describes items by rarity and category, without markup", () => {
    expect(subtitleFor(site, "item", {
      rarity: { key: "r", name: "[[col:ancillary_rare]]Rare[[/col]]", colour: "#FFFFFF" },
      category: { key: "weapon", name: "Weapon" },
    })).toBe("Rare · Weapon");
  });

  it("describes factions by culture and start campaigns", () => {
    expect(subtitleFor(site, "faction", {
      culture: link("emp", "The Empire"),
      start_campaigns: [link("a", "Immortal Empires"), link("b", "The Realm of Chaos")],
    })).toBe("The Empire · Immortal Empires · The Realm of Chaos");
  });

  it("describes technology trees by faction, else culture", () => {
    expect(subtitleFor(site, "technology_tree", { faction: link("f", "Wulfhart"), culture: link("c", "The Empire") })).toBe("Wulfhart");
    expect(subtitleFor(site, "technology_tree", { faction: null, culture: link("c", "Grand Cathay") })).toBe("Grand Cathay");
  });

  it("has no subtitle for other types", () => {
    expect(subtitleFor(site, "skill", { key: "s" })).toBeNull();
  });
});

describe("repeatedNames", () => {
  it("finds names used more than once", () => {
    expect(repeatedNames([link("a", "Greatswords"), link("b", "Greatswords"), link("c", "Halberdiers"), link("d", null), null]))
      .toEqual(new Set(["Greatswords"]));
  });
});
```

`web/test/unit/browse.test.ts`: in "lists every entity with URL, name and field values, sorted by name":
- Rename the test to "lists every named entity with URL, name, subtitle and field values, sorted by name".
- Replace `expect(rows).toHaveLength(site.model.entities.unit.size);` with:

```ts
    expect(rows).toHaveLength([...site.model.entities.unit.values()].filter((u) => u.name).length);
```

- After `expect(gs.name).toBe("Greatswords");`, add `expect(gs.subtitle).toBe(site.model.entities.unit.get("wh_main_emp_inf_greatswords")!.category_name);`.

`web/test/unit/search.test.ts`:
- Rename "indexes every entity of every page type" to "indexes every named entity of every page type".
- Change its `expected` to:

```ts
    const expected = PAGE_TYPES.reduce(
      (n, p) => n + [...(site.model.entities[p.type] as Map<string, { name: string | null }>).values()].filter((e) => e.name).length, 0);
```

- In "stores names, URLs and facts", add `expect(gs.subtitle).not.toBe("");`.
- In the `groupResults` test, add `subtitle: ""` to the `hit(...)` object.

`web/test/unit/regionCultures.test.ts`: in "groups a culture's chains by category", change the `toHaveLength` line to:

```ts
    const named = site.chainsByCulture.get("wh_main_emp_empire")!.filter((k) => site.model.entities.building_chain.get(k)!.name);
    expect(all).toHaveLength(named.length);
    expect(all.every((c) => c.name && !/placeholder/i.test(c.name))).toBe(true);
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `cd web && npx vitest run test/unit/subtitle.test.ts test/unit/browse.test.ts test/unit/search.test.ts test/unit/regionCultures.test.ts`
Expected: FAIL. The module is not found, and `subtitle` is `undefined`.

- [ ] **Step 3: Implement.**

Create `web/src/lib/subtitle.ts`:

```ts
/** Short text that tells same-named records apart. */
import type { Site } from "../data/site";
import { stripGameMarkup } from "./gameText";

type Entity = Record<string, any>;
type NamedLink = { key: string; name: string | null } | null | undefined;

function join(parts: (string | null | undefined)[]): string | null {
  const text = parts
    .filter((p): p is string => Boolean(p))
    .map(stripGameMarkup)
    .filter(Boolean)
    .join(" · ");
  return text || null;
}

export function subtitleFor(site: Site, type: string, entity: Entity): string | null {
  switch (type) {
    case "unit":
      return join([entity.category_name]);
    case "character": {
      const first = entity.factions?.[0];
      const faction = first ? site.model.entities.faction.get(first.key) : undefined;
      return join([entity.agent_types?.[0]?.name, faction?.culture?.name]);
    }
    case "building_level":
      return join([entity.chain?.name]);
    case "item":
      return join([entity.rarity?.name, entity.category?.name]);
    case "faction":
      return join([entity.culture?.name, ...(entity.start_campaigns ?? []).map((c: NamedLink) => c?.name)]);
    case "technology_tree":
      return join([entity.faction?.name ?? entity.culture?.name]);
    default:
      return null;
  }
}

/** Names that appear more than once in a list of links. */
export function repeatedNames(links: NamedLink[]): Set<string> {
  const counts = new Map<string, number>();
  for (const link of links) if (link?.name) counts.set(link.name, (counts.get(link.name) ?? 0) + 1);
  return new Set([...counts].filter(([, n]) => n > 1).map(([name]) => name));
}
```

`web/src/components/EntityHeader.astro`:
- Add `subtitle: string | null;` to `Props` and to the destructuring.
- Add `const title = name ?? \`Unnamed ${info.singular.toLowerCase()}\`;`.
- The h1 becomes `<h1 class:list={[{ unnamed: !name }]}>{title}</h1>`.
- Directly under it, add `{subtitle && <p class="entity-subtitle">{subtitle}</p>}`.

`web/src/pages/[segment]/[slug].astro`:
- Import `{ subtitleFor }` from `../../lib/subtitle`.
- Add `const title = name ?? \`Unnamed ${info.singular.toLowerCase()}\`;`.
- Set the Layout props to `title={title}` and `description={\`${info.singular}: ${title} — Total War: WARHAMMER III\`}`.
- Pass `subtitle={subtitleFor(site, type, entity)}` to `EntityHeader`.

`web/src/data/browse.ts`:
- Import `{ subtitleFor }` from `../lib/subtitle`.
- In `BrowseRow`, replace `unnamed: boolean;` with `subtitle: string;`.
- In `browseRows`:
  - Replace `const name: string | null = entity.name ?? null;` with `const name: string | null = entity.name ?? null; if (!name) continue;`.
  - Set `name,` and `subtitle: subtitleFor(site, type, entity) ?? "",`.
  - Delete `unnamed: !name,`.

`web/src/pages/[segment]/index.astro`:
- The header row becomes `<tr><th>Name</th><th>Details</th><th>Key</th>{fields.map((f) => <th>{f.label}</th>)}</tr>`.
- The name cell renders `<span>{row.name}</span>` with no `unnamed` class.
- After the name cell, add `<td>{row.subtitle}</td>`.

`web/src/lib/search.ts`:
- Add `subtitle: string;` to `SearchDocument` and `SearchHit`.
- Add `"subtitle"` to `storeFields`, but not to `fields`.
- In `groupResults`, add `subtitle: result.subtitle ?? "",`.

`web/src/data/searchIndex.ts`:
- Import `{ subtitleFor }` from `../lib/subtitle`.
- In `buildSearchDocuments`, at the top of the inner loop, add `if (!entity.name) continue;`.
- Set `name: entity.name,` and `subtitle: subtitleFor(site, info.type, entity) ?? "",`.

`web/src/islands/SearchBox.tsx`: replace `<span>{item.name}</span>` with:

```tsx
                    <span className="search-hit-text">
                      <span>{item.name}</span>
                      {item.subtitle && <span className="search-hit-subtitle">{item.subtitle}</span>}
                    </span>
```

Replace `web/src/components/LinkList.astro` with:

```astro
---
import { getSite } from "../data/model";
import { repeatedNames, subtitleFor } from "../lib/subtitle";
import EntityLink from "./EntityLink.astro";

type LinkRef = { type: string; key: string; name: string | null; missing: boolean };

interface Props {
  links: (LinkRef | null)[];
}

const site = await getSite();
const links = Astro.props.links.filter((l): l is LinkRef => l !== null);
const repeated = repeatedNames(links);
const entities = site.model.entities as Record<string, Map<string, Record<string, any>>>;
const subtitle = (link: LinkRef) =>
  link.name && repeated.has(link.name) ? subtitleFor(site, link.type, entities[link.type]?.get(link.key) ?? {}) : null;
---
{links.length > 0 && (
  <ul class="link-list">
    {links.map((link) => {
      const sub = subtitle(link);
      return <li><EntityLink link={link} />{sub && <span class="muted link-subtitle"> · {sub}</span>}</li>;
    })}
  </ul>
)}
```

`web/src/lib/regionCultures.ts`:
- In `cultureChoices`:

```ts
  return [...site.model.entities.culture.values()]
    .filter((c) => c.name)
    .map((c) => ({ key: c.key, name: c.name! }))
    .sort((a, b) => a.name.localeCompare(b.name) || a.key.localeCompare(b.key));
```

- In `chainGroups`, after `const chain = …!;`, add `if (!chain.name) continue;` and set `name: chain.name,`.

Append to `web/src/styles/theme.css`:

```css
.entity-subtitle { margin: 0.1rem 0 0; color: var(--text); }
.search-hit-text { display: flex; flex-direction: column; }
.search-hit-subtitle { color: var(--muted); font-size: 0.75rem; }
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd web && npm test`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add web/src web/test
git commit -m "feat(web): subtitles for same-named records; unnamed records left out of lists and search" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 17: Entity page updates (unit, item, building level, character)

**Files:**
- Modify: `web/src/components/pages/UnitPage.astro`
- Modify: `web/src/components/pages/ItemPage.astro`
- Modify: `web/src/components/pages/BuildingLevelPage.astro`
- Modify: `web/src/components/pages/CharacterPage.astro`
- Modify: `web/src/styles/theme.css`

**Interfaces:**
- Consumes:
  - `AgentType`, `ItemCategory` and `Rarity` (Task 5)
  - `BuildingLevel.availability` (Task 6)
  - `stripGameMarkup` (Task 12)
- Produces: page markup that the end-to-end checks in Task 18 look for, including `.item-rarity`.

These are template-only changes. The end-to-end tests in Task 18 cover them, and `npm run build` checks that they render.

- [ ] **Step 1: Unit page.** In `UnitPage.astro`:
- In the frontmatter, add:

```ts
const typeNames = [unit.caste_name ?? unit.caste, unit.category_name ?? unit.category, unit.class_name ?? unit.unit_class];
const typeRows: [string, string | null][] = typeNames.every((n) => n === typeNames[0])
  ? [["Type", typeNames[0]]]
  : [["Caste", typeNames[0]], ["Category", typeNames[1]], ["Class", typeNames[2]]];
```

- In the Overview rows, replace the three rows `["Caste", …]`, `["Category", …]` and `["Class", …]` with `...typeRows,`.
- Delete `["Weapon", melee.key],` from the melee table and `["Weapon", missile.key],` from the missile table.

- [ ] **Step 2: Item page.** In `ItemPage.astro`:
- Import `{ stripGameMarkup }` from `../../lib/gameText`.
- Replace the StatTable rows with:

```astro
  {item.rarity && (
    <p class="item-rarity">Rarity: <span style={item.rarity.colour ? `color: ${item.rarity.colour}` : undefined}>{stripGameMarkup(item.rarity.name ?? item.rarity.key)}</span></p>
  )}
  <StatTable rows={[
    ["Category", item.category.name ?? item.category.key],
    ["Subcategory", item.subcategory],
    ["Legendary", item.legendary],
    ["Transferable", item.transferrable],
    ["Unique in the world", item.unique_to_world],
    ["Unique to faction", item.unique_to_faction],
    ["Agent types", item.agent_types.map((a) => a.name ?? a.key).join(", ")],
  ]} />
```

  The `Type` and `Applies to` rows are gone.

- [ ] **Step 3: Building level and character pages.**

In `BuildingLevelPage.astro`:
- Delete `["Cultures", level.cultures.join(", ")],`.
- After the Overview section, add `<Section title="Available to" show={level.availability.length > 0}><LinkList links={level.availability} /></Section>`.

In `CharacterPage.astro`, change the agent types row to `["Agent types", character.agent_types.map((a) => a.name ?? a.key).join(", ")],`.

Append to `web/src/styles/theme.css`: `.item-rarity { margin: 0 0 0.4rem; }`.

- [ ] **Step 4: Build to check the pages render**

Run: `cd web && npm run build`
Expected: Astro builds every page without errors. The build report prints page counts including `campaigns 4` (three pages plus the browse page), `unknown colours`, `missing links` and `placeholder images`. Record the report in the task report.

- [ ] **Step 5: Commit**

```bash
git add web/src
git commit -m "feat(web): unit type row, item rarity and category, building availability, agent type names" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 18: End-to-end checks, README, and the full suite

**Files:**
- Modify: `web/test/e2e/wiki.spec.ts`
- Modify: `README.md` (entity and page counts, the reference folder, new manifest sections, model version 3)

**Interfaces:**
- Consumes: the built site from Task 17.
- Produces: a green branch, ready for the rollout the user approves.

- [ ] **Step 1: Find the two real-data values the checks pin.** From `web/`, run:

```bash
node -e "const fs=require('fs'),p=require('path');const root=p.join('..','model');const dir=p.join(root,fs.readdirSync(root).filter(n=>!n.includes('.')).map(n=>[n,JSON.parse(fs.readFileSync(p.join(root,n,'manifest.json'),'utf8')).generated_at]).sort((a,b)=>a[1].localeCompare(b[1])).pop()[0]);const rows=t=>fs.readFileSync(p.join(dir,'entities',t+'.jsonl'),'utf8').split('\n').filter(Boolean).map(JSON.parse);console.log('named units',rows('unit').filter(u=>u.name).length);console.log('hidden-effect skill',rows('skill').find(s=>s.name&&s.levels.some(l=>l.effects.some(e=>e.hidden))).key)"
```

Expected output is two lines: `named units <N>` and `hidden-effect skill <key>`.

- [ ] **Step 2: Write the end-to-end checks.** In `web/test/e2e/wiki.spec.ts`:
- Rename "browse page lists every unit" to "browse page lists every named unit".
- Change its count from `2609` to the `named units` value from Step 1.
- Add these tests inside the `describe`, replacing `SKILL_WITH_HIDDEN_EFFECTS` with the key from Step 1:

```ts
  test("factions list defaults to Immortal Empires and All shows more", async ({ page }) => {
    await page.goto("/factions/");
    await waitForHydrated(page, "BrowseFilter");
    const campaign = page.getByLabel("Campaign", { exact: true });
    await expect(campaign).toHaveValue("wh3_main_combi");
    const visible = page.locator("#browse-table tbody tr:not([hidden])");
    await expect.poll(() => visible.count()).toBeGreaterThan(0);
    const immortalEmpires = await visible.count();
    await campaign.selectOption("");
    await expect.poll(() => visible.count()).toBeGreaterThan(immortalEmpires);
  });

  test("item page shows its rarity", async ({ page }) => {
    await page.goto("/items/wh_main_anc_weapon_ghal_maraz/");
    await expect(page.locator(".item-rarity")).toContainText("Unique");
  });

  test("unit page has no weapon key row", async ({ page }) => {
    await page.goto("/units/wh_main_emp_inf_greatswords/");
    await expect(page.getByRole("rowheader", { name: "Weapon", exact: true })).toHaveCount(0);
    await expect(page.getByText("wh_main_emp_greatsword", { exact: true })).toHaveCount(0);
  });

  test("effect lists set hidden effects aside", async ({ page }) => {
    await page.goto("/skills/SKILL_WITH_HIDDEN_EFFECTS/");
    await expect(page.locator("details.hidden-effects summary").first()).toHaveText(/^Hidden effects \(\d+\)$/);
  });

  test("campaign page lists playable factions", async ({ page }) => {
    await page.goto("/campaigns/wh3_main_combi/");
    await expect(page.locator("h1")).toHaveText("Immortal Empires");
    await expect(page.getByRole("heading", { name: "Playable factions" })).toBeVisible();
  });

  test("region culture picker has no placeholder entries", async ({ page }) => {
    await page.goto("/regions/wh3_main_combi_region_altdorf/");
    const picker = page.locator(".culture-picker");
    await picker.scrollIntoViewIfNeeded();
    const options = await picker.locator("select option").allTextContents();
    expect(options.length).toBeGreaterThan(1);
    expect(options.some((t) => /placeholder/i.test(t))).toBe(false);
    const chains = await picker.locator(".chain-group li").allTextContents();
    expect(chains.some((t) => /placeholder/i.test(t))).toBe(false);
  });
```

  The skill URL uses the skill's slug. If `site.slugs` lower-cases or changes the key, open `/skills/` in the built site and copy the link for that key.

- [ ] **Step 3: Run the end-to-end suite**

Run: `cd web && npm run build && npm run test:e2e`
Expected: every test passes, the existing ones included.

- [ ] **Step 4: Update README.md.**
- `entities/<type>.jsonl … for 19 types` becomes 20 types, adding campaigns.
- `The site has a page for each of the 15 entity types with pages` becomes 16.
- `shows the 19 \`entity\` exemptions` becomes 20.
- In the model layout section, add a `reference/` bullet: `campaigns.json`, `colours.json` (game UI colours with a dark-background variant and colour-blind profiles) and `ui_labels.json`.
- In the manifest description, add the `text`, `unnamed_by_type`, quality count and `reference` sections.
- Where the model version is mentioned, make it 3.

Keep each edit to the sentence that states the fact.

- [ ] **Step 5: Run everything and commit**

Run from the repository root: `uv run pytest tests -q`
Run from `web/`: `npm test`
Expected: both suites pass.

```bash
git add web/test/e2e/wiki.spec.ts README.md
git commit -m "test(web): end-to-end checks for campaigns, rarity, hidden effects and clean text; README for model version 3" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Handoff after the last task (needs the user's approval)

Do not do any of these without the user's go-ahead. The pull request description must list the rollout order from the spec:

1. Rebuild the model locally: `uv run python -m twwiki.model`. Task 9 already did this; do it again if `twwiki.duckdb` changed since.
2. Publish without deploying: `uv run python -m twwiki.publish --no-deploy`. This puts model version 3 in Firestore and Cloud Storage under the same build id.
3. Merge the pull request. The push to `main` runs Deploy, which builds the version 3 site and deploys `firestore.indexes.json` with the new `campaign` exemption.

Between steps 2 and 3, the live site keeps serving its existing static release. The pull request also explains every baseline count that rose (Task 9).
