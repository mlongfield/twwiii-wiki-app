# TWW3 Wiki — UI Consistency & Data-Model Coverage Audit

Scope: `web/src/**` (Astro 7 + React islands) against `twwiki/model/schemas.py`,
`twwiki/model/build.py`, and `docs/superpowers/specs/2026-09-15-wiki-web-app-design.md`.
Code review only; no files modified, no build/dev-server run.

All 15 page bodies (`web/src/components/pages/*.astro`), all 10 shared
components, all 4 islands, all `lib/` and `data/` modules, `theme.css`, the 3
route files, and the design spec were read in full. Field-level comparisons
were checked against `web/test/fixtures/model/entities/*.jsonl` where useful
(e.g. to confirm a "_name" field actually carries `[[img:]]` markup, or that a
"cultures" field really is a raw key).

---

## Summary — top 10 findings by reader impact

1. **`StatTable` cannot render game-text markup, but some "_name" fields fed
   into it can carry it.** `ability.type_name` was proven (via fixture data)
   to contain `[[img:...]][[/img]]Augment (Area)`; the author worked around
   this by pulling *only* `type_name` out of `StatTable` into its own
   `<GameText>`-wrapped paragraph, while the sibling field `source_type_name`
   (and Unit's `caste_name`/`category_name`/`class_name`) still go straight
   into `StatTable`'s plain-string cell. Any future data with markup in those
   fields will render literal `[[...]]` brackets. *(High — `StatTable.astro`;
   `AbilityPage.astro:18-25`)*
2. **Effect "polarity" is modeled but never shown.** `Effect.is_positive_value_good`
   and `Effect.icon_negative_image` exist specifically to mark whether a
   change is good or bad for the player, but no component reads either field
   — every effect delta is a plain signed number with one static icon, so a
   "+2 Corruption" (bad) looks exactly like a "+2 Growth" (good). *(High —
   `schemas.py:37,69-74`; unused across `web/src`)*
3. **`BuildingLevel.cultures` is a raw string list, not `Link`s**, so the
   "Cultures" stat on every building page — and the "Cultures" browse column
   — shows internal keys like `wh_main_emp_empire` instead of resolved names
   or links, unlike `BuildingChain.availability`, which models the same
   culture/subculture/faction relationship as full `Link`s one page over.
   `Unit.mount` has the same raw-string problem. *(High — `schemas.py:484` vs
   `489-494`; `BuildingLevelPage.astro:32`; confirmed in fixture data)*
4. **The mobile tree fallback is duplicated.** `TreeView`'s own narrow-width
   behaviour renders a `TreeLines` list, but `TreeStaticList` is *also*
   always rendered right below it — so a phone-width visitor with JavaScript
   sees the same skill/technology tree listed twice, once inside each
   component's own collapsible `<details>` UI. *(Medium-High —
   `TreeView.tsx:69-92,108-110`; `CharacterPage.astro:43-44`;
   `TechnologyTreePage.astro:26-27`)*
5. **Ability phase stat-effects are shown unformatted.** `phase.stat_effects`
   renders raw `e.how` operator codes and raw `e.value` numbers with no
   `formatNumber()` and no snake_case humanizing, unlike literally every
   other numeric/enum display in the app (`StatTable`, `ResourceCost`,
   `EffectList`, browse `cellText`). *(Medium-High — `AbilityPage.astro:74-84`,
   esp. line 78)*
