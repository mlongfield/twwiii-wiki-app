# Firebase Platform — Design

**Date:** 2026-09-16
**Status:** Approved
**Sub-project:** 2c (Firebase platform)

## Context

The pipeline so far runs on one machine: `twwiki.extract` reads the game
through rpfm_server, `twwiki.load` builds `twwiki.duckdb`, and
`twwiki.model` writes `model/<build_id>/`:

- `entities/<type>.jsonl` — 19 entity types, 48,599 entities, about 130 MB
- `index/<type>.json` — key, name and browse fields per type
- `schema/<type>.schema.json` — JSON Schemas from the Pydantic models
- `images/` — 8,843 referenced images plus `images/inline.json`
- `manifest.json` (`model_version` 2) and `link_report.json`

The Astro wiki in `web/` (sub-project 2b) reads a model folder at build time
and writes a static site to `web/dist`: 35,493 files, 633 MB, of which
images are 118 MB and `search-index.json` 11.4 MB. Nothing is hosted yet.

This sub-project hosts the project on Firebase. The project owner has an
existing Firebase project, `twwiii-wiki`, on the Blaze (pay-as-you-go) plan;
its default Hosting site is `https://twwiii-wiki.web.app`.

## Decisions made in brainstorming

- **Firebase is the platform.** Hosting serves the site; Firestore serves game
  data for queries and, later, saved builds; Cloud Storage holds published
  model snapshots.
- **Game data goes to Firestore**, for three goals: updating the live site
  without a manual redeploy, live queries and filters in the wiki, and one
  backend shared with the planners.
- **Pages stay static.** Each publish rebuilds the static site in the cloud.
  Server rendering (Firebase App Hosting or Cloud Functions) was rejected:
  per-request reads, cold starts and the largest rework of the web app, for
  instant updates nobody needs.
- **The planners are browser apps.** Adding items to characters, units and
  heroes to armies, and adjusting skills, is page state; the stat engine recalculates in the browser from
  planner bundles published with each build. Per-interaction Firestore reads
  would be slow and billed per document.
- **Saved builds: share links, no accounts.** Small Firestore documents with
  short ids, anonymous Firebase sign-in and App Check behind the scenes.
  Built in sub-projects 4–5.
- **Queries run on Firestore**, not over files shipped to the browser.
- **The rebuild reads a snapshot from Cloud Storage**, not Firestore. The web
  build needs schemas and images anyway, and the existing build then runs
  unchanged.
- **GitHub Actions rebuilds and deploys**, started by the publish command and
  by merges to `main`, so data and code deploys share one path.
- **Old builds:** Cloud Storage keeps every snapshot; Firestore keeps the
  current and previous build, and older ones are removed only by an explicit
  prune command.

### Sub-project order after this decision

- **2c Firebase platform** (this spec).
- **2d Wiki query screens:** Firestore-backed filter and sort screens, their
  composite indexes, derived fields they need beyond this spec's, and App
  Check enforcement.
- **3 Stat engine:** browser only.
- **4 Character planner** and **5 Army planner:** planner bundles published
  with each build, saved builds in Firestore behind share links, and army data
  the model lacks (unit caps, hero limits).

### Decisions revised

| Earlier decision | Where | Now |
|---|---|---|
| Output deploys to any static host; host selection out of scope | `2026-09-15-wiki-web-app-design.md` | Firebase Hosting, deployed by GitHub Actions |
| Hosting undecided | `2026-09-15-wiki-data-regions-images-design.md` | Firebase |
| Stat engine runs in browser and server | `2026-09-15-game-data-model-design.md` | Browser only |
| The only server-side user feature is shareable build links | `2026-09-15-game-data-model-design.md` | Game data is also served from Firestore for queries; share links remain the only user-written data, still without accounts |

Each earlier spec gets a one-line note pointing here.

## Findings this design relies on

