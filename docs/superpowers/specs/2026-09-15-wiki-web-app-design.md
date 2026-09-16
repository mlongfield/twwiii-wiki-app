# Wiki Web App — Design

**Date:** 2026-09-15
**Status:** Approved in brainstorming, pending written-spec review
**Sub-project:** 2b of the wiki (sub-project 2)

## Context

Sub-project 1 built the game data model; sub-project 2a added regions,
provinces, building-chain availability and game images
(`docs/superpowers/specs/2026-09-15-wiki-data-regions-images-design.md`).
`python -m twwiki.model` writes `model/<build_id>/`:

- `entities/<type>.jsonl` — 19 entity types, ~150 MB, 44,599 entities
- `index/<type>.json` — key, name and filter fields per type
- `schema/<type>.schema.json` — JSON Schemas from the Pydantic models
- `images/` — referenced game images (8,843 files) and `images/inline.json`
- `manifest.json` — `build_id`, `model_version` (2), counts, gaps, `images`
  and `regions` sections

This sub-project is the public wiki built on that output.

Decisions already made for the whole project: TypeScript full-stack web app;
lives in `web/` in the same repository; no accounts; shareable build links
later (planners); one game build, no mods.

Decisions made in this brainstorming:

- Public and search-engine friendly; hosting undecided, so the output must
  deploy to any static host.
- **Pages for main types only** (15 types); effects, effect bundles,
  difficulty levels and campaign variables appear inline where used.
- **Search covers names plus key facts** (type, culture, category), not full
  text.
- **Region building browser: pick a culture**, defaulting to the region's
  starting owner's culture.
- **Visual direction: game-themed** — dark parchment and gold, serif headings.
- **Skill and technology trees: game-faithful grid with a pinned detail
  panel**, collapsing to per-line lists on small screens.
- **Architecture: Astro static site** with React islands.

## Findings this design relies on

Verified against model build `1eb25ce70f3a`.

**Page counts (15 page types, 26,621 pages):** unit 2,609; character 613;
skill 5,944; ability 2,899; technology 1,869; technology_tree 33;
building_level 5,259; building_chain 1,943; item 2,671; trait 744;
faction 717; culture 27; subculture 32; region 945; province 316.
Inline-only types: effect 15,064; effect_bundle 5,855; difficulty_level 7;
campaign_variable 1,052.

**Entity file sizes:** largest are effect 21.6 MB, unit 18.7 MB, character
16.9 MB, region 14.4 MB, building_level 14.0 MB, skill 13.4 MB.

**Game markup in entity text** (occurrences across all entity files):

| Form | Count | Meaning |
|---|---|---|
| `[[img:<path or tag>]][[/img]]` | ~24,000 | inline icon; target resolved via `images/inline.json` |
| `[[col:<name>]]…[[/col]]` | ~3,900 | coloured text (`magic`, `red`, …) |
| `[[b]]…[[/b]]` | ~1,560 | bold |
| `[[overridecol:<name>]]…` | 31 | coloured text (e.g. `fe_white`) |
| `[[i]]…[[/i]]` | 26 | italic |
| `[[sl:<help page>]]…[[/sl]]` | 25 | link to an in-game help page (no wiki target) |
| `{{tr:<key>}}` | 95 | unresolved text replacement left by the model |

Closing tags are sometimes mismatched in game data (`[[b]]…[[/i]]`). Text
uses `\n` for line breaks and `||` to separate a title from its body in
tooltips. Of 14,550 non-empty effect descriptions, 8,616 carry a value
placeholder — `%+n` (3,785), `%+n%` (3,639), `%n` (646), `%n%` (547),
`%-n%` (1) — and 5,934 carry none. Colour names used by `[[col:]]`: `yellow`
(1,966), `white` (1,693), `red` (356), `green` (187), `magic` (59),
`fe_white` (52), `ancillary_unique` (1); `[[overridecol:]]` uses only
`fe_white`.