6. **Faction pages show no territory.** `Region.starting_owner` links to a
   faction, but `Faction` has no `regions` field at all (and it's absent from
   `build.py`'s generic reverse-link table), so a faction page has no
   "starting regions"/territory section — arguably one of the first things a
   wiki reader looks for on a faction page. *(Medium-High, partly a model gap
   — `schemas.py:601-616`; `build.py:26-38`; `FactionPage.astro`)*
7. **Several concrete fields are silently dropped**: `Unit.unit_sets` never
   rendered; `BaseStats.num_mounts`/`secondary_ammo` missing from the Base
   Stats table; `Phase.max_damaged_entities`/`imbue_ignition`/`mana_regen_mod`
   missing from Ability phases; `TechnologyTree.colour` never shown anywhere.
   *(Medium — see "Model fields not surfaced" below for citations)*
8. **Traits have no reverse link to their bearers** (only "Antitraits"),
   unlike Skills, which do show "Characters" via the generic reverse-link
   mechanism — though this may be deliberate since traits are usually
   acquired dynamically during a campaign rather than being static data.
   *(Medium, caveated — `build.py:26-38`; `TraitPage.astro`)*
9. **Browse-table filters don't decompose multi-value columns.**
   `browseFilters` builds its option list from the already comma-joined
   display string, so filtering a Character by "Agent types" or a Building
   by "Cultures" offers whole concatenated combinations as single dropdown
   options instead of one option per value — far less useful than the
   single-value filters (Caste, Category, Tier). *(Medium — `browse.ts:60-65`
   built on `:53-56`)*
10. **Colour values are bare text with no swatch.** `Faction.primary_colour`
    renders as `Colour: E00606` in a `StatTable` row — no `#` prefix, no
    visual preview — even though the page already has an image slot
    (flag) that could sit next to it. *(Low-Medium — `FactionPage.astro:21`)*

---

## Page consistency table

All 15 entity pages share one `EntityHeader.astro` (breadcrumbs, main image,
`<h1>` name-or-key, `{Singular} · <key>` subtitle) via `[segment]/[slug].astro`,
so the **header is structurally identical everywhere**; the only variance is
whether the type has an image concept at all (see "Images/placeholders" row).

| Page | Section order (top → bottom) | Stats | Links | Effects | Images / empty states |
|---|---|---|---|---|---|
| Unit | Overview, Base stats, Melee weapon, Missile weapon, Shield, Attributes, Abilities, Characters, Recruited at, Custom battle factions | `StatTable` throughout | `LinkList` for reverse links | none (units have no direct effects) | card→portrait fallback via `mainImage`; conditional sections via `Section show=` |
| Character | Overview (title + description + stats + associated unit), Abilities, Factions, Items, Skill tree(s) | `StatTable` | `LinkList`; associated unit as inline `EntityLink` | none directly (effects live on skills) | portrait borrowed from associated unit; `TreeView`+`TreeStaticList` per tree |
| Skill | Overview, Levels (per-level heading + effects), Characters | `StatTable` (2 rows) | `LinkList` | `EffectList` per level | icon; `Section show=` |
| Ability | Overview (+ ad-hoc `<p>` for `type_name`), Activation, Phase N × (StatTable + **ad-hoc raw table** for stat/attribute effects), Units, Characters, Modified by effects | `StatTable` + one **non-StatTable raw `<table class="phase-stats">`** (unformatted) | `LinkList` | none via `EffectList` — ability phases use bespoke markup instead | icon; type_name routed through `GameText` uniquely on this page |
| Technology | Overview (2 `GameText` blocks), Effects, Research (raw `<table>` with `ResourceCost`), Requires technologies, Requires buildings | `StatTable` | `LinkList` + `EntityLink` inline (`unlocked_by_building`) | `EffectList` | icon |
| Technology tree | Scope, Technologies (tree island) | `StatTable` (2 rows) | `EntityLink` inline only | none (effects live on technologies) | no image; `colour` field unused |
| Building level | Overview (+ `ResourceCost`), Effects, Recruits | `StatTable` | `LinkList`; chain as inline `EntityLink` | `EffectList` (damaged/ruined/context shown) | icon; **raw `cultures` strings, not links** |
| Building chain | Overview, Levels, Available to (raw `<table>` of culture/subculture/faction/campaign) | `StatTable` (2 rows) | `LinkList`; raw `<table>` of `EntityLink`s (blank cells when a link is null, no "—") | none | no image |
| Item | Overview (2 `GameText` blocks), Effects, Characters (=`agent_subtypes`), Required skills (raw `<ul>` w/ inline level) | `StatTable` | `LinkList`; one raw `<ul>` | `EffectList` | icon |
| Trait | Overview, Level N × (heading + description + `StatTable` + `EffectList`), Antitraits | `StatTable` | `LinkList` | `EffectList` per level | icon; **no reverse link to bearers** |
| Faction | Overview, Units, Characters | `StatTable` | `LinkList`; culture/subculture inline | none | flag image; **no regions/territory** |
| Culture | Subcultures, Factions *(no Overview section at all — nothing to show)* | none | `LinkList` | none | no image |
| Subculture | Overview (wraps a single culture link), Factions | none | `LinkList`; culture inline | none | no image |
| Region | Overview, Special settlement slots, Buildings-by-culture (`CulturePicker` island) | `StatTable` | `LinkList`; several inline `EntityLink`s | none | no image; rich nested cards for slot templates |
| Province | Overview, Regions | `StatTable` (2 rows) | `LinkList`; capital inline | none | no image |

Cross-cutting observations from the table:

- **Cost presentation differs by type for the same concept.** Unit/Character
  show a bare integer (`Recruitment cost`, `Cost`) in `StatTable` with no
  currency icon; Technology/BuildingLevel show a bulleted `ResourceCost` list
  (`Treasury: 750`, pooled resources, trade resources). This follows the
  model (`Unit.recruitment_cost: int` vs `ResourceCost` object) but the
  reader-facing effect is that "cost" looks structurally different across
  types with no visual unification (e.g. no coin icon anywhere).
- **Reverse-link section naming is actually consistent** ("Characters",
  "Units", "Factions" reused verbatim across Unit/Ability/Skill/Faction/
  Culture/Subculture pages) — this is a genuine strength, not a gap.
- **Ad-hoc raw `<table>`/`<ul>` markup appears on 4 of 15 pages**
  (Ability's phase-stats table, Technology's Research table, BuildingChain's
  availability table, Item's required-skills list) instead of a shared
  component, so column headers, cell alignment and null-handling are
  reinvented four times instead of once.
- **Culture vs Subculture structure differs for an equivalent case**: Culture
  has no wrapping "Overview" section (nothing to show), but Subculture wraps
  its single `culture` link in an explicit "Overview" section — cosmetic but
  inconsistent given both are otherwise near-identical minimal pages.

---

## Findings by theme

### A. Game text & effect formatting

1. **`StatTable` never routes values through `GameText`/`renderGameTextHtml`.**
   Confirmed via fixture data that `ability.type_name` contains
   `"[[img:ui/battle ui/ability_icons/icon_spell_area_of_augments.png]][[/img]]Augment (Area)"`
   — real markup. The code's own fix (routing `type_name` through a separate
   `<GameText>` paragraph, `AbilityPage.astro:19,25`) proves the team knows
   `StatTable` can't handle it, yet the structurally identical
   `source_type_name` (`AbilityPage.astro:21`) and Unit's `caste_name`/
   `category_name`/`class_name` (`UnitPage.astro:24-26`) still go straight
   into `StatTable`.
   **Severity:** High. **Impact:** any future markup in those fields renders
   as literal bracket text in a stats table. **Fix direction:** either give
   `StatTable` an optional GameText-aware cell renderer, or route every
   `_name` field through `GameText` consistently and drop the one-off
   paragraph.

2. **`phase.stat_effects` and `phase.attribute_effects` are unformatted.**
   `AbilityPage.astro:74-84`: `<td>{e.how}</td><td>{e.value}</td>` bypasses
   `formatNumber()`; `attribute_effects` is a plain
   `` `${a.attribute} (${a.attribute_type})` `` join with no `GameText` and no
   `.replace(/_/g," ")` humanizing, unlike `EffectList`'s
   `scopeLabel()`/`advancement_stage.replace(...)` pattern or `ResourceCost`'s
   `pooled_resource_factor.replace(...)`.
   **Severity:** Medium-High. **Impact:** readers see raw floats and enum
   codes like `add` instead of "+5" / "Addition". **Fix direction:** run
   `e.value` through `formatNumber`/`signed`, and humanize `e.how` and
   `attribute`/`attribute_type` the same way other snake_case codes are
   handled elsewhere.

3. **Effect polarity and negative-state icon are modeled but unused.**
   `Effect.is_positive_value_good` and `Effect.icon_negative_image`
   (`schemas.py:69-74`) have zero references anywhere in `web/src`
   (`EffectList.astro` only reads `description`/`icon_image`).
   **Severity:** High. **Impact:** a reader can't visually tell "this bigger
   number is worse" (e.g. Corruption, Upkeep) from "this bigger number is
   better" (e.g. Growth, Income) — exactly the distinction the model field
   was built for. **Fix direction:** color the effect value/icon based on
   `is_positive_value_good` XOR sign, and swap to `icon_negative_image` when
   the applied value is unfavourable.

4. **`Effect.additional_tooltip` and `Effect.bonus_targets` are never
   surfaced** (`schemas.py:43,49-58`) — no page or component reads either
   field, so extra tooltip text and the structured list of what an effect's
   bonus actually targets (unit set, ability, attribute, phase) are dropped
   entirely even though they're present on every effect application.
   **Severity:** Medium. **Fix direction:** consider showing
   `additional_tooltip` as a secondary line in `EffectList`, at least where
   present.

5. **`EffectBundle`/`effect_bundle` is essentially dead weight in the web
   app** — it exists only in `pageTypes.ts` exclusions and generated types;
   nothing in `web/src/lib` or `web/src/components` ever reads an
   effect-bundle entity (its `EffectApplication.advancement_stage` field is
   handled generically by `EffectList`, but the bundle entity itself is
   inert). Not a defect (bundles are intentionally inline-only per the design
   spec), but worth flagging as unused surface area if it's ever pruned.

### B. Model fields not surfaced

| Field | Schema location | Missing from |
|---|---|---|
| `Unit.unit_sets` | `schemas.py:259-264,295` | `UnitPage.astro` (no section at all) |
| `BaseStats.num_mounts` | `schemas.py:202` | `UnitPage.astro:37-62` |
| `BaseStats.secondary_ammo` | `schemas.py:194` | `UnitPage.astro:37-62` |
| `MeleeWeapon.splash_attack_power_multiplier` | `schemas.py:215` | `UnitPage.astro:65-81` |
| `Projectile.category`, `.marksmanship_bonus`, `.shockwave_radius` | `schemas.py:223,234,237` | `UnitPage.astro:82-101` |
| `Phase.max_damaged_entities`, `.imbue_ignition`, `.mana_regen_mod` | `schemas.py:139,144,148` | `AbilityPage.astro:56-73` |
| `TechnologyTree.colour` | `schemas.py:459` | `TechnologyTreePage.astro` (whole file) |
| `Effect.category`, `.priority`, `.additional_tooltip`, `.bonus_targets`, `.is_positive_value_good`, `.icon_negative*` | `schemas.py:62-74` | everywhere (see Theme A) |
| `Faction.flags_path` | `schemas.py:611` | `FactionPage.astro` (reasonable to omit — internal path) |

Which omissions matter to a reader: `unit_sets` (moderate — affects which
mass buffs/abilities apply to a unit), `num_mounts`/`secondary_ammo`
(moderate — relevant for cavalry/artillery reading), `marksmanship_bonus`
(moderate — affects missile accuracy readers care about), effect
polarity/tooltip fields (**high**, see Theme A), `TechnologyTree.colour` and
`Faction.flags_path` (low — cosmetic/internal).

Also, **some fields are shown without a resolvable name or unit**:
- `MeleeWeapon.key`/`MissileWeapon.key` are shown verbatim as the "Weapon"
  stat value (`UnitPage.astro:68,85`) — the schema has no weapon display
  name at all, so readers see internal ids like `wh_main_emp_hammer_hero`.
- `Character.agent_types` (`CharacterPage.astro:23`) and `Item.agent_types`
  (`ItemPage.astro:29`) are raw snake_case codes (e.g. `general`) joined by
  comma, with no `_name` enrichment — unlike Unit's `caste`/`category`/
  `unit_class`, which each get a paired `_name` field the page prefers.
  Inconsistent enrichment for conceptually similar categorical fields.
- `BuildingChain.category`/`Item.category`/`Faction.category` are shown raw
  with no unit or enrichment (schema simply provides none) — not fixable
  without a model change, but worth noting as an inconsistency between types
  that do get a `_name` (Unit, Ability) and types that don't.

### C. Cross-linking gaps

1. **Faction has no regions/territory**, described in Summary #6.
2. **Trait has no reverse link to bearers** (only forward "Antitraits"),
   described in Summary #8 — likely intentional since traits are dynamic
   campaign state, not static per-character data (`Character`/`Unit` schemas
   have no `traits` field to reverse in the first place).
3. **BuildingLevel has no reverse "unlocks technologies"** even though
   `Technology.unlocked_by_building` (`schemas.py:444`) points the other way;
   `BuildingLevelPage.astro` has no such section, and `build.py`'s `REVERSE`
   table (`:26-38`) doesn't cover it.
4. **`BuildingChainPage`'s availability table renders blank cells** (no "—"
   placeholder) when `culture`/`subculture`/`faction` is null, because
   `EntityLink` renders nothing for a null link (`EntityLink.astro:25`
   `{link && (...)}`), unlike other null-handling in the codebase which
   substitutes an empty string explicitly (e.g. `TechnologyPage.astro:38`
   `p.cost_per_round || ""`). Minor visual inconsistency (an apparently empty
   cell vs. an intentionally blank one look identical).
