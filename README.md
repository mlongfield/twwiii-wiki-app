# twwiki — Total War: WARHAMMER III data extraction pipeline

Extract game DB tables and loc text via `rpfm_server`, land them raw, load
them into a typed DuckDB database, and generate pages from the result.

```
rpfm_server (WS) → raw/<build_id>/{files,images}/ → twwiki.duckdb → model/<build_id>/ → web app
     extract.py            (immutable)               load.py        model (Python)
```

## Why this shape

**Extract lands raw and does nothing else.** Every transform happens after the
files hit disk. Extraction is the slow, patch-sensitive step — you want to run
it once per game build and then iterate on modelling for free. Raw dumps are
one row per line, so they are diffable, which is how you find out what a patch
actually changed.

**Everything is keyed by `build_id`.** `raw/` is append-only per build. Never
overwrite a previous build's dump; that history is the most valuable thing the
pipeline produces. The id is derived from the size and mtime of the packs the
data came from
(`db.pack`, `local_en.pack`, and the UI packs holding the exported images).

## Before you run it

`rpfm_server` ships with RPFM (https://github.com/Frodo45127/rpfm/releases).
Open `rpfm_ui.exe` and, once per install:

1. **Edit → Preferences**: check the Warhammer 3 game path; set Default Game.
2. **About → Check Updates**: download schemas. Repeat after every game patch.
3. **Game Selected → Generate Dependencies Cache**. Repeat after every game patch.

Leave RPFM open while the pipeline runs. The UI keeps the server alive; the
server exits by itself once its last session closes.

## Run order

```bash
uv sync                          # or: pip install -e .
uv run python -m twwiki.extract  # needs RPFM open
uv run python -m twwiki.load
uv run python -m twwiki.model   # curated entities for the web app
uv run python -m twwiki.render
```

## The three things that will bite you

### 1. Where the data comes from

A Total War game spreads its data across many packs, and later packs can
override earlier ones. Rather than reimplementing that, `extract.py` reads
RPFM's **vanilla dependency cache** (`DecodePackedFile` with source
`GameFiles`), which exposes the game as one file set. For WH3 that is 1,521 DB
tables, one `data__` file each, all from `db.pack`, plus 235 loc files from
`local_en.pack`.

Consequences:

- The cache reflects the game **as of its last regeneration**. After a patch,
  regenerate it in RPFM before extracting, or you will extract stale data under
  a new `build_id`.
- Only vanilla data is extracted. Mods are not included.
- Each new server session loads the game's schema and cache itself
  (`SetGameSelected`); having them loaded in the UI is not enough.

### 2. Keys and loc resolution

Primary keys come from the schema's `is_key` flags, never from column-name
guesses: 568 WH3 tables have multi-column keys and 385 have a key that is not
the first column. `load.py` records every column's key and reference flags in
`_columns`, and counts duplicate keys per table in `_tables` instead of
dropping rows.

DB tables contain keys (`wh_main_emp_inf_spearmen`), not names. Display text
lives in loc files keyed by strings like
`land_units_onscreen_name_wh_main_emp_inf_spearmen`. All loc files land in one
`loc` table behind a `resolve_loc()` macro, which falls back to the raw key so
missing text is visible rather than blank.

### 3. Schema drift

RPFM decodes tables using community-maintained schemas. After a patch, a table
may fail to decode until the schema repo updates. `extract.py` lists such files
under `undecodable` in `manifest.json` (and any RPFM had to alter while
decoding under `altered`) rather than dropping them silently.

## Raw file format

Each `raw/<build_id>/files/<in-game path>.jsonl` is a header line followed by
one JSON array per row:

```
{"kind": "DB", "table": "main_units_tables", "version": 7, "path": "db/main_units_tables/data__", "container": "db.pack", "altered": false, "fields": [{"name": "unit", "type": "StringU8", "is_key": true, "reference": null}, ...]}
["", -1, "lord", 1, false, ...]
```

Values are in `fields` order (RPFM's *processed* field order) with RPFM's type
tags stripped. `load.py` maps the types onto DuckDB: integers to `BIGINT`,
floats to `DOUBLE`, booleans to `BOOLEAN`, everything else to `VARCHAR`.

## Images

`config.yaml` `images.folders` lists in-game folders exported as they are to
`raw/<build_id>/images/<in-game path>` (all PNG for what the wiki uses). A
folder that fails to export is listed under `images.failed_folders` in the raw
manifest and extraction carries on.

The model resolves each image reference in the tables (bare names, names with
`.png`, full paths with backslashes) against those files, copies only the
referenced ones to `model/<build_id>/images/`, and writes
`images/inline.json` mapping every `[[img:…]]` text icon to a file or null
(a tag is looked up in the `ui_tagged_images` table; anything else is treated
as a path). Image fields end in `_image`; `unit.portrait_image` is the
custom-battle portrait, which stands in for characters that have no
`card_image`. The manifest's `images` section counts
referenced, resolved, missing and ambiguous references per field. Without
`raw/<build_id>/images` the build still succeeds with every image field null.

## Game data model

`python -m twwiki.model` turns `twwiki.duckdb` into curated entities in
`model/<build_id>/` (design: `docs/superpowers/specs/2026-09-15-game-data-model-design.md`):

- `entities/<type>.jsonl`: one entity per line for 19 types (units, characters
  with skill trees, skills, abilities, effects and bundles, buildings,
  technologies and trees, items, traits, factions, cultures, subcultures,
  difficulty levels, campaign variables, regions, provinces). References are links
  `{type, key, name, missing}`; effects are applied through one
  `EffectApplication` shape everywhere.
- Regions and provinces come from the start-position tables: owner at
  campaign start, capitals, slot cap and province. Slot templates, resources
  and permitted building chains are known only for special settlements (their
  templates are named after the region); every other settlement is marked
  `template_source: "generic"`. Exact slots for those need `startpos.esf`,
  which is not decoded.
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
Regenerate `tests/model/missing_images_baseline.json` the same way, only after
checking why images went missing.

## Mapping the server surface

`extract.py --discover` selects the game, prints what the dependency cache
holds, and sends a handful of read-only probe commands. The protocol and
command reference live in RPFM's docs under `docs/server/`; the commands this
project uses are in the `CMD` dict at the top of `rpfm_client.py`.

rpfm_server also exposes an MCP endpoint at `http://127.0.0.1:45127/mcp` with
150 tools, if you want to explore it from Claude Code.

## Later

- `diff.py`: two build_ids in, changed rows out. This is the killer feature.
- Swap markdown render for a static site once the model settles.
- Only reach for SQLite if you need the DB to ship inside a browser bundle.