**Trees:** skill trees give each node `tier` (column) and `indent` (row); Karl
Franz's tree has 51 nodes, rows 0–6 and 99 (row 99 and nodes with
`visible_in_ui` false are hidden in game), 60 links. Technology trees give
`tier`, `indent`, `pixel_offset_x/y` and links (Empire Civil Tech: 73 nodes,
41 links).

**Toolchain:** Node 22.12.0, npm 10.9.0. Current package versions: astro
7.3.2, @astrojs/react 6.0.5, react/react-dom 19.3.0, minisearch 7.2.0,
json-schema-to-typescript 16.0.0, typescript 7.0.2, vitest 5.0.1,
@playwright/test 1.63.0.

## Goals

- A crawlable HTML page for every entity of the 15 page types, cross-linked,
  with game icons and images.
- Interactive skill and technology trees, a region building browser with a
  culture picker, and site-wide type-ahead search.
- Output is plain static files that deploy to any static host.
- Gaps in the data show as clearly marked missing links or placeholder images,
  never broken pages; the build reports them.

## Non-goals

- Stat engine, combined stats, and the character and army planners
  (sub-projects 3 and 4).
- Shareable build links, accounts, user content.
- Choosing a host or writing host-specific deployment configuration.
- Multiple game builds or mods side by side.
- Pages for effects, effect bundles, difficulty levels, campaign variables.
- Full-text search.
- Light theme.

## Architecture

```
model/<build_id>/ ──prebuild──▶ web/src/generated/ (types)
                                web/public/images/ (copied images)
                                web/public/search-index.json
                   ──astro build (data layer → pages, islands)──▶ web/dist/
```

### Project layout

```
web/
  package.json            npm scripts: prebuild, build, dev, preview, test, test:e2e, fixtures
  astro.config.mjs        static output, React integration
  tsconfig.json
  scripts/
    prebuild.ts           locate model, validate, generate types, copy images, build search index
    make-fixtures.ts      regenerate test/fixtures/model from the real model
  src/
    data/                 data layer (build time only)
    lib/                  pure functions: game text, effect formatting, tree layout, search, region filter
    components/           Astro components (static)
    islands/              React components hydrated in the browser
    layouts/              page shell
    pages/                routes
    styles/               theme tokens and global styles
    generated/            generated TypeScript types (git-ignored)
  test/
    unit/                 Vitest tests
    e2e/                  Playwright tests
    fixtures/model/       small committed sample model
```

`web/node_modules/`, `web/dist/`, `web/.astro/`, `web/public/search-index.json`,
`web/public/images/` and `web/src/generated/` are git-ignored.

### Prebuild (`web/scripts/prebuild.ts`)

1. Locate the model: `MODEL_DIR` environment variable if set, otherwise the
   newest directory under `../model/` by `manifest.json` `generated_at`.
2. Validate: `manifest.json` exists, `model_version === 2`, and every one of
   the 19 `entities/<type>.jsonl` files named in `manifest.counts` exists.
   Any failure stops the build with a message naming the problem and the
   directory.
3. Generate `src/generated/<type>.ts` from `schema/<type>.schema.json` with
   json-schema-to-typescript, plus `src/generated/index.ts` exporting every
   type and an `EntityTypeMap`.
4. Copy `images/` to `public/images/` (skip when unchanged: same `build_id`
   marker file).
5. Build the search index (see Search) to `public/search-index.json`, which
   Astro copies to `dist/search-index.json`.
6. Write `src/generated/build-info.ts` with `buildId`, `generatedAt`,
   counts and the absolute `modelDir`, so the data layer loads exactly the
   model the prebuild validated.

### Data layer (`web/src/data/`)

Loaded once per build and memoised; pages never read files.

- `loadModel(dir): Model` streams each JSONL file and returns, per type, a
  `Map<string, Entity>` keyed by `key`, plus the manifest and `inline.json`.
- Derived lookups, built once: skills by key; chains available per culture
  (from `building_chain.availability`); units and characters per faction
  (already reverse-linked in the model); regions per province.
- `pageTypes` lists the 15 page types with their URL segment and display
  label; `hasPage(type)` is false for the four inline-only types.
- Validation against the generated types happens at compile time; the loader
  checks at runtime only that each line parses and has a string `key`.