5. Culture/Subculture/Faction pages do **not** list building chains
   available to them even though `BuildingChain.availability` links to all
   three — but this looks deliberate: the design spec explicitly routes
   "what can this culture build" through the Region `CulturePicker` island
   instead, so flagged as an **open question**, not a defect.

### D. Browse and search alignment

1. **`BROWSE_FIELDS` (`web/src/data/browse.ts:5-40`) matches `INDEX_FIELDS`
   (`twwiki/model/build.py:41-57`) exactly** for every type present in both —
   no drift found. However, both leave `technology_tree`, `faction`,
   `culture`, and `subculture` with **zero** extra columns/filters, even
   though `TechnologyTree` has useful `campaign`/`culture`/`faction` fields
   and `Faction` has `culture`/`subculture` — unlike `Region`/`Province`,
   which do filter by `campaign`. **Severity:** Medium. **Fix direction:**
   add at least a `campaign` filter to technology trees and a
   `culture`/`subculture` filter to factions, mirroring Region/Province.
2. **Filters don't decompose multi-value columns** (Summary #9):
   `browseFilters` (`browse.ts:60-65`) derives its option list from
   `cellText`'s comma-joined string (`browse.ts:53-56`), so array-valued
   browse fields (`agent_types`, `cultures`) produce one filter option per
   *combination* seen, not per individual value.
