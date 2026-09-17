# twwiki — Total War: WARHAMMER III data extraction pipeline

Extract game DB tables and loc text via `rpfm_server`, land them raw, load
them into a typed DuckDB database, and generate pages from the result.

```
rpfm_server (WS) → raw/<build_id>/{files,images}/ → twwiki.duckdb → model/<build_id>/ → web app
                 extract.py  (immutable)          load.py         model (Python)
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

`config.yaml` `images.folders` lists what is exported as it is to
`raw/<build_id>/images/<in-game path>` (all PNG for what the wiki uses). An
entry is either a folder, exported whole, or a pattern whose `*` matches one
path segment (`ui/flags/*/mon_64.png`), exported file by file from the game's
file list. `images.path_columns` lists `table.column` pairs whose values are
exact image paths (`ui_tagged_images.image_path`, `ancillary_types.ui_icon`);
those files are exported too, read from the tables extracted earlier in the
same run, unless an entry already covers them. They keep the narrow patterns
safe: text icons and item icons point into skin subfolders the patterns leave
out, and without the exact file the model would fall back to a different image
with the same file name. An entry or column that fails, or a pattern that
matches nothing, is listed under `images.failed_folders` in the raw manifest
and extraction carries on. The raw manifest's `images.from_tables` section
counts paths listed, not in the game files, already covered and exported, and
names any pack they come from outside the build id.

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

The `build_id` is derived from the packs holding the files `images.folders`
selects, not from the section itself (files named by `path_columns` do not
feed it). If you add, remove or narrow an entry whose files sit in an
already-covered pack (almost any `ui/...` folder), the `build_id` does not
change, so `extract.py` sees the build as already extracted, logs "nothing to
do", and the new images never land on disk. After changing `images` for a game
build you have already extracted, move or rename the existing
`raw/<build_id>/` directory (the pipeline never deletes raw builds) and run
extract again so it re-exports under that id.

Raw images are large and `raw/` is append-only, so every game patch adds this
cost again. For build `1eb25ce70f3a`, exporting all of `ui/flags` and
`ui/skins` made `raw/<build_id>/images` 836 MB; the patterns and path columns
bring it to 286 MB (16,561 files) with an identical model.

## Game data model

`python -m twwiki.model` turns `twwiki.duckdb` into curated entities in
`model/<build_id>/` (design: `docs/superpowers/specs/2026-09-15-game-data-model-design.md`):

- `entities/<type>.jsonl`: one entity per line for 20 types (units, characters
  with skill trees, skills, abilities, effects and bundles, buildings,
  technologies and trees, items, traits, factions, cultures, subcultures,
  difficulty levels, campaign variables, regions, provinces, campaigns).
  References are links `{type, key, name, missing}`; effects are applied
  through one `EffectApplication` shape everywhere.
- Regions and provinces come from the start-position tables: owner at
  campaign start, capitals, slot cap and province. Slot templates, resources
  and permitted building chains are known only for special settlements (their
  templates are named after the region); every other settlement is marked
  `template_source: "generic"`. Exact slots for those need `startpos.esf`,
  which is not decoded.
- `index/<type>.json`: key, name and filter fields for browsing.
- `schema/<type>.schema.json`: JSON Schemas exported from the Pydantic models
  in `twwiki/model/schemas.py`; the web app generates TypeScript types from them.
- `images/`: referenced image files copied under their in-game paths, plus
  `images/inline.json` mapping `[[img:…]]` text tokens to a file or null.
- `reference/`: `campaigns.json`, `colours.json` (game UI colours with a
  dark-background variant and colour-blind profiles) and `ui_labels.json`.
- `manifest.json`: `model_version` (3), counts, missing names, missing links,
  unresolved text tokens, a `text` section (placeholder prefixes and dropped
  token counts), `unnamed_by_type`, quality counts (effect applications
  without scope text, unmatched rarity scores, unresolved agent type names,
  excluded campaign-exclusive permissions, unresolved building availability
  keys, `ui_labels_without_text`), partial entity types, an `images` section (per-field
  referenced/resolved/missing/ambiguous counts, plus `available` and
  `files_copied`), a `reference` section (document name to entry count), and a
  `regions` section (`special_templates_unmatched`).
- `link_report.json`: every schema reference (RPFM's reference marks, kept
  in the database's `_columns` table) that touches a table the build read,
  labelled `both_read`, `source_not_read` (a table the model ignores points at
  one it uses: a possible missed link) or `target_not_read`. For `both_read`
  references it counts rows whose value matches nothing in the target column,
  with up to five examples. "Read" means a builder queried the table, not
  that it follows that column. The report is informational and never fails a
  build.

The model never calculates final stats or research turns; that is the stat
engine's job. Gaps in game data are counted in the manifest; an entity that
fails schema validation stops the build.

Tests: `uv run pytest`. Tests against the real database skip when
`twwiki.duckdb` is absent. After a game patch, rebuild, review any failing
expected values, and regenerate `tests/model/missing_links_baseline.json` only
after checking why links went missing.
Regenerate `tests/model/missing_images_baseline.json` the same way, only after
checking why images went missing.

## Wiki web app

`web/` is an Astro static site built from the newest `model/<build_id>/`
(design: `docs/superpowers/specs/2026-09-15-wiki-web-app-design.md`).

```bash
cd web
npm install
npm run build      # prebuild (validate model, generate types, copy images,
                   # build search index) then Astro, then a build report
npm run preview    # serve web/dist locally
npm run dev        # prebuild once, then the Astro dev server
npm test           # unit tests against the committed fixture model
npm run test:e2e   # Playwright tests against web/dist (needs npm run build; a cold run
                   # can fail with "webServer exited early" because astro preview
                   # daemonizes itself — start `npm run preview -- --port 4321`
                   # first, then re-run)
npm run fixtures   # regenerate web/test/fixtures/model from the real model
```

`MODEL_DIR=test/fixtures/model npm run build` builds the small fixture site in
seconds, which is the quickest way to check a change.

The site has a page for each of the 16 entity types with pages (effects,
effect bundles, difficulty levels and campaign variables are shown inline on
the pages that use them), skill and technology tree views, a region building
browser with a culture picker, and search over names and key facts. Pages are
addressed by a slug derived from the entity key.

`web/dist/` is plain static files. Everything it serves comes from the model
build; the live site is built and deployed by GitHub Actions from a published
snapshot (see "Publishing and hosting").

## Publishing and hosting

The wiki is hosted on Firebase (project `twwiii-wiki`, `https://twwiii-wiki.web.app`).
Design: `docs/superpowers/specs/2026-09-16-firebase-platform-design.md`.

```
extract → load → model → python -m twwiki.publish ─┬─► Cloud Storage  builds/{build_id}/  (model snapshot)
                                                    ├─► Firestore      builds/{build_id}/{type}/{key}
                                                    ├─► Firestore      site/current
                                                    └─► GitHub Actions deploy.yml ─► Firebase Hosting
```

After a game patch: extract, load and model as usual, then

```bash
uv run python -m twwiki.publish
```

It publishes the newest model (or `--build-id ID`) in this order and stops at
the first failure:

1. Preflight: model version and files, Google credentials, the bucket, and
   `TWWIKI_GITHUB_TOKEN` (unless `--no-deploy`). Nothing is written if it fails.
2. Uploads the model folder to `builds/{build_id}/` in Cloud Storage, skipping
   files whose MD5 already matches.
3. Marks `builds/{build_id}` as `loading`, writes every entity document, and
   deletes documents whose keys are no longer in the model.
4. Checks each collection's document count against the manifest.
5. Marks the build `ready` and points `site/current` at it.
6. Starts the `Deploy` workflow, which downloads the snapshot, builds the
   site, runs the web unit tests, deploys Hosting plus Firestore and Storage
   rules and indexes, and checks the live home page names the build.

Each entity document holds `key`, `name`, the type's browse fields, a
`<field>_keys` list for every top-level link field (for example
`abilities_keys` on units), and the full entity under `entity`, which is
exempt from indexing (`firestore.indexes.json`, generated by
`uv run python -m twwiki.publish --write-indexes`). Browsers may read
`site/current` and `builds/**`; nothing can be written from a browser, and
Cloud Storage is closed to browsers.

Other modes:

- `--no-deploy`: stop after step 5.
- `--deploy-only [--build-id ID]`: start the deploy workflow again, for the
  current build unless given.
- `--prune BUILD_ID`: delete one build's Firestore documents. Refuses the
  current and previous builds; Cloud Storage snapshots are never deleted.

Recovering:

- Failure in steps 1–4: the live site and `site/current` are untouched. Fix
  the cause and run publish again; unchanged files and documents are cheap to
  repeat.
- Failure in step 6 (dispatch): the build is live in Firestore but the site
  still shows the previous pages. Run `--deploy-only`.
- A failed workflow run leaves the previous Hosting release live; re-run it
  from the Actions tab, or roll back a bad release in the Firebase console.
- If a republish of the build that is already current fails, `builds/{id}`
  stays `loading` and CI deploys refuse it until publish is re-run
  successfully.

Pushes to `main` that touch `web/`, the Firebase config or the workflow also
deploy, using the build named by `site/current`.

Setup (once, by the project owner):

1. Install the Google Cloud CLI and run `gcloud auth application-default login`
   and `gcloud auth application-default set-quota-project twwiii-wiki`.
2. Firestore in Native mode and the default Storage bucket must exist. Put the
   bucket name in `config.yaml` (`firebase.storage_bucket`). The project id
   lives in `config.yaml` (`firebase.project_id`) and `.firebaserc`.
3. Create a deploy service account with Firebase Hosting Admin, Firebase Rules
   Admin, Cloud Datastore Index Admin, Cloud Datastore Viewer, Storage Object
   Viewer, Service Usage Consumer, Firebase Storage Viewer and Firebase Viewer
   (without Firebase Viewer the Storage rules deploy fails with "Firebase
   Storage has not been set up"); store its JSON key as the repository secret `FIREBASE_SERVICE_ACCOUNT`, and set repository
   variables `FIREBASE_PROJECT_ID` and `FIREBASE_STORAGE_BUCKET`. Keyless
   Workload Identity Federation is a more secure alternative to a JSON key.
4. Create a fine-grained GitHub token for this repository with Actions read
   and write, and set it as `TWWIKI_GITHUB_TOKEN` where you publish.
5. Limit Hosting release retention to 5 in the Firebase console (each release
   is about 633 MB).
6. Before the first publish, deploy the rules and index exemptions once with
   your own login:

   ```bash
   npx --yes firebase-tools@15.30.1 deploy --only firestore:rules,firestore:indexes,storage --project twwiii-wiki
   ```

   and wait until the Firestore console, under Indexes → Single field →
   Exemptions, shows the 20 `entity` exemptions as ready. The deploy workflow
   deploys them too, but it first runs after publish has written about 48,600
   documents; without the exemptions Firestore would index every `entity`
   subfield (about 2.87 million index entries), and a database created in
   test mode would stay writable from browsers until then.

Costs (list prices, approximate): a publish is about 48,600 document writes
plus count queries (and a key listing when republishing an existing build),
roughly 10–15 US cents.

Optional emulator tests (need Java 21+):

```bash
npx --yes firebase-tools@15.30.1 emulators:exec --project demo-twwiki --only firestore,storage "uv run pytest tests/publish/test_emulator.py -q"
cd web && npm run test:rules
```

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