### Routes

| Route | Source |
|---|---|
| `/` | home: entry points per type, featured trees, region browser entry |
| `/<segment>/` | browse page per page type |
| `/<segment>/<key>` | entity page per page type |
| `/search-index.json` | search index |
| `/data/culture-chains.json` | chains available per culture, for the region culture picker |
| `/images/...` | copied model images |
| `/404` | not-found page |

URL segments: `units`, `characters`, `skills`, `abilities`, `technologies`,
`technology-trees`, `buildings` (building levels), `building-chains`,
`items`, `traits`, `factions`, `cultures`, `subcultures`, `regions`,
`provinces`. Entity pages are addressed by a slug derived from the key (names
are not unique). Keys cannot be used verbatim: two skill keys differ only by
case (`wh2_main_skill_LL_self_defense` / `wh2_main_skill_ll_self_defense`),
which collide on case-insensitive file systems, and keys contain `&`, `!`,
`'`, `*` and `-` (`*` is not allowed in Windows file names). Slug rule: lower-
case the key and replace every character outside `[a-z0-9_-]` with `-`; when
two keys of the same type produce the same slug, each of them gets `-` plus
the first 6 hex characters of the SHA-1 of its original key appended. Slugs
are computed from the full key set of each type at build time. Links use
trailing slashes (`/units/wh_main_emp_inf_greatswords/`). Image URLs are the model's lower-case paths with each segment
URL-encoded (paths contain spaces).

### Pages

Every entity page shows breadcrumbs, the display name (or the key, marked,
when the name is missing), its main image, and the sections below. Sections
with no data are omitted.

- **Unit:** card image (portrait when no card), caste/category/class, tier,
  costs and caps, base stats, melee weapon, missile weapon with projectile,
  shield, mount, attributes, abilities, characters using the unit, custom
  battle factions, recruiting building levels.
- **Character:** portrait of the associated unit, title and description, agent
  types, lore of magic, cost and cap, factions, abilities, items, and each
  skill tree through the tree island.
- **Skill:** icon, description, unlock rank, levels (unlock rank and inline
  effects per level), characters with the skill.
- **Ability:** icon, type and source type, description, activation, phases
  (stat effects, attribute effects, other phase values), units, characters,
  modifying effects (as inline effect names).
- **Technology:** icon, descriptions, civil/engineering/military flags, effects,
  placements (tree link, research points, cost per round, resource cost),
  required technologies and buildings, unlocking building.
- **Technology tree:** scope (culture, subculture, faction, campaign) and the
  tree island.
- **Building level:** icon, chain, level, costs, resource cost, cultures,
  effects (with damaged/ruined values and context requirement), recruited
  units.
- **Building chain:** category, levels in order, availability (culture,
  subculture, faction, campaign).
- **Item:** icon, type, category, subcategory, legendary, applies to,
  bodyguard unit, allowed agent types and characters, required skills,
  effects.
- **Trait:** icon, levels (threshold, name, description, effects), antitraits.
- **Faction / culture / subculture:** flag (factions), links between them,
  units and characters (factions).
- **Region:** province, campaign, settlement flag, starting owner, capital
  flags, slot cap, cultural originator, region groups; special settlements
  list slot templates (role, variant, resource with icon, permitted chains);
  every settlement shows the culture picker island with the chains that
  culture can build.
- **Province:** campaign, capital, member regions.