3. **Search "key facts" are inconsistent across types**, contrary to the
   design spec's claim that search covers "names plus key facts (type,
   culture, category)" (design doc line 35-36): `searchCulture`
   (`searchIndex.ts:14-31`) only populates `culture` for
   faction/subculture/technology_tree/building_level/building_chain, and
   `searchCategory` (`searchIndex.ts:33-45`) only populates `category` for
   unit/item/building_chain/ability. Character, skill, technology, trait,
   region, province, and culture entities get **empty** `culture` and
   `category` search fields, so search only matches those types on
   name/key. Also, `region.cultural_originator`/`starting_owner` (a natural
   culture signal) is not fed into `searchCulture` at all.
   **Severity:** Medium. **Fix direction:** extend `searchCulture`/
   `searchCategory` to cover the remaining types where a reasonable
   culture/category source exists (e.g. region via `starting_owner`'s
   faction, technology via `is_civil`/`is_military`/`is_engineering`).
4. **Browse columns generally match what the entity page leads with**
   (e.g. Unit's Caste/Category/Class/Tier/Naval columns mirror the first
   `StatTable` rows on `UnitPage.astro`), which is a consistency strength
   worth noting, not a gap.

### E. Island vs static behaviour

1. **Duplicate tree list on narrow+JS** (Summary #4) — the strongest finding
   in this theme; it also runs counter to the design doc's description of a
   single "collapsible per-row list" behaviour for both narrow screens and
   no-JS crawling (design doc lines 280-284), where the implementation
   built two separate versions of that idea (`TreeView.tsx`'s `TreeLines`
   and `TreeStaticList.astro`).
2. **`SearchBox`'s wrapper has no `role="search"`** landmark
   (`SearchBox.tsx:72`, plain `<div className="site-search">`), while
   `BrowseFilter`'s wrapper does (`BrowseFilter.tsx:45`,
   `<div className="browse-filter" role="search">`) — the site's two
   "search" UIs are labeled inconsistently for assistive tech. Minor:
   `BrowseFilter`'s `role="search"` also wraps its `<select>` filter
   dropdowns, which aren't really "search" controls.