- All 48,599 entity keys are valid Firestore document ids: none contains `/`,
  is `.` or `..`, matches `__.*__`, or exceeds 1,500 bytes.
- The largest entity is 247 KB (an ability), under Firestore's 1 MiB document
  limit. Largest by type: ability 247 KB, effect 148 KB, region 147 KB,
  character 142 KB.
- Firestore indexes every field by default and allows 40,000 index entries per
  document; deeply nested entities risk that limit, so the full entity must be
  exempt from indexing.
- Top-level link fields (a link is `{type, key, name, missing}`) include
  `unit.abilities`, `unit.characters`, `unit.custom_battle_factions`,
  `unit.recruited_by_buildings`, `character.associated_unit`,
  `character.abilities`, `character.factions`, `character.items`,
  `item.bodyguard_unit` and `item.agent_subtypes`.
- `wh_main_lord_passive_hold_the_line` is on 18 units, including
  `wh_main_emp_cha_captain_0` (Empire Captain).
- One publish is about 48,600 document writes, over the Spark plan's 20,000
  per day; Blaze is required and already in place.
- Astro builds with `build.format: "directory"`, so every page is
  `<path>/index.html`. `SearchBox` fetches the search index only when used.
- There is no CI in the repository yet.

## Goals

- One command publishes a model: snapshot to Cloud Storage, entities to
  Firestore, switch the live build, trigger the site rebuild.
- Nothing becomes live until every write for the build has succeeded and been
  verified; a failed publish leaves the live site untouched and resumes
  cheaply when re-run.
- The static site deploys to Firebase Hosting from GitHub Actions, for data
  publishes and code merges alike.
- Firestore documents are queryable by browse fields and link keys, with the
  full entity attached and unindexed.
- Rules: public read of game data, no browser writes, no browser access to
  Cloud Storage.

## Non-goals

- Query screens, composite indexes and App Check enforcement (2d).
- Planner bundles, saved builds, share links, anonymous sign-in (4–5).
- Accounts, user content, preview deploys for pull requests, a custom domain.
- Running extraction or the model build in the cloud; both need the game
  install and rpfm_server.
- Creating the Firebase project, service accounts, tokens or billing; those
  are the owner's setup steps.

## Architecture

```
your machine                          Google Cloud / Firebase                 GitHub
─────────────                         ───────────────────────                 ──────
extract → load → model (unchanged)
        │
        └─ python -m twwiki.publish ─┬─► Cloud Storage  builds/{build_id}/…  (snapshot)
                                     ├─► Firestore      builds/{build_id}/…  (entities)
                                     ├─► Firestore      site/current = {build_id}
                                     └─► dispatches deploy workflow ────────► Actions: deploy.yml
                                                                               download snapshot
                                                          Firebase Hosting ◄── npm run build + firebase deploy
browser ◄── static pages, images, search index (Hosting)
browser ◄── live queries (2d) and saved builds (4–5) (Firestore)
```

### Repository layout (new files)

```
firebase.json                    Hosting, Firestore and Storage config
.firebaserc                      default project id
firestore.rules
firestore.indexes.json           generated; committed
storage.rules
.github/workflows/deploy.yml
twwiki/publish/
  __init__.py
  __main__.py                    CLI
  documents.py                   entity -> Firestore document; derived fields
  indexes.py                     generates firestore.indexes.json
  snapshot.py                    upload plan and upload to Cloud Storage
  firestore_writer.py            bulk writes, stale deletes, counts, prune
  deploy.py                      GitHub workflow dispatch
  clients.py                     thin adapters over firebase-admin / HTTP
tests/publish/                   unit tests with fakes; emulator tests
pyproject.toml                   adds firebase-admin (Firestore, Storage)
web/scripts/fetch-snapshot.ts
web/test/unit/fetchSnapshot.test.ts
web/test/rules/                  rules tests (emulator)
```