**Browse pages** render a table of all entities of the type from the data
layer: name with icon (the entity's main image), key, and the same filter
fields the model writes to `index/<type>.json` (e.g. units: caste, category,
class, tier; regions: campaign, settlement, template source). The index files
themselves are not read, because they carry no image paths.
A small island filters the table in the browser by text and by the type's
category-like fields; without JavaScript the full table is still readable.

### Components (`web/src/components/`, static)

- `Layout` — header (site name, search island, type navigation), footer
  (game build id and model generation date), theme stylesheet.
- `EntityLink` — `{type, key, name, missing}` link → icon + name linking to
  the entity page; when `missing` is true or the type has no page, renders the
  name (or key) as text with a "missing" style for missing targets.
- `GameImage` — model image path → `<img>` with width/height classes per kind
  (`icon`, `card`, `portrait`, `flag`); null → themed placeholder of the same
  shape.
- `GameText` — renders game markup (see below).
- `EffectList` — list of effect applications: effect icon, description with
  value substituted, scope label, and building-only extras (damaged/ruined
  values, context requirement).
- `StatTable`, `Breadcrumbs`, `Section`.

### Islands (`web/src/islands/`, React)

- `TreeView` — used for skill trees and technology trees. Props: nodes (row,
  column, id, icon, label, detail payload), links, hidden-row rule. Desktop:
  CSS grid, rows by `indent`, columns by `tier`, SVG connector lines between
  linked nodes, selected node's details in a pinned side panel (skills:
  levels with unlock rank and effects; technologies: effects and research
  cost per placement). Below 768 px wide: collapsible per-row lists with the
  same detail content inline. Hidden nodes (`visible_in_ui` false, row 99)
  are not shown. Hydrated with `client:visible`. The static HTML behind it
  lists every node with its details, so content is crawlable without
  JavaScript.
- `CulturePicker` — culture selector (defaults to the starting owner's
  culture, or the first culture alphabetically when there is no owner) and
  the list of chains available to it, grouped by chain category. The default
  culture's list is rendered statically in the page; other cultures' lists
  come from one shared static file, `/data/culture-chains.json` (culture key →
  groups of chain key, name, URL, icon), fetched on the first culture change.
  Embedding every culture's chains in each region page was rejected: about
  230 KB per page across 945 region pages. `client:visible`.
- `SearchBox` — see Search. `client:idle`.
- `BrowseFilter` — table filter for browse pages. `client:visible`.

### Game text (`web/src/lib/gameText.ts`)

`parseGameText(text): Node[]` produces a small tree; `GameText` renders it.

- Tags: `[[img:X]][[/img]]` → inline icon using `inline.json[X]` (placeholder
  when null or absent); `[[col:NAME]]` and `[[overridecol:NAME]]` → span with
  a colour class from a fixed palette map (unknown names → default text
  colour); `[[b]]`, `[[i]]` → bold, italic; `[[sl:X]]` → emphasised text (no
  link).
- Closing tags close the innermost open tag regardless of name; unclosed tags
  close at the end of the text; stray closers are dropped.
- `\n` → line break; `A||B`, split at the first `||` in the text → title `A`
  rendered as a heading-styled line above body `B`.
- `{{tr:X}}` and any unrecognised `[[…]]` or `{{…}}` token → rendered as
  plain text with the braces removed (the token content stays visible).

### Effect values (`web/src/lib/effectText.ts`)

`formatEffect(description, value): string` substitutes placeholders:
`%+n` → value with explicit sign (`+4`, `-5`); `%n` → value without sign;
`%+n%` / `%n%` keep the trailing percent sign; `%-n%` is treated like `%n%`. Values are formatted without
trailing `.0`. A description with no placeholder is shown followed by the
signed value in parentheses. A null description shows the effect key
followed by the signed value in parentheses.

### Search

- Index built at prebuild with MiniSearch over all 15 page types. Document
  fields: `id` (`<type>:<key>`), `name`, `key`, `type`, and per type the
  facts `culture`/`subculture` names where the entity has them, and `category`
  (unit category, item category, building chain category, ability type).
  Stored fields: `name`, `type`, `key`, `icon` (image path or null).
  Searchable: `name` (boost 3), `key`, facts.
- `SearchBox` fetches `/search-index.json` on first focus, then searches as
  you type (prefix and fuzzy 0.2), showing up to 8 results per type with icon
  and type label; Enter opens the top result; arrow keys move.
- Target index size: under 10 MB uncompressed; the prebuild prints the size.

### Theme (`web/src/styles/`)