3. **`CulturePicker` and `TreeView` degrade sensibly without JS**: the
   default culture's chain list is server-rendered
   (`RegionPage.astro:33-47`) before the island hydrates, and `TreeView`'s
   detail content is fully present in `TreeStaticList` for crawlers/no-JS —
   both good, consistent patterns.
4. **`BrowseFilter` degrades correctly without JS**: rows have no `hidden`
   attribute until the island runs, so the full table is readable
   server-rendered, matching the design doc's claim (line 255).

### F. Layout, theme and accessibility

1. **Colour-contrast spot check (manual WCAG calculation) passed** for the
   theme's main token pairs: `--text` on `--bg` (very high contrast),
   `--muted` (`#a8925f`) on `--bg` (~6.2:1) and on `--panel` (~5.6:1), and
   `--missing` (`#c0705a`) on `--bg` (~5.1:1) all clear the 4.5:1 AA
   threshold for normal text. No CSS resets `outline`, so default browser
   focus rings remain visible on all interactive elements — no contrast or
   focus-visibility defects found in `theme.css`. (Flagged as an **open
   question** below since this was a manual calculation, not a rendered
   check.)
2. **Heading hierarchy is consistent** (`h1` from `EntityHeader`, `h2` from
   every `Section`/ad-hoc `<h2>`, `h3` for sub-items like skill/trait levels
   and region slot templates) — no skipped levels found across the 15 page
   bodies.