The publish code talks to Cloud Storage, Firestore and GitHub only through
the small interfaces in `clients.py`, so every step is unit-testable with
fakes.

## Firestore layout

### Documents

- **`site/current`**: `{build_id, previous_build_id, model_version,
  published_at}`. The single pointer the site, the deploy workflow and later
  query screens read.
- **`builds/{build_id}`**: `{status: "loading" | "ready", model_version,
  generated_at, published_at, counts}`. `counts` is copied from the manifest.
- **`builds/{build_id}/{type}/{key}`**: one collection per entity type, named
  exactly as the model's entity types (`unit`, `character`, `skill`, …), with
  the game key as the document id.

### Entity documents (`twwiki/publish/documents.py`)

```
{
  "key": "wh_main_emp_cha_captain_0",
  "name": "Empire Captain",
  <browse fields>,                 // from INDEX_FIELDS, e.g. caste, category, unit_class, tier, is_naval
  "<field>_keys": [...],           // one per top-level link or link-list field
  "entity": { ...full entity... }  // exactly as in entities/<type>.jsonl
}
```

- **Browse fields** are the fields `twwiki.model.build.INDEX_FIELDS` names for
  the type, copied from the entity.
- **Link key fields:** for each top-level entity field whose value is a link,
  `<field>_keys` is `[key]`; for a list of links, the list of their keys in
  order, de-duplicated. A null link gives `[]`. Links marked `missing` are
  included (their key is still the game's reference). Nested links are not
  derived here; 2d adds specific derived fields when a screen needs them.
- Derived field names must not collide with entity field names; a collision
  fails the publish preflight.

### Indexes (`twwiki/publish/indexes.py`)

`firestore.indexes.json` holds no composite indexes and one field override
per entity collection group exempting `entity` from indexing:

```json
{
  "indexes": [],
  "fieldOverrides": [
    {"collectionGroup": "unit", "fieldPath": "entity", "indexes": []}
  ]
}
```

(one entry per entity type, sorted by type). `python -m twwiki.publish
--write-indexes` regenerates the file; a unit test fails when the committed
file differs from the generated one.

### Rules (`firestore.rules`)

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /site/{doc} {
      allow read: if true;
      allow write: if false;
    }
    match /builds/{buildId} {
      allow read: if true;
      allow write: if false;
      match /{type}/{key} {
        allow read: if true;
        allow write: if false;
      }
    }
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

The publish command and the deploy workflow use admin credentials, which
bypass rules.

## Cloud Storage

- **Bucket:** the project's default bucket, `<project_id>.firebasestorage.app`
  (configurable).
- **Layout:** `builds/{build_id}/` mirrors `model/<build_id>/` exactly
  (`manifest.json`, `link_report.json`, `entities/`, `index/`, `schema/`,
  `images/`).
- **Retention:** snapshots are never deleted by any command.
- **Rules (`storage.rules`):** deny all reads and writes from browsers.

## Publish command (`twwiki/publish`)

### Config (`config.yaml`)

```yaml
firebase:
  project_id: twwiii-wiki
  storage_bucket: twwiii-wiki.firebasestorage.app   # confirm in the console
  deploy_workflow:
    repo: mlongfield/twwiii-wiki-app
    workflow: deploy.yml
    ref: main
```

No secrets live in config. Google credentials come from Application Default
Credentials (`gcloud auth application-default login`). The GitHub token comes
from `TWWIKI_GITHUB_TOKEN`: a fine-grained token for this repository only,
with the Actions read-and-write permission.

### `uv run python -m twwiki.publish [--build-id ID] [--no-deploy]`

Model selection: `--build-id` picks `model/<ID>`; otherwise the newest model
under `paths.model_dir` by manifest `generated_at`, skipping `.partial` and
`.old` folders (the rule `web/src/data/modelDir.ts` uses).

Steps, stopping at the first failure:

1. **Preflight** (no writes):
   - `manifest.json` exists and `model_version` is 2;
   - all 19 entity files, 19 schema files and `images/inline.json` exist;
   - no derived field name collides with an entity field;
   - the Google credentials can read `site/current` (a missing document is
     fine) and see the bucket;
   - `TWWIKI_GITHUB_TOKEN` is set, unless `--no-deploy`.
2. **Snapshot:** list existing blobs under `builds/{build_id}/` with their MD5
   hashes; upload every local file that is missing or differs, 16 in
   parallel; delete nothing. Log files uploaded and skipped.
3. **Entities:**
   - set `builds/{build_id}` to `status: "loading"` (keeping `published_at`
     if present);
   - write every entity document with the Firestore bulk writer (retries and
     rate limiting built in), overwriting by key;
   - list existing document ids in each of the build's collections and delete
     ids absent from the model.
4. **Verify:** a count aggregation per collection must equal
   `manifest.counts[type]`; any mismatch stops the publish with the
   differences listed.
5. **Go live:** set `builds/{build_id}` to `status: "ready"` with
   `published_at` now; set `site/current` to this build. `previous_build_id`
   becomes the old current build id only when it differs from this one;
   otherwise it is kept.
6. **Deploy** (skipped with `--no-deploy`): `POST
   /repos/{repo}/actions/workflows/{workflow}/dispatches` with `ref` and
   `inputs.build_id`; on success print the repository's Actions URL for the
   workflow.

### Other modes

- `--deploy-only [--build-id ID]`: step 6 only, for the current build unless
  given; refuses a build that is not `ready`.
- `--prune ID`: deletes `builds/{ID}` and its entity collections. Refuses the
  current and previous build ids. Never touches Cloud Storage.
- `--write-indexes`: regenerates `firestore.indexes.json` and exits.

### Failure behaviour

- A failure in steps 1–4 leaves `site/current` unchanged, so the live site
  and queries keep using the previous build. Re-running resumes: matching
  snapshot files are skipped and document writes are idempotent.
- A build left `loading` is never pointed to by `site/current`.
- If step 6 fails after go-live, the command exits non-zero, says the site
  still shows the previous pages, and names `--deploy-only` as the fix.
- Republishing the build that is already current updates its documents in
  place; queries may briefly see a mix of old and new documents. Accepted:
  it only happens when republishing the same game build after a model change.
- Exit code 0 only when every requested step succeeded.

### Cost per publish (list prices, approximate)

About 48,600 writes, a document-id listing of about 48,600 reads, and 19
count queries: roughly 10–15 US cents. Unchanged snapshot files cost only a
listing.

## Hosting (`firebase.json`)

```json
{
  "hosting": {
    "public": "web/dist",
    "trailingSlash": true,
    "headers": [
      {"source": "/_astro/**", "headers": [{"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}]},
      {"source": "/images/**", "headers": [{"key": "Cache-Control", "value": "public, max-age=86400"}]},
      {"source": "/search-index.json", "headers": [{"key": "Cache-Control", "value": "public, max-age=300"}]},
      {"source": "/data/**", "headers": [{"key": "Cache-Control", "value": "public, max-age=300"}]}
    ]
  },
  "firestore": {"rules": "firestore.rules", "indexes": "firestore.indexes.json"},
  "storage": {"rules": "storage.rules"}
}
```

- `trailingSlash: true` matches Astro's directory format. The plan verifies
  that internal links (`urlFor` and hard-coded links) end in `/`, fixing any
  that do not, so Hosting never redirects.
- HTML keeps Hosting's default caching; each deploy clears the Hosting CDN
  cache.
- Hosting compresses responses itself; nothing is pre-compressed.
- Unknown paths get `404.html` automatically.

## Web app changes

- **`astro.config.mjs`:** `site: process.env.PUBLIC_SITE_URL` (unset locally);
  add `@astrojs/sitemap`, which writes a sitemap index when `site` is set.
- **`web/scripts/fetch-snapshot.ts`** (run with `tsx`; `firebase-admin` as a
  dev dependency):
  - arguments: `--project`, `--bucket`, optional `--build-id`, `--out`
    (default `../model`);
  - without `--build-id`, reads `site/current`; either way reads
    `builds/{id}` and fails unless `status` is `ready`;
  - downloads every blob under `builds/{id}/` to `<out>/{id}/`, 16 in
    parallel;
  - fails unless the downloaded `manifest.json` has that `build_id`;
  - prints the model folder path as its last line.
- Local development is unchanged: `npm run dev` and `npm run build` still use
  `MODEL_DIR` or the newest local model.

## Deploy workflow (`.github/workflows/deploy.yml`)

- **Triggers:**
  - `workflow_dispatch` with optional input `build_id`;
  - `push` to `main` with paths `web/**`, `firebase.json`, `.firebaserc`,
    `firestore.rules`, `firestore.indexes.json`, `storage.rules`,
    `.github/workflows/deploy.yml`.
- **Concurrency:** group `deploy`, `cancel-in-progress: false`.
- **Environment:** repository variables `FIREBASE_PROJECT_ID` and
  `FIREBASE_STORAGE_BUCKET`; secret `FIREBASE_SERVICE_ACCOUNT` (JSON key).
- **Steps:**
  1. Check out; set up Node 22.12 with the npm cache for `web/`.
  2. Write the service account key to a temporary file and export
     `GOOGLE_APPLICATION_CREDENTIALS`.
  3. `npm ci` in `web/`.
  4. `npx tsx scripts/fetch-snapshot.ts` with the input build id if given;
     export the printed folder as `MODEL_DIR`.
  5. `PUBLIC_SITE_URL=https://twwiii-wiki.web.app npm run build`, then
     `npm test`. Tests run after the build because `src/data/model.ts`
     imports `src/generated/build-info.ts`, which the prebuild writes and git
     ignores.
  6. `npx firebase-tools@<version> deploy --only
     hosting,firestore:rules,firestore:indexes,storage --project
     $FIREBASE_PROJECT_ID --message "build <id> @ <short sha>"
     --non-interactive`.
  7. Smoke check: `curl` the home page; fail unless HTTP 200 and the body
     contains the build id.
- The temporary key file is removed in an `always()` step.
- `firebase-tools` is pinned to an exact version, chosen when the plan is
  written, like every other dependency in the repository.

**Service account roles** (owner creates; confirmed against the first
deploy): Firebase Hosting Admin, Firebase Rules Admin, Cloud Datastore Index
Admin, Cloud Datastore Viewer, Storage Object Viewer, Service Usage Consumer
(`firebase deploy` checks enabled APIs), Firebase Storage Viewer and Firebase
Viewer. The Storage rules deploy asks the Firebase Storage API for the default
bucket; without Firebase Viewer that call returns 404 and `firebase-tools`
reports "Firebase Storage has not been set up" (found on the first deploy).

## Error handling summary

| Situation | Behaviour |
|---|---|
| Wrong `model_version`, missing files, field-name collision | Publish preflight fails; nothing written |
| Credentials or bucket unavailable | Preflight fails; nothing written |
| Upload or write error after retries | Publish stops; `site/current` unchanged; re-run resumes |
| Counts differ from manifest | Publish stops before go-live; differences listed |
| Workflow dispatch fails | Exit non-zero after go-live; `--deploy-only` retries |
| Snapshot build not `ready`, or manifest build id differs | `fetch-snapshot` fails; workflow stops before deploying |
| Build or tests fail in CI | Workflow stops; Hosting keeps the previous release |
| Deployed site missing the build id | Smoke check fails the workflow (the release is already live; roll back in the console if needed) |
| Prune of current or previous build | Refused |

## Testing

### Python unit tests (`tests/publish/`, no network)

- Derived fields: single link, link list (order kept, duplicates removed),
  null link, missing link, non-link fields ignored; browse fields copied;
  `entity` identical to the input.
- Field-name collision detection.
- `firestore.indexes.json` generation: one `entity` override per entity type,
  no composite indexes; the committed file equals the generated one.
- Preflight: wrong `model_version`, missing entity or schema file, missing
  token (and not required with `--no-deploy`).
- Snapshot plan: uploads only missing or changed files (by MD5); never
  deletes.
- Entity writes against a fake Firestore: stale ids deleted; `loading`
  before writes; count mismatch stops before go-live and leaves
  `site/current` untouched; `previous_build_id` rules for a new build and a
  republish.
- Prune refuses current and previous builds and never calls Storage.
- Deploy dispatch: request URL, headers and body; failure message names
  `--deploy-only`.

### Emulator tests (optional)

Skipped unless `FIRESTORE_EMULATOR_HOST` and `FIREBASE_STORAGE_EMULATOR_HOST`
are set (Firebase Emulator Suite; needs Java and `firebase-tools`):

- Publish `web/test/fixtures/model` with `--no-deploy`: documents, counts,
  `builds/{id}` status and `site/current` as expected; a second run changes
  nothing; prune removes a non-current build and refuses the current one.
- **Rules** (`web/test/rules/`, `@firebase/rules-unit-testing`, `npm run
  test:rules`): unauthenticated reads of `site/current`, `builds/{id}` and an
  entity document succeed; writes to each fail; reads of other paths fail;
  Storage reads and writes fail.

### Web unit tests

`fetch-snapshot.ts` with a fake Firestore and bucket: uses `site/current`
without `--build-id`; refuses a `loading` build; fails on a manifest build id
mismatch; writes files under `<out>/<id>/`.

The existing web unit and end-to-end tests stay as they are; CI runs the
unit tests only.

### Acceptance (first real publish of `1eb25ce70f3a`)

- `python -m twwiki.publish` exits 0 and the deploy workflow succeeds.
- `https://twwiii-wiki.web.app/` returns 200 and names `1eb25ce70f3a`; a unit
  page and an image load.
- Firestore counts equal the manifest counts for all 19 types.
- A query on `builds/1eb25ce70f3a/unit` where `abilities_keys` contains
  `wh_main_lord_passive_hold_the_line` returns 18 documents, including
  `wh_main_emp_cha_captain_0`.
- A browser (client SDK) write to `site/current` is rejected.

## Owner setup steps

1. Install the gcloud CLI; run `gcloud auth application-default login`.
2. Confirm Firestore (Native mode) and the default Storage bucket exist. The
   Firestore location cannot be changed once created.
3. Create a deploy service account with the roles above, including Service
   Usage Consumer, Firebase Storage Viewer and Firebase Viewer; store its JSON key
   as the `FIREBASE_SERVICE_ACCOUNT` repository secret, and set the
   `FIREBASE_PROJECT_ID` and `FIREBASE_STORAGE_BUCKET` repository variables.
   Workload Identity Federation (keyless) is the more secure alternative.
4. Create a fine-grained GitHub token for this repository with Actions
   read-and-write; set `TWWIKI_GITHUB_TOKEN` in the publishing environment.
5. In the Firebase console, limit Hosting release retention to 5 releases
   (each about 633 MB).
6. Provide the project id for `config.yaml` and `.firebaserc`.

## Documentation

- README section **Publishing and hosting**: the flow, the publish command
  and its flags, owner setup, recovering from a failed publish or deploy,
  pruning, and costs.
- One-line notes in the three earlier specs pointing to "Decisions revised".

## Out-of-scope follow-ups

- 2d query screens, composite indexes and App Check enforcement.
- Planner bundles, saved builds and share links (4–5).
- Custom domain; preview deploys for pull requests; end-to-end tests in CI.
- Moving the service account key to Workload Identity Federation.