Design tokens as CSS custom properties: background `#16120d`, panel
`#241c12`, border `#6b5326`, accent border `#8a6d33`, gold `#e2b85c`, muted
`#a8925f`, text `#e8dcc2`; headings in a serif stack (Georgia), body and
tables in a system sans-serif stack. Game colour names used by `[[col:]]` and
`[[overridecol:]]` map to tokens: `yellow`, `white`, `red`, `green`, `magic`,
`fe_white` and `ancillary_unique` each get one; any other name uses the text
colour. One theme (dark) in v1.

## Error handling

| Situation | Behaviour |
|---|---|
| No model directory found, `manifest.json` missing, `model_version` ≠ 2, or an entity file missing | Prebuild exits non-zero with a message naming the problem and directory |
| A JSONL line fails to parse or lacks `key` | Build fails naming file and line number |
| Link to a missing entity (`missing: true`) | `EntityLink` renders the key as text with the "missing" style; counted in the build report |
| Link to an inline-only type | Rendered as text (effects inline), never a link |
| Image field null or file absent from `public/images` | `GameImage` placeholder of the right shape; counted in the build report |
| Entity name null | Page title and links show the key, styled as unnamed |
| Unknown or malformed markup | `GameText` falls back to visible text |
| Unknown URL | Static `/404` page |

The build prints a report after `astro build`: pages per type, missing links
rendered, placeholder images rendered, search index size. Gaps never fail the
build.

## Testing

**Unit tests (Vitest, `npm test`)** against `test/fixtures/model/`:

- Data layer: loading, maps per type, derived lookups (chains per culture,
  regions per province), `hasPage`, parse errors name file and line.
- `parseGameText`: every tag, nested tags, mismatched and stray closers,
  unclosed tags, `\n`, `||`, `{{tr:}}`, unknown tokens, `[[img:]]` with
  resolved, null and absent `inline.json` entries.
- `formatEffect`: `%+n`, `%n`, `%+n%`, negative values, decimals, no
  placeholder, null description.
- Tree layout: row/column placement, hidden rows removed, links between
  visible nodes only, mobile grouping by row.
- Culture filter: default culture choice (owner, fallback), chains grouped by
  category.
- Search index: documents per type, facts present, stored fields, a query for
  "greatswords" returns the unit first.

**Fixture model** (`test/fixtures/model/`, committed): produced by
`npm run fixtures` from the real model — manifest, `inline.json`, schemas, and
entity files containing Greatswords (`wh_main_emp_inf_greatswords`), Emperor
Karl Franz (`wh_main_emp_karl_franz`) with all skills in his tree, Hold the
Line! (`wh_main_lord_passive_hold_the_line`), Empire Civil Tech
(`emp_civ_reworkd`) with its technologies, Altdorf
(`wh3_main_combi_region_altdorf`) with the other regions of Reikland, the
building chains available to the Empire culture (`wh_main_emp_empire`) with
the levels of `wh_main_EMPIRE_settlement_major` and `wh_main_EMPIRE_barracks`,
the item `wh2_dlc09_anc_magic_standard_banner_of_the_hidden_dead`, the Empire culture/subculture/faction, and
the effects they apply. No images are committed; image tests use null paths
or stubbed `inline.json` entries.

**End-to-end tests (Playwright, `npm run test:e2e`)** against a full build of
the real model served by `astro preview`; run on demand, skipped with a clear
message when `web/dist/` is absent:

- `/units/wh_main_emp_inf_greatswords` shows "Greatswords", melee attack 32 and
  a loaded card image.
- `/characters/wh_main_emp_karl_franz`: selecting "Devastating Charge" in the
  tree shows its details in the panel; at 400 px wide the tree shows
  collapsible lines.
- `/regions/wh3_main_combi_region_altdorf`: special slot templates are listed;
  choosing another culture in the picker changes the chain list.
- Searching "greatswords" in the header lists the unit; Enter opens it.
- Browse page counts: `/units/` lists 2,609 rows.
- `/effects/anything` returns the 404 page.

## Out-of-scope follow-ups

- Stat engine and planners (sub-projects 3–4), which reuse the data layer and
  islands.
- Host selection and deployment configuration.
- Light theme, full-text search, pages for inline-only types.
- Slot-template output shape (region pages repeat permitted chains per
  template; a model change can deduplicate later without changing pages'
  appearance).