3. **Decorative icon `alt=""` is applied consistently** everywhere an icon
   sits next to visible text (`EntityLink.astro:28`, `TreeView.tsx:60,80`,
   `CulturePicker.tsx:68`, `SearchBox.tsx:112`, browse rows in
   `[segment]/index.astro:38`) — a genuine strength, not a gap.
4. **`.tree` is the only component with an explicit phone-width breakpoint**
   (`theme.css:110-112`, `@media (max-width: 767px)`); the browse table
   instead relies on `.table-wrap { overflow-x: auto }` plus
   `white-space: nowrap` cells (`theme.css:83-84`), which is reasonable but
   means wide browse tables (e.g. Units with 5 extra columns) will scroll
   horizontally on phones rather than reflow — acceptable, but worth
   confirming visually since this audit didn't render the page.
5. **Culture vs Subculture Overview-section inconsistency** (noted in the
   table above) — cosmetic, `Section title="Overview"` present on one,
   absent on the other for structurally similar minimal pages.
6. **`ICON_TYPES` in `images.ts:10` lists `effect`/`effect_bundle`**, but
   `mainImage()` is never actually called with those types in practice
   (only `PageType`s reach it) — harmless dead code, not a live bug.

### G. Data-model duplication risk (raw strings instead of Links)

Beyond `BuildingLevel.cultures` (Summary #3), the same "conceptually a
relation but modeled as a raw string" pattern recurs for `Unit.mount`
(`schemas.py:291`, `str | None`, shown raw at `UnitPage.astro:32`) and
`SkillTreeNode.faction`/`.subculture`/`.campaign` (`schemas.py:315-317`, used
only internally for tree layout, not directly displayed — lower risk).
**Fix direction:** where these raw strings reference another entity type
(mount → unit, cultures → culture), promoting them to `Link` in the schema
would let the pages resolve names/links the same way every other relation
does, instead of leaking internal database keys to readers.

---

## Open questions

1. Is `BuildingLevel.cultures` intentionally a raw string list (e.g. for
   build performance/size) rather than `list[Link]`, or is this an oversight
   that should be fixed alongside `BuildingChain.availability`'s richer
   shape?
2. Should `Faction` gain a `regions`/territory reverse link, or is omitting
   it deliberate because the Region `CulturePicker` island already covers
   "what a culture can build" and starting territory is considered
   out of scope for v1?
3. Is the missing Trait→bearers reverse link deliberate (traits are dynamic
   per-campaign state, so there's no static "characters with this trait"
   data to show), or should the model eventually capture default/starting
   traits for named characters?
4. Should `StatTable` become GameText-aware generally (retiring the
   `Ability.type_name` special case), or should the convention instead be
   "no `_name` field may contain markup" enforced upstream in the model
   build — which would need auditing every `_name` field for embedded
   `[[...]]` tokens (only `type_name` and `stat_name` were confirmed to carry
   markup in the sampled fixture data)?
5. The colour-contrast and focus-visibility conclusions above were computed
   manually from the CSS custom properties, not observed in a rendered
   browser — worth a quick confirmation pass with an automated contrast
   checker (the live-site visual reviewer may already be covering this).
6. Should the search index extend `searchCulture`/`searchCategory` coverage
   to the remaining types (character, skill, technology, trait, region,
   province, culture) so "key facts" search behaves uniformly across all 15
   types, per the design doc's stated intent?
