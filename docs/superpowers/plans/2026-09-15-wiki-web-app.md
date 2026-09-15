# Wiki Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the public, static Total War: WARHAMMER III wiki in `web/` from `model/<build_id>/`: pages for 15 entity types, skill and technology tree views, a region building browser and site-wide search.

**Architecture:** An Astro static site. A prebuild script validates the newest model, generates TypeScript types from its JSON Schemas, copies images and builds a MiniSearch index. A build-time data layer loads the JSONL entities once; one dynamic route renders every entity page through per-type Astro components; React islands handle trees, the region culture picker, search and browse filtering.

**Tech Stack:** Node 22.12, npm, Astro 7.3.2, @astrojs/react 6.0.5, React 19.3.0, MiniSearch 7.2.0, json-schema-to-typescript 16.0.0, tsx 4.23.13, TypeScript 7.0.2, Vitest 5.0.1, Playwright 1.63.0.

**Spec:** `docs/superpowers/specs/2026-09-15-wiki-web-app-design.md`

## Global Constraints

- All web code lives in `web/`; run commands from `web/` with npm. Node `>=22.12.0` (npm warns that `undici`, pulled in by Astro's font helper, wants 22.19; the site does not use it and builds on 22.12).
- Exact dependency versions: `astro` 7.3.2, `@astrojs/react` 6.0.5, `react` 19.3.0, `react-dom` 19.3.0, `minisearch` 7.2.0; dev: `json-schema-to-typescript` 16.0.0, `tsx` 4.23.13, `typescript` 7.0.2, `vitest` 5.0.1, `@types/node` 22.20.3, `@types/react` 19.3.0, `@types/react-dom` 19.3.0, `@playwright/test` 1.63.0 (added in Task 11). Commit `web/package-lock.json`.
- Static output only (`output: "static"`); no server code; `web/dist/` must deploy to any static host.
- Model contract: `model_version` must be 2. The data layer only reads model files through `loadModel`; pages never read files.
- Page types and URL segments (exactly these 15): unit `units`, character `characters`, skill `skills`, ability `abilities`, technology `technologies`, technology_tree `technology-trees`, building_level `buildings`, building_chain `building-chains`, item `items`, trait `traits`, faction `factions`, culture `cultures`, subculture `subcultures`, region `regions`, province `provinces`. Effects, effect bundles, difficulty levels and campaign variables have no pages and are never linked.
- Slug rule: lower-case the key and replace every character outside `[a-z0-9_-]` with `-`; when two keys of the same type produce the same slug, each gets `-` plus the first 6 hex characters of the SHA-1 of its original key. Entity URLs are `/<segment>/<slug>/`.
- Image URLs: `/images/` + the model's lower-case path with each `/`-separated segment passed through `encodeURIComponent`.
- Gaps never fail the build: missing links render the key as text with `data-missing-link`; missing images render a placeholder with `data-placeholder-image`.
- Theme tokens: background `#16120d`, panel `#241c12`, border `#6b5326`, accent border `#8a6d33`, gold `#e2b85c`, muted `#a8925f`, text `#e8dcc2`; serif headings (Georgia), sans-serif body. Dark theme only.
- Git: branch `feature/wiki-web-app` (stacked on `feature/wiki-data-regions-images`). Do not push. Commit with a heredoc message ending in exactly `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Shell is Git Bash on Windows: forward-slash paths; `MODEL_DIR=test/fixtures/model npm run build` sets an environment variable for one command.

---

## File Structure

| Path (under `web/`) | Responsibility | Task |
|---|---|---|
| `package.json`, `package-lock.json`, `astro.config.mjs`, `tsconfig.json`, `vitest.config.ts` | Project setup, scripts | 1 (scripts extended in 3, 9, 10, 11) |
| `src/data/pageTypes.ts` | Entity/page type lists, segments, `hasPage`, `imageUrl` | 1 |
| `src/data/slugs.ts` | `baseSlug`, `buildSlugs` | 1 |
| `src/styles/theme.css` | Tokens and base styles | 1 (extended by later tasks) |
| `src/layouts/Layout.astro` | Page shell | 1 (footer 3, search 9) |
| `scripts/make-fixtures.ts`, `test/fixtures/model/` | Small real sample model | 2 |
| `src/data/load.ts` | `loadModel`, `readJsonl`, `Model`, `ModelLoadError` | 2 |
| `src/data/site.ts` | `createSite`, `urlFor`, `imageSrc`, chains per culture | 2 |
| `src/data/validate.ts` | `findModelDir`, `validateModelDir` | 3 |
| `scripts/prebuild.ts` | Validate, generate types, copy images, build info (search index in 9) | 3 |
| `src/data/model.ts` | `getSite()` memo over `buildInfo.modelDir` | 3 |
| `src/lib/html.ts`, `src/lib/gameText.ts`, `src/lib/effectText.ts` | Escaping, game markup, effect values | 4 |
| `src/data/images.ts` | `mainImage` per entity | 5 |
| `src/components/*.astro` | Shared components | 5 |
| `src/pages/[segment]/[slug].astro`, `src/components/pages/*.astro` | Entity route and per-type page bodies | 5, 6 |
| `src/data/browse.ts`, `src/pages/[segment]/index.astro`, `src/islands/BrowseFilter.tsx` | Browse pages | 6 |
| `src/lib/treeLayout.ts`, `src/lib/detailHtml.ts`, `src/islands/TreeView.tsx`, `src/components/TreeStaticList.astro` | Trees | 7 |
| `src/lib/regionCultures.ts`, `src/pages/data/culture-chains.json.ts`, `src/islands/CulturePicker.tsx` | Region browser | 8 |
| `src/lib/search.ts`, `src/islands/SearchBox.tsx` | Search | 9 |
| `src/pages/index.astro`, `src/pages/404.astro`, `scripts/build-report.ts` | Home, 404, build report | 10 |
| `playwright.config.ts`, `test/e2e/*.spec.ts`, root `README.md` | End-to-end tests, docs | 11 |

---

### Task 1: Scaffold the Astro project with page types and slugs

**Files:**
- Create: `web/package.json`, `web/astro.config.mjs`, `web/tsconfig.json`, `web/vitest.config.ts`
- Create: `web/src/data/pageTypes.ts`, `web/src/data/slugs.ts`
- Create: `web/src/styles/theme.css`, `web/src/layouts/Layout.astro`, `web/src/pages/index.astro`
- Modify: `.gitignore` (repository root)
- Test: `web/test/unit/pageTypes.test.ts`, `web/test/unit/slugs.test.ts`

**Interfaces:**
- Produces:
  - `type EntityType` (19 string literals), `ENTITY_TYPES: readonly EntityType[]`
  - `type PageType`, `interface PageTypeInfo { type: PageType; segment: string; label: string; singular: string }`, `PAGE_TYPES: readonly PageTypeInfo[]`
  - `pageTypeInfo(type: string): PageTypeInfo | undefined`, `pageTypeBySegment(segment: string): PageTypeInfo | undefined`, `hasPage(type: string): type is PageType`
  - `imageUrl(path: string): string`
  - `baseSlug(key: string): string`, `buildSlugs(keys: Iterable<string>): Map<string, string>`
  - `Layout.astro` props `{ title: string; description?: string }`, default slot; named slot `footer`

- [ ] **Step 1: Create the project files**

`web/package.json`:

```json
{
  "name": "twwiki-web",
  "private": true,
  "type": "module",
  "engines": { "node": ">=22.12.0" },
  "scripts": {
    "build": "astro build",
    "dev": "astro dev",
    "preview": "astro preview",
    "test": "vitest run"
  },
  "dependencies": {
    "@astrojs/react": "6.0.5",
    "astro": "7.3.2",
    "minisearch": "7.2.0",
    "react": "19.3.0",
    "react-dom": "19.3.0"
  },
  "devDependencies": {
    "@types/node": "22.20.3",
    "@types/react": "19.3.0",
    "@types/react-dom": "19.3.0",
    "json-schema-to-typescript": "16.0.0",
    "tsx": "4.23.13",
    "typescript": "7.0.2",
    "vitest": "5.0.1"
  }
}
```

`web/astro.config.mjs`:

```js
import { defineConfig } from "astro/config";
import react from "@astrojs/react";

export default defineConfig({
  output: "static",
  integrations: [react()],
  build: { format: "directory" },
});
```

`web/tsconfig.json`:

```json
{
  "extends": "astro/tsconfigs/strict",
  "include": [".astro/types.d.ts", "**/*"],
  "exclude": ["dist", "node_modules"],
  "compilerOptions": { "jsx": "react-jsx", "jsxImportSource": "react" }
}
```

`web/vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: { include: ["test/unit/**/*.test.ts"] },
});
```

Append to the repository root `.gitignore`:

```
/web/node_modules/
/web/dist/
/web/.astro/
/web/public/images/
/web/public/search-index.json
/web/src/generated/
/web/test-results/
/web/playwright-report/
```

- [ ] **Step 2: Install dependencies**

Run (from `web/`): `npm install --no-audit --no-fund`
Expected: `added … packages`; an `EBADENGINE` warning for `undici` is expected and harmless. `package-lock.json` is created.

- [ ] **Step 3: Write the failing tests**

`web/test/unit/pageTypes.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { ENTITY_TYPES, PAGE_TYPES, hasPage, imageUrl, pageTypeBySegment, pageTypeInfo } from "../../src/data/pageTypes";

describe("page types", () => {
  it("lists 19 entity types and 15 page types", () => {
    expect(ENTITY_TYPES).toHaveLength(19);
    expect(PAGE_TYPES.map((p) => p.segment)).toEqual([
      "units", "characters", "skills", "abilities", "technologies", "technology-trees", "buildings",
      "building-chains", "items", "traits", "factions", "cultures", "subcultures", "regions", "provinces",
    ]);
  });

  it("knows which types have pages", () => {
    expect(hasPage("unit")).toBe(true);
    expect(hasPage("building_level")).toBe(true);
    for (const t of ["effect", "effect_bundle", "difficulty_level", "campaign_variable", "nonsense"]) {
      expect(hasPage(t)).toBe(false);
    }
  });

  it("looks up page types by type and segment", () => {
    expect(pageTypeInfo("technology_tree")?.segment).toBe("technology-trees");
    expect(pageTypeBySegment("buildings")?.type).toBe("building_level");
    expect(pageTypeBySegment("effects")).toBeUndefined();
  });

  it("encodes image path segments", () => {
    expect(imageUrl("ui/battle ui/ability_icons/hold.png")).toBe("/images/ui/battle%20ui/ability_icons/hold.png");
  });
});
```

`web/test/unit/slugs.test.ts`:

```ts
import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import { baseSlug, buildSlugs } from "../../src/data/slugs";

const hash6 = (key: string) => createHash("sha1").update(key).digest("hex").slice(0, 6);

describe("slugs", () => {
  it("lower-cases and replaces unsafe characters", () => {
    expect(baseSlug("wh_main_EMPIRE_settlement_major")).toBe("wh_main_empire_settlement_major");
    expect(baseSlug("wh3_main_*_x&y!z'q-r")).toBe("wh3_main_-_x-y-z-q-r");
  });

  it("keeps unique slugs and disambiguates collisions with a hash suffix", () => {
    const slugs = buildSlugs(["wh2_main_skill_LL_self_defense", "wh2_main_skill_ll_self_defense", "wh_main_emp_inf_greatswords"]);
    expect(slugs.get("wh_main_emp_inf_greatswords")).toBe("wh_main_emp_inf_greatswords");
    expect(slugs.get("wh2_main_skill_LL_self_defense")).toBe(`wh2_main_skill_ll_self_defense-${hash6("wh2_main_skill_LL_self_defense")}`);
    expect(slugs.get("wh2_main_skill_ll_self_defense")).toBe(`wh2_main_skill_ll_self_defense-${hash6("wh2_main_skill_ll_self_defense")}`);
    expect(new Set(slugs.values()).size).toBe(3);
  });
});
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `npm test`
Expected: FAIL — cannot resolve `../../src/data/pageTypes` and `../../src/data/slugs`.

- [ ] **Step 5: Implement `web/src/data/pageTypes.ts`**

```ts
export type EntityType =
  | "unit" | "character" | "skill" | "ability" | "effect" | "effect_bundle" | "building_level" | "building_chain"
  | "technology" | "technology_tree" | "item" | "trait" | "faction" | "culture" | "subculture"
  | "difficulty_level" | "campaign_variable" | "region" | "province";

export const ENTITY_TYPES: readonly EntityType[] = [
  "unit", "character", "skill", "ability", "effect", "effect_bundle", "building_level", "building_chain",
  "technology", "technology_tree", "item", "trait", "faction", "culture", "subculture",
  "difficulty_level", "campaign_variable", "region", "province",
];

export type PageType = Exclude<EntityType, "effect" | "effect_bundle" | "difficulty_level" | "campaign_variable">;

export interface PageTypeInfo {
  type: PageType;
  segment: string;
  label: string;
  singular: string;
}

export const PAGE_TYPES: readonly PageTypeInfo[] = [
  { type: "unit", segment: "units", label: "Units", singular: "Unit" },
  { type: "character", segment: "characters", label: "Characters", singular: "Character" },
  { type: "skill", segment: "skills", label: "Skills", singular: "Skill" },
  { type: "ability", segment: "abilities", label: "Abilities", singular: "Ability" },
  { type: "technology", segment: "technologies", label: "Technologies", singular: "Technology" },
  { type: "technology_tree", segment: "technology-trees", label: "Technology trees", singular: "Technology tree" },
  { type: "building_level", segment: "buildings", label: "Buildings", singular: "Building" },
  { type: "building_chain", segment: "building-chains", label: "Building chains", singular: "Building chain" },
  { type: "item", segment: "items", label: "Items", singular: "Item" },
  { type: "trait", segment: "traits", label: "Traits", singular: "Trait" },
  { type: "faction", segment: "factions", label: "Factions", singular: "Faction" },
  { type: "culture", segment: "cultures", label: "Cultures", singular: "Culture" },
  { type: "subculture", segment: "subcultures", label: "Subcultures", singular: "Subculture" },
  { type: "region", segment: "regions", label: "Regions", singular: "Region" },
  { type: "province", segment: "provinces", label: "Provinces", singular: "Province" },
];

const BY_TYPE = new Map(PAGE_TYPES.map((p) => [p.type as string, p]));
const BY_SEGMENT = new Map(PAGE_TYPES.map((p) => [p.segment, p]));

export function pageTypeInfo(type: string): PageTypeInfo | undefined {
  return BY_TYPE.get(type);
}

export function pageTypeBySegment(segment: string): PageTypeInfo | undefined {
  return BY_SEGMENT.get(segment);
}

export function hasPage(type: string): type is PageType {
  return BY_TYPE.has(type);
}

/** Model image paths are lower-case with spaces; encode each segment. */
export function imageUrl(path: string): string {
  return "/images/" + path.split("/").map(encodeURIComponent).join("/");
}
```

- [ ] **Step 6: Implement `web/src/data/slugs.ts`**

```ts
import { createHash } from "node:crypto";

/** Lower-case key with every character outside [a-z0-9_-] replaced by "-". */
export function baseSlug(key: string): string {
  return key.toLowerCase().replace(/[^a-z0-9_-]/g, "-");
}

function shortHash(key: string): string {
  return createHash("sha1").update(key).digest("hex").slice(0, 6);
}

/** Slugs for one entity type; keys whose base slugs collide get a hash suffix. */
export function buildSlugs(keys: Iterable<string>): Map<string, string> {
  const byBase = new Map<string, string[]>();
  for (const key of keys) {
    const base = baseSlug(key);
    const group = byBase.get(base);
    if (group) group.push(key);
    else byBase.set(base, [key]);
  }
  const slugs = new Map<string, string>();
  for (const [base, group] of byBase) {
    if (group.length === 1) slugs.set(group[0], base);
    else for (const key of group) slugs.set(key, `${base}-${shortHash(key)}`);
  }
  return slugs;
}
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `npm test`
Expected: PASS (6 tests).

- [ ] **Step 8: Add the theme, layout and placeholder home page**

`web/src/styles/theme.css`:

```css
:root {
  --bg: #16120d;
  --panel: #241c12;
  --border: #6b5326;
  --border-accent: #8a6d33;
  --gold: #e2b85c;
  --muted: #a8925f;
  --text: #e8dcc2;
  --missing: #c0705a;
  --col-yellow: #e8c547;
  --col-white: #f4efe4;
  --col-red: #d9644a;
  --col-green: #8fc26a;
  --col-magic: #7fb3e8;
  --col-fe-white: #f4efe4;
  --col-ancillary-unique: #d68ce0;
  --serif: Georgia, "Times New Roman", serif;
  --sans: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}

* { box-sizing: border-box; }
html { background: var(--bg); color: var(--text); font: 15px/1.5 var(--sans); }
body { margin: 0; }
h1, h2, h3 { font-family: var(--serif); color: var(--gold); font-weight: normal; margin: 0 0 0.5rem; }
h1 { font-size: 2rem; }
h2 { font-size: 1.35rem; }
h3 { font-size: 1.1rem; }
a { color: var(--gold); text-decoration: none; }
a:hover { text-decoration: underline; }
.muted { color: var(--muted); }

.site-header { border-bottom: 1px solid var(--border); background: #120e0a; }
.site-header .inner, .site-main, .site-footer .inner { max-width: 1200px; margin: 0 auto; padding: 0.75rem 1rem; }
.site-header .inner { display: flex; flex-wrap: wrap; gap: 0.75rem 1.5rem; align-items: center; }
.site-name { font-family: var(--serif); font-size: 1.4rem; color: var(--gold); }
.site-nav { display: flex; flex-wrap: wrap; gap: 0.25rem 0.9rem; font-size: 0.85rem; }
.site-nav a { color: var(--muted); }
.site-footer { border-top: 1px solid var(--border); margin-top: 3rem; color: var(--muted); font-size: 0.8rem; }

.panel { background: var(--panel); border: 1px solid var(--border); padding: 0.9rem 1rem; margin: 0 0 1rem; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; padding: 0.3rem 0.5rem; border-bottom: 1px solid #3a2e1d; vertical-align: top; }
th { color: var(--muted); font-weight: normal; }
.stats th { width: 45%; }

.missing { color: var(--missing); border-bottom: 1px dotted var(--missing); }
.unnamed { font-style: italic; }
```

`web/src/layouts/Layout.astro`:

```astro
---
import "../styles/theme.css";
import { PAGE_TYPES } from "../data/pageTypes";

interface Props {
  title: string;
  description?: string;
}

const { title, description = "Total War: WARHAMMER III game data wiki" } = Astro.props;
---
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content={description} />
    <title>{`${title} — TWW3 Wiki`}</title>
  </head>
  <body>
    <header class="site-header">
      <div class="inner">
        <a class="site-name" href="/">TWW3 Wiki</a>
        <slot name="header" />
        <nav class="site-nav" aria-label="Entity types">
          {PAGE_TYPES.map((p) => <a href={`/${p.segment}/`}>{p.label}</a>)}
        </nav>
      </div>
    </header>
    <main class="site-main">
      <slot />
    </main>
    <footer class="site-footer">
      <div class="inner">
        <slot name="footer">Game data extracted from Total War: WARHAMMER III.</slot>
      </div>
    </footer>
  </body>
</html>
```

`web/src/pages/index.astro`:

```astro
---
import Layout from "../layouts/Layout.astro";
---
<Layout title="Home">
  <h1>TWW3 Wiki</h1>
  <p class="muted">Units, characters, skills, buildings, technologies and regions of Total War: WARHAMMER III.</p>
</Layout>
```

- [ ] **Step 9: Build the scaffold**

Run: `npm run build`
Expected: `1 page(s) built` and `Complete!`; `dist/index.html` exists and contains `TWW3 Wiki`.

- [ ] **Step 10: Commit**

```bash
git add .gitignore web/package.json web/package-lock.json web/astro.config.mjs web/tsconfig.json web/vitest.config.ts web/src web/test
git commit -F - <<'EOF'
feat(web): scaffold Astro wiki with page types and slugs

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 2: Model loader, site derivations and the fixture model

**Files:**
- Create: `web/src/data/modelDir.ts`, `web/src/data/load.ts`, `web/src/data/site.ts`
- Create: `web/scripts/make-fixtures.ts`, `web/test/fixtures/model/**` (generated, committed)
- Modify: `web/package.json` (add `fixtures` script)
- Test: `web/test/unit/modelDir.test.ts`, `web/test/unit/load.test.ts`, `web/test/unit/site.test.ts`

**Interfaces:**
- Consumes: `ENTITY_TYPES`, `EntityType`, `PAGE_TYPES`, `PageType`, `hasPage`, `pageTypeInfo`, `imageUrl` (Task 1); `buildSlugs` (Task 1).
- Produces:
  - `findModelDir(modelRoot: string, env?: NodeJS.ProcessEnv): Promise<string>` — absolute path
  - `class ModelLoadError extends Error`
  - `interface Manifest { build_id: string; model_version: number; generated_at: string; counts: Record<string, number> }`
  - `type EntityMaps = { [T in EntityType]: Map<string, EntityTypeMap[T]> }` (types from `src/generated/index`, created in Task 3; type-only import)
  - `interface Model { dir: string; manifest: Manifest; inline: Record<string, string | null>; entities: EntityMaps }`
  - `readJsonl<T extends { key: string }>(file: string): Promise<Map<string, T>>`, `loadModel(dir: string): Promise<Model>`
  - `interface Site { model: Model; slugs: Record<PageType, Map<string, string>>; chainsByCulture: Map<string, string[]>; images: Set<string> }`
  - `createSite(model: Model): Promise<Site>`, `urlFor(site: Site, type: string, key: string): string | null`, `imageSrc(site: Site, path: string | null | undefined): string | null`
  - `interface AvailabilityRef { culture: { key: string } | null; subculture: { key: string } | null; faction: { key: string } | null }`
  - `chainCultureKeys(availability: AvailabilityRef[], subcultureCulture: (key: string) => string | undefined, factionCulture: (key: string) => string | undefined): Set<string>`

The real model must exist (`model/1eb25ce70f3a/`, produced by sub-project 2a). The fixture generator reads it; unit tests only read the committed fixture.

- [ ] **Step 1: Write the failing tests**

`web/test/unit/modelDir.test.ts`:

```ts
import { mkdtemp, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { findModelDir } from "../../src/data/modelDir";
import { ModelLoadError } from "../../src/data/load";

async function fakeModel(root: string, name: string, generatedAt: string) {
  await mkdir(path.join(root, name), { recursive: true });
  await writeFile(path.join(root, name, "manifest.json"), JSON.stringify({ build_id: name, generated_at: generatedAt }));
}

describe("findModelDir", () => {
  it("uses MODEL_DIR when set", async () => {
    expect(await findModelDir("/unused", { MODEL_DIR: "some/dir" })).toBe(path.resolve("some/dir"));
  });

  it("picks the newest model by generated_at and ignores staging directories", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "models-"));
    await fakeModel(root, "old", "2026-01-01T00:00:00+00:00");
    await fakeModel(root, "new", "2026-09-15T00:00:00+00:00");
    await fakeModel(root, "newer.partial", "2026-12-01T00:00:00+00:00");
    expect(await findModelDir(root, {})).toBe(path.join(root, "new"));
  });

  it("fails clearly when no model exists", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "models-"));
    await expect(findModelDir(root, {})).rejects.toThrow(ModelLoadError);
    await expect(findModelDir(root, {})).rejects.toThrow(/no model found/);
  });
});
```

`web/test/unit/load.test.ts`:

```ts
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { ModelLoadError, loadModel, readJsonl } from "../../src/data/load";

export const FIXTURE = path.resolve(__dirname, "../fixtures/model");

describe("loadModel", () => {
  it("loads the fixture model", async () => {
    const model = await loadModel(FIXTURE);
    expect(model.manifest.model_version).toBe(2);
    expect(model.entities.unit.get("wh_main_emp_inf_greatswords")?.name).toBe("Greatswords");
    expect(model.entities.character.has("wh_main_emp_karl_franz")).toBe(true);
    expect(model.entities.skill.size).toBe(51);
    expect(model.entities.technology.size).toBe(67);
    expect(model.entities.region.size).toBe(4);
    expect(model.entities.building_level.size).toBe(9);
    expect(model.entities.effect_bundle.size).toBe(0);
    expect(typeof model.inline).toBe("object");
  });
});

describe("readJsonl", () => {
  it("names the file and line of invalid JSON", async () => {
    const dir = await mkdtemp(path.join(tmpdir(), "jsonl-"));
    const file = path.join(dir, "unit.jsonl");
    await writeFile(file, '{"key": "a"}\n{not json\n');
    await expect(readJsonl(file)).rejects.toThrow(ModelLoadError);
    await expect(readJsonl(file)).rejects.toThrow(/unit\.jsonl:2: invalid JSON/);
  });

  it("rejects entities without a string key", async () => {
    const dir = await mkdtemp(path.join(tmpdir(), "jsonl-"));
    const file = path.join(dir, "unit.jsonl");
    await writeFile(file, '{"name": "x"}\n');
    await expect(readJsonl(file)).rejects.toThrow(/unit\.jsonl:1: entity has no string "key"/);
  });

  it("skips blank lines", async () => {
    const dir = await mkdtemp(path.join(tmpdir(), "jsonl-"));
    const file = path.join(dir, "unit.jsonl");
    await writeFile(file, '{"key": "a"}\n\n{"key": "b"}\n');
    expect([...(await readJsonl(file)).keys()]).toEqual(["a", "b"]);
  });
});
```

`web/test/unit/site.test.ts`:

```ts
import path from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import { loadModel } from "../../src/data/load";
import { type Site, chainCultureKeys, createSite, imageSrc, urlFor } from "../../src/data/site";

const FIXTURE = path.resolve(__dirname, "../fixtures/model");
let site: Site;

beforeAll(async () => {
  site = await createSite(await loadModel(FIXTURE));
});

describe("createSite", () => {
  it("builds slugs and URLs for page types only", () => {
    expect(site.slugs.unit.get("wh_main_emp_inf_greatswords")).toBe("wh_main_emp_inf_greatswords");
    expect(urlFor(site, "unit", "wh_main_emp_inf_greatswords")).toBe("/units/wh_main_emp_inf_greatswords/");
    expect(urlFor(site, "building_chain", "wh_main_EMPIRE_barracks")).toBe("/building-chains/wh_main_empire_barracks/");
    expect(urlFor(site, "unit", "not_in_model")).toBeNull();
    const effectKey = [...site.model.entities.effect.keys()][0];
    expect(urlFor(site, "effect", effectKey)).toBeNull();
  });

  it("lists chains available per culture", () => {
    const empire = site.chainsByCulture.get("wh_main_emp_empire") ?? [];
    expect(empire).toContain("wh_main_EMPIRE_settlement_major");
    expect(empire).toContain("wh_main_EMPIRE_barracks");
  });

  it("only resolves images that exist", () => {
    expect(site.images.size).toBe(0);
    expect(imageSrc(site, "ui/battle ui/x.png")).toBeNull();
    expect(imageSrc(site, null)).toBeNull();
    site.images.add("ui/battle ui/x.png");
    expect(imageSrc(site, "ui/battle ui/x.png")).toBe("/images/ui/battle%20ui/x.png");
    site.images.delete("ui/battle ui/x.png");
  });
});

describe("chainCultureKeys", () => {
  it("resolves culture directly, via subculture, and via faction", () => {
    const keys = chainCultureKeys(
      [
        { culture: { key: "emp" }, subculture: null, faction: null },
        { culture: null, subculture: { key: "sc_dwf" }, faction: null },
        { culture: null, subculture: null, faction: { key: "f_chs" } },
        { culture: null, subculture: { key: "unknown" }, faction: null },
      ],
      (k) => (k === "sc_dwf" ? "dwf" : undefined),
      (k) => (k === "f_chs" ? "chs" : undefined),
    );
    expect([...keys].sort()).toEqual(["chs", "dwf", "emp"]);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test`
Expected: FAIL — cannot resolve `../../src/data/modelDir`, `../../src/data/load`, `../../src/data/site`.

- [ ] **Step 3: Implement `web/src/data/load.ts`**

```ts
import { createReadStream } from "node:fs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { createInterface } from "node:readline";
import type { EntityTypeMap } from "../generated/index";
import { ENTITY_TYPES, type EntityType } from "./pageTypes";

export class ModelLoadError extends Error {}

export interface Manifest {
  build_id: string;
  model_version: number;
  generated_at: string;
  counts: Record<string, number>;
}

export type EntityMaps = { [T in EntityType]: Map<string, EntityTypeMap[T]> };

export interface Model {
  dir: string;
  manifest: Manifest;
  inline: Record<string, string | null>;
  entities: EntityMaps;
}

export async function readJsonl<T extends { key: string }>(file: string): Promise<Map<string, T>> {
  const rows = new Map<string, T>();
  const lines = createInterface({ input: createReadStream(file, "utf-8"), crlfDelay: Infinity });
  let lineNo = 0;
  for await (const line of lines) {
    lineNo += 1;
    if (!line.trim()) continue;
    let row: unknown;
    try {
      row = JSON.parse(line);
    } catch (e) {
      throw new ModelLoadError(`${file}:${lineNo}: invalid JSON (${(e as Error).message})`);
    }
    const key = (row as { key?: unknown }).key;
    if (typeof key !== "string") throw new ModelLoadError(`${file}:${lineNo}: entity has no string "key"`);
    rows.set(key, row as T);
  }
  return rows;
}

export async function loadModel(dir: string): Promise<Model> {
  const manifest = JSON.parse(await readFile(path.join(dir, "manifest.json"), "utf-8")) as Manifest;
  let inline: Record<string, string | null> = {};
  try {
    inline = JSON.parse(await readFile(path.join(dir, "images", "inline.json"), "utf-8"));
  } catch {
    inline = {};
  }
  const loaded = await Promise.all(
    ENTITY_TYPES.map(async (type) => [type, await readJsonl(path.join(dir, "entities", `${type}.jsonl`))] as const),
  );
  return { dir, manifest, inline, entities: Object.fromEntries(loaded) as unknown as EntityMaps };
}
```

- [ ] **Step 4: Implement `web/src/data/modelDir.ts`**

```ts
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { ModelLoadError } from "./load";

/** MODEL_DIR if set, else the newest model under modelRoot by manifest generated_at. */
export async function findModelDir(modelRoot: string, env: NodeJS.ProcessEnv = process.env): Promise<string> {
  if (env.MODEL_DIR) return path.resolve(env.MODEL_DIR);
  let names: string[] = [];
  try {
    names = await readdir(modelRoot);
  } catch {
    names = [];
  }
  let best: { dir: string; generatedAt: string } | null = null;
  for (const name of names) {
    if (name.endsWith(".partial") || name.endsWith(".old")) continue;
    const dir = path.join(modelRoot, name);
    try {
      const manifest = JSON.parse(await readFile(path.join(dir, "manifest.json"), "utf-8"));
      const generatedAt = String(manifest.generated_at ?? "");
      if (!best || generatedAt > best.generatedAt) best = { dir, generatedAt };
    } catch {
      continue;
    }
  }
  if (!best) {
    throw new ModelLoadError(
      `no model found under ${modelRoot}; run \`uv run python -m twwiki.model\` in the repository root or set MODEL_DIR`,
    );
  }
  return best.dir;
}
```

- [ ] **Step 5: Implement `web/src/data/site.ts`**

```ts
import { readdir } from "node:fs/promises";
import path from "node:path";
import type { Model } from "./load";
import { PAGE_TYPES, hasPage, imageUrl, pageTypeInfo, type PageType } from "./pageTypes";
import { buildSlugs } from "./slugs";

export interface Site {
  model: Model;
  slugs: Record<PageType, Map<string, string>>;
  chainsByCulture: Map<string, string[]>;
  images: Set<string>;
}

export interface AvailabilityRef {
  culture: { key: string } | null;
  subculture: { key: string } | null;
  faction: { key: string } | null;
}

/** Culture keys a chain's availability rows grant, resolving subculture and faction rows to their culture. */
export function chainCultureKeys(
  availability: AvailabilityRef[],
  subcultureCulture: (key: string) => string | undefined,
  factionCulture: (key: string) => string | undefined,
): Set<string> {
  const keys = new Set<string>();
  for (const row of availability) {
    const culture =
      row.culture?.key ??
      (row.subculture ? subcultureCulture(row.subculture.key) : undefined) ??
      (row.faction ? factionCulture(row.faction.key) : undefined);
    if (culture) keys.add(culture);
  }
  return keys;
}

async function listImages(modelDir: string): Promise<Set<string>> {
  const root = path.join(modelDir, "images");
  try {
    const entries = await readdir(root, { recursive: true, withFileTypes: true });
    return new Set(
      entries
        .filter((e) => e.isFile())
        .map((e) => path.relative(root, path.join(e.parentPath, e.name)).split(path.sep).join("/"))
        .filter((p) => p !== "inline.json"),
    );
  } catch {
    return new Set();
  }
}

export async function createSite(model: Model): Promise<Site> {
  const slugs = Object.fromEntries(
    PAGE_TYPES.map((p) => [p.type, buildSlugs(model.entities[p.type].keys())]),
  ) as Record<PageType, Map<string, string>>;

  const subcultureCulture = (key: string) => model.entities.subculture.get(key)?.culture?.key ?? undefined;
  const factionCulture = (key: string) => model.entities.faction.get(key)?.culture?.key ?? undefined;
  const chainsByCulture = new Map<string, string[]>();
  for (const chain of model.entities.building_chain.values()) {
    for (const culture of chainCultureKeys(chain.availability, subcultureCulture, factionCulture)) {
      const list = chainsByCulture.get(culture);
      if (list) list.push(chain.key);
      else chainsByCulture.set(culture, [chain.key]);
    }
  }
  const chainName = (key: string) => model.entities.building_chain.get(key)?.name ?? key;
  for (const list of chainsByCulture.values()) {
    list.sort((a, b) => chainName(a).localeCompare(chainName(b)) || a.localeCompare(b));
  }

  return { model, slugs, chainsByCulture, images: await listImages(model.dir) };
}

/** URL of an entity page, or null when the type has no pages or the key is not in the model. */
export function urlFor(site: Site, type: string, key: string): string | null {
  if (!hasPage(type)) return null;
  const slug = site.slugs[type].get(key);
  return slug ? `/${pageTypeInfo(type)!.segment}/${slug}/` : null;
}

/** Public URL for a model image path, or null when the path is empty or the file was not copied. */
export function imageSrc(site: Site, imagePath: string | null | undefined): string | null {
  return imagePath && site.images.has(imagePath) ? imageUrl(imagePath) : null;
}
```

- [ ] **Step 6: Implement `web/scripts/make-fixtures.ts`**

```ts
/** Regenerate test/fixtures/model from the real model: a small, consistent real subset. */
import { copyFile, cp, mkdir, readFile, rm, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { readJsonl } from "../src/data/load";
import { findModelDir } from "../src/data/modelDir";
import { ENTITY_TYPES, type EntityType } from "../src/data/pageTypes";
import { chainCultureKeys } from "../src/data/site";

type Row = { key: string; [field: string]: any };

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outDir = path.join(webRoot, "test", "fixtures", "model");

function collectEffectKeys(value: unknown, out: Set<string>): void {
  if (Array.isArray(value)) {
    for (const item of value) collectEffectKeys(item, out);
  } else if (value && typeof value === "object") {
    const obj = value as Record<string, unknown>;
    if (obj.type === "effect" && typeof obj.key === "string" && "missing" in obj) out.add(obj.key);
    for (const child of Object.values(obj)) collectEffectKeys(child, out);
  }
}

async function main(): Promise<void> {
  const source = await findModelDir(path.join(webRoot, "..", "model"));
  console.log(`reading ${source}`);
  const all = Object.fromEntries(
    await Promise.all(ENTITY_TYPES.map(async (t) => [t, await readJsonl<Row>(path.join(source, "entities", `${t}.jsonl`))] as const)),
  ) as Record<EntityType, Map<string, Row>>;
  const picked = Object.fromEntries(ENTITY_TYPES.map((t) => [t, new Set<string>()])) as Record<EntityType, Set<string>>;
  const add = (type: EntityType, key: string): Row => {
    const row = all[type].get(key);
    if (!row) throw new Error(`fixture entity ${type}:${key} is not in the model`);
    picked[type].add(key);
    return row;
  };

  add("unit", "wh_main_emp_inf_greatswords");
  const karl = add("character", "wh_main_emp_karl_franz");
  add("unit", karl.associated_unit.key);
  for (const tree of karl.skill_trees) for (const node of tree.nodes) add("skill", node.skill.key);
  add("ability", "wh_main_lord_passive_hold_the_line");
  add("item", "wh2_dlc09_anc_magic_standard_banner_of_the_hidden_dead");
  const techTree = add("technology_tree", "emp_civ_reworkd");
  for (const node of techTree.nodes) add("technology", node.technology.key);
  const province = add("province", "wh3_main_combi_province_reikland");
  for (const region of province.regions) add("region", region.key);
  add("culture", "wh_main_emp_empire");
  add("subculture", "wh_main_sc_emp_empire");
  add("subculture", "wh_main_sc_teb_teb");
  add("faction", "wh_main_emp_empire");

  const subcultureCulture = (k: string) => all.subculture.get(k)?.culture?.key;
  const factionCulture = (k: string) => all.faction.get(k)?.culture?.key;
  for (const chain of all.building_chain.values()) {
    if (chainCultureKeys(chain.availability, subcultureCulture, factionCulture).has("wh_main_emp_empire")) {
      add("building_chain", chain.key);
    }
  }
  for (const chainKey of ["wh_main_EMPIRE_settlement_major", "wh_main_EMPIRE_barracks"]) {
    for (const level of add("building_chain", chainKey).levels) add("building_level", level.key);
  }

  const effects = new Set<string>();
  for (const type of ENTITY_TYPES) {
    if (type === "effect") continue;
    for (const key of picked[type]) collectEffectKeys(all[type].get(key), effects);
  }
  for (const key of effects) if (all.effect.has(key)) add("effect", key);

  await rm(outDir, { recursive: true, force: true });
  await mkdir(path.join(outDir, "entities"), { recursive: true });
  await mkdir(path.join(outDir, "images"), { recursive: true });
  const counts: Record<string, number> = {};
  let bytes = 0;
  for (const type of ENTITY_TYPES) {
    const lines = [...picked[type]].sort().map((key) => JSON.stringify(all[type].get(key)));
    const text = lines.length ? lines.join("\n") + "\n" : "";
    await writeFile(path.join(outDir, "entities", `${type}.jsonl`), text, "utf-8");
    counts[type] = lines.length;
    bytes += Buffer.byteLength(text);
  }
  const manifest = JSON.parse(await readFile(path.join(source, "manifest.json"), "utf-8"));
  await writeFile(
    path.join(outDir, "manifest.json"),
    JSON.stringify({ build_id: manifest.build_id, model_version: manifest.model_version, generated_at: manifest.generated_at, counts }, null, 2) + "\n",
  );
  await copyFile(path.join(source, "images", "inline.json"), path.join(outDir, "images", "inline.json"));
  await cp(path.join(source, "schema"), path.join(outDir, "schema"), { recursive: true });
  console.log(counts);
  console.log(`entity bytes: ${bytes}; inline.json bytes: ${(await stat(path.join(outDir, "images", "inline.json"))).size}`);
}

await main();
```

Add to `web/package.json` `scripts`: `"fixtures": "tsx scripts/make-fixtures.ts"`.

- [ ] **Step 7: Generate the fixture**

Run: `npm run fixtures`
Expected: prints counts including `unit: 2`, `character: 1`, `skill: 51`, `technology: 67`, `technology_tree: 1`, `building_chain: 114`, `building_level: 9`, `region: 4`, `province: 1`, `culture: 1`, `subculture: 2`, `faction: 1`, `item: 1`, `ability: 1`, `effect` about 226, and entity bytes around 1.5 MB (must stay under 3 MB; if larger, stop and report).

- [ ] **Step 8: Run tests to verify they pass**

Run: `npm test`
Expected: PASS (all tests in `modelDir`, `load`, `site`, `pageTypes`, `slugs`).

- [ ] **Step 9: Commit**

```bash
git add web/package.json web/src/data web/scripts/make-fixtures.ts web/test
git commit -F - <<'EOF'
feat(web): load the model, derive slugs and culture chains, add fixture model

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 3: Prebuild — validate the model, generate types, copy images

**Files:**
- Create: `web/src/data/validate.ts`, `web/scripts/prebuild.ts`, `web/src/data/model.ts`
- Modify: `web/package.json` (scripts), `web/src/layouts/Layout.astro` (footer)
- Test: `web/test/unit/validate.test.ts`

**Interfaces:**
- Consumes: `findModelDir`, `ModelLoadError`, `Manifest`, `loadModel` (Task 2); `createSite`, `Site` (Task 2); `ENTITY_TYPES` (Task 1).
- Produces:
  - `MODEL_VERSION = 2`, `validateModelDir(dir: string): Promise<Manifest>`
  - Generated (git-ignored) `src/generated/<type>.ts` for all 19 types, each exporting the entity interface named in PascalCase (`Unit`, `EffectBundle`, `BuildingLevel`, `TechnologyTree`, …) plus nested interfaces (`Link`, `EffectApplication`, …)
  - Generated `src/generated/index.ts`: `export type { Unit } from "./unit";` for every type and `export interface EntityTypeMap { unit: Unit; … }`
  - Generated `src/generated/build-info.ts`: `export const buildInfo = { buildId, generatedAt, modelDir, counts } as const`
  - `getSite(): Promise<Site>` (memoised) and re-export `buildInfo` from `src/data/model.ts`
  - `public/images/` = model `images/` plus `.build-id` marker containing `<build_id>:<modelDir>`

- [ ] **Step 1: Write the failing test**

`web/test/unit/validate.test.ts`:

```ts
import { mkdtemp, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { ModelLoadError } from "../../src/data/load";
import { MODEL_VERSION, validateModelDir } from "../../src/data/validate";

const FIXTURE = path.resolve(__dirname, "../fixtures/model");

async function tempModel(manifest: object | null, entityTypes: string[]): Promise<string> {
  const dir = await mkdtemp(path.join(tmpdir(), "model-"));
  await mkdir(path.join(dir, "entities"));
  if (manifest) await writeFile(path.join(dir, "manifest.json"), JSON.stringify(manifest));
  for (const t of entityTypes) await writeFile(path.join(dir, "entities", `${t}.jsonl`), "");
  return dir;
}

describe("validateModelDir", () => {
  it("accepts the fixture model", async () => {
    const manifest = await validateModelDir(FIXTURE);
    expect(manifest.model_version).toBe(MODEL_VERSION);
    expect(typeof manifest.build_id).toBe("string");
  });

  it("rejects a directory without manifest.json", async () => {
    const dir = await tempModel(null, []);
    await expect(validateModelDir(dir)).rejects.toThrow(ModelLoadError);
    await expect(validateModelDir(dir)).rejects.toThrow(/manifest\.json is missing/);
  });

  it("rejects another model version", async () => {
    const dir = await tempModel({ build_id: "x", model_version: 1, generated_at: "", counts: {} }, []);
    await expect(validateModelDir(dir)).rejects.toThrow(/model_version 1, expected 2/);
  });

  it("lists missing entity files", async () => {
    const dir = await tempModel({ build_id: "x", model_version: 2, generated_at: "", counts: {} }, ["unit"]);
    await expect(validateModelDir(dir)).rejects.toThrow(/missing entity files: character\.jsonl/);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run test/unit/validate.test.ts`
Expected: FAIL — cannot resolve `../../src/data/validate`.

- [ ] **Step 3: Implement `web/src/data/validate.ts`**

```ts
import { access, readFile } from "node:fs/promises";
import path from "node:path";
import { ModelLoadError, type Manifest } from "./load";
import { ENTITY_TYPES } from "./pageTypes";

export const MODEL_VERSION = 2;

export async function validateModelDir(dir: string): Promise<Manifest> {
  let manifest: Manifest;
  try {
    manifest = JSON.parse(await readFile(path.join(dir, "manifest.json"), "utf-8"));
  } catch {
    throw new ModelLoadError(`${dir}: manifest.json is missing or unreadable`);
  }
  if (manifest.model_version !== MODEL_VERSION) {
    throw new ModelLoadError(
      `${dir}: model_version ${manifest.model_version}, expected ${MODEL_VERSION}; rebuild the model with \`uv run python -m twwiki.model\``,
    );
  }
  const missing: string[] = [];
  for (const type of ENTITY_TYPES) {
    try {
      await access(path.join(dir, "entities", `${type}.jsonl`));
    } catch {
      missing.push(`${type}.jsonl`);
    }
  }
  if (missing.length) throw new ModelLoadError(`${dir}: missing entity files: ${missing.join(", ")}`);
  return manifest;
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npx vitest run test/unit/validate.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Implement `web/scripts/prebuild.ts`**

```ts
/** Runs before `astro build` (npm prebuild hook) and `npm run dev`. */
import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { compileFromFile } from "json-schema-to-typescript";
import { ModelLoadError, type Manifest } from "../src/data/load";
import { findModelDir } from "../src/data/modelDir";
import { ENTITY_TYPES } from "../src/data/pageTypes";
import { validateModelDir } from "../src/data/validate";

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const generatedDir = path.join(webRoot, "src", "generated");

function pascalCase(type: string): string {
  return type
    .split("_")
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join("");
}

async function generateTypes(modelDir: string): Promise<void> {
  await rm(generatedDir, { recursive: true, force: true });
  await mkdir(generatedDir, { recursive: true });
  for (const type of ENTITY_TYPES) {
    const source = await compileFromFile(path.join(modelDir, "schema", `${type}.schema.json`), {
      bannerComment: `// Generated from ${type}.schema.json by scripts/prebuild.ts. Do not edit.`,
      additionalProperties: false,
    });
    await writeFile(path.join(generatedDir, `${type}.ts`), source);
  }
  const reexports = ENTITY_TYPES.map((t) => `export type { ${pascalCase(t)} } from "./${t}";`).join("\n");
  const imports = ENTITY_TYPES.map((t) => `import type { ${pascalCase(t)} } from "./${t}";`).join("\n");
  const fields = ENTITY_TYPES.map((t) => `  ${t}: ${pascalCase(t)};`).join("\n");
  await writeFile(
    path.join(generatedDir, "index.ts"),
    `// Generated by scripts/prebuild.ts. Do not edit.\n${reexports}\n${imports}\n\nexport interface EntityTypeMap {\n${fields}\n}\n`,
  );
}

async function copyImages(modelDir: string, buildId: string): Promise<void> {
  const target = path.join(webRoot, "public", "images");
  const marker = path.join(target, ".build-id");
  const wanted = `${buildId}:${modelDir}`;
  const current = await readFile(marker, "utf-8").catch(() => "");
  if (current === wanted) {
    console.log("prebuild: images up to date");
    return;
  }
  await rm(target, { recursive: true, force: true });
  try {
    await cp(path.join(modelDir, "images"), target, { recursive: true });
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code !== "ENOENT") throw e;
  }
  await mkdir(target, { recursive: true });
  await writeFile(marker, wanted);
  console.log(`prebuild: images copied from ${modelDir}`);
}

async function writeBuildInfo(modelDir: string, manifest: Manifest): Promise<void> {
  const info = {
    buildId: manifest.build_id,
    generatedAt: manifest.generated_at,
    modelDir: modelDir.split(path.sep).join("/"),
    counts: manifest.counts,
  };
  await writeFile(
    path.join(generatedDir, "build-info.ts"),
    `// Generated by scripts/prebuild.ts. Do not edit.\nexport const buildInfo = ${JSON.stringify(info, null, 2)} as const;\n`,
  );
}

async function prebuild(): Promise<void> {
  const modelDir = await findModelDir(path.join(webRoot, "..", "model"));
  const manifest = await validateModelDir(modelDir);
  console.log(`prebuild: model ${manifest.build_id} at ${modelDir}`);
  await generateTypes(modelDir);
  await copyImages(modelDir, manifest.build_id);
  await writeBuildInfo(modelDir, manifest);
}

try {
  await prebuild();
} catch (e) {
  console.error(e instanceof ModelLoadError ? `prebuild failed: ${e.message}` : e);
  process.exit(1);
}
```

- [ ] **Step 6: Implement `web/src/data/model.ts`**

```ts
import { buildInfo } from "../generated/build-info";
import { loadModel } from "./load";
import { createSite, type Site } from "./site";

let site: Promise<Site> | undefined;

/** The whole site's data, loaded once per build from the model the prebuild validated. */
export function getSite(): Promise<Site> {
  site ??= loadModel(buildInfo.modelDir).then(createSite);
  return site;
}

export { buildInfo };
```

- [ ] **Step 7: Wire the scripts and footer**

In `web/package.json` set `scripts` to:

```json
{
  "prebuild": "tsx scripts/prebuild.ts",
  "build": "astro build",
  "dev": "tsx scripts/prebuild.ts && astro dev",
  "preview": "astro preview",
  "test": "vitest run",
  "fixtures": "tsx scripts/make-fixtures.ts"
}
```

In `web/src/layouts/Layout.astro`, add to the frontmatter:

```ts
import { buildInfo } from "../data/model";
```

and replace the footer slot line with:

```astro
<slot name="footer">Game build <code>{buildInfo.buildId}</code> · data model generated {buildInfo.generatedAt.slice(0, 10)} · Total War: WARHAMMER III</slot>
```

- [ ] **Step 8: Run the prebuild and build against the fixture**

Run: `MODEL_DIR=test/fixtures/model npm run build`
Expected: `prebuild: model 1eb25ce70f3a at …/test/fixtures/model`, then Astro `Complete!`. `src/generated/` contains 19 `<type>.ts` files, `index.ts` and `build-info.ts`; `dist/index.html` contains `Game build`.

- [ ] **Step 9: Check the real model is picked by default**

Run: `npm run prebuild`
Expected: `prebuild: model 1eb25ce70f3a at …/model/1eb25ce70f3a` and `images copied`; `public/images/ui/units/icons/` exists.

Run: `EMPTY=$(mktemp -d) && MODEL_DIR="$EMPTY" npm run prebuild; echo "exit=$?"`
Expected: `prebuild failed: …empty-model: manifest.json is missing or unreadable` and `exit=1`. (Never move or edit files under `../model/`.)

- [ ] **Step 10: Run all unit tests**

Run: `npm test`
Expected: PASS.

- [ ] **Step 11: Commit**

```bash
git add web/package.json web/scripts/prebuild.ts web/src/data/validate.ts web/src/data/model.ts web/src/layouts/Layout.astro web/test/unit/validate.test.ts
git commit -F - <<'EOF'
feat(web): prebuild validates the model, generates types and copies images

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 4: Game text and effect value formatting

**Files:**
- Create: `web/src/lib/html.ts`, `web/src/lib/gameText.ts`, `web/src/lib/effectText.ts`
- Modify: `web/src/styles/theme.css` (game text classes)
- Test: `web/test/unit/gameText.test.ts`, `web/test/unit/effectText.test.ts`

**Interfaces:**
- Produces:
  - `escapeHtml(text: string): string`
  - `type GameNode = { kind: "text"; text: string } | { kind: "br" } | { kind: "img"; target: string } | { kind: "span"; style: "bold" | "italic" | "help" | "colour"; colour: string | null; children: GameNode[] }`
  - `interface ParsedGameText { title: GameNode[] | null; body: GameNode[] }`, `parseGameText(text: string): ParsedGameText`
  - `KNOWN_COLOURS` (7 names), `interface GameTextImages { inline: Record<string, string | null>; src: (path: string) => string | null }`
  - `renderGameTextHtml(text: string | null | undefined, images: GameTextImages): string`
  - `formatNumber(value: number): string`, `signed(value: number): string`, `formatEffect(description: string | null, key: string, value: number): string`, `scopeLabel(scope: string | null): string | null`

- [ ] **Step 1: Write the failing tests**

`web/test/unit/gameText.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { type GameTextImages, parseGameText, renderGameTextHtml } from "../../src/lib/gameText";

const images: GameTextImages = {
  inline: { icon_hero: "ui/skins/default/icon_agent_small.png", icon_gone: null },
  src: (p) => `/images/${p}`,
};
const html = (text: string | null) => renderGameTextHtml(text, images);
const PLACEHOLDER = '<span class="game-img game-img-inline placeholder" data-placeholder-image aria-hidden="true"></span>';

describe("parseGameText", () => {
  it("builds a node tree", () => {
    expect(parseGameText("[[b]]x")).toEqual({
      title: null,
      body: [{ kind: "span", style: "bold", colour: null, children: [{ kind: "text", text: "x" }] }],
    });
  });

  it("splits a title at the first ||", () => {
    const parsed = parseGameText("Rampage||A unit||more");
    expect(parsed.title).toEqual([{ kind: "text", text: "Rampage" }]);
    expect(parsed.body).toEqual([{ kind: "text", text: "A unit||more" }]);
  });
});

describe("renderGameTextHtml", () => {
  it("escapes plain text and handles empty input", () => {
    expect(html("a < b & \"c\"")).toBe("a &lt; b &amp; &quot;c&quot;");
    expect(html(null)).toBe("");
    expect(html("")).toBe("");
  });

  it("renders bold, italic, help and colour tags", () => {
    expect(html("[[b]]x[[/b]] [[i]]y[[/i]] [[sl:campaign_armies]]z[[/sl]] [[col:red]]r[[/col]]")).toBe(
      '<strong>x</strong> <em>y</em> <span class="gt-help">z</span> <span class="gt-col gt-col-red">r</span>',
    );
    expect(html("[[overridecol:fe_white]]w[[/overridecol]]")).toBe('<span class="gt-col gt-col-fe-white">w</span>');
    expect(html("[[col:blue]]b[[/col]]")).toBe('<span class="gt-col">b</span>');
  });

  it("tolerates nesting, mismatched, stray and unclosed tags", () => {
    expect(html("A [[b]][[col:red]]Rampaging[[/col]][[/b]] unit")).toBe(
      'A <strong><span class="gt-col gt-col-red">Rampaging</span></strong> unit',
    );
    expect(html("[[b]]Corrupt Units[[/i]] allows")).toBe("<strong>Corrupt Units</strong> allows");
    expect(html("[[b]]open")).toBe("<strong>open</strong>");
    expect(html("x[[/b]]y")).toBe("xy");
  });

  it("turns literal and real newlines into line breaks", () => {
    expect(html("a\\nb")).toBe("a<br>b");
    expect(html("a\nb")).toBe("a<br>b");
  });

  it("renders a title line", () => {
    expect(html("Rampage||A [[b]]unit[[/b]]")).toBe('<span class="gt-title">Rampage</span>A <strong>unit</strong>');
  });

  it("shows unresolved and unknown tokens as text", () => {
    expect(html("{{tr:research}}: [[foo:bar]] [[baz]]")).toBe("tr:research: foo:bar baz");
  });

  it("renders inline icons through inline.json and placeholders otherwise", () => {
    expect(html("[[img:icon_hero]][[/img]]Hero")).toBe(
      '<img class="game-img game-img-inline" src="/images/ui/skins/default/icon_agent_small.png" alt="" loading="lazy" decoding="async">Hero',
    );
    expect(html("[[img:icon_gone]][[/img]]")).toBe(PLACEHOLDER);
    expect(html("[[img:unknown]][[/img]]")).toBe(PLACEHOLDER);
  });

  it("shows a placeholder when the resolved image file is not available", () => {
    const noFiles: GameTextImages = { inline: images.inline, src: () => null };
    expect(renderGameTextHtml("[[img:icon_hero]][[/img]]", noFiles)).toBe(PLACEHOLDER);
  });
});
```

`web/test/unit/effectText.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { formatEffect, formatNumber, scopeLabel, signed } from "../../src/lib/effectText";

describe("numbers", () => {
  it("drops trailing zeros and rounds to two decimals", () => {
    expect(formatNumber(2)).toBe("2");
    expect(formatNumber(2.0)).toBe("2");
    expect(formatNumber(0.333333)).toBe("0.33");
    expect(formatNumber(-12.5)).toBe("-12.5");
  });

  it("signs values", () => {
    expect(signed(4)).toBe("+4");
    expect(signed(-5)).toBe("-5");
    expect(signed(0)).toBe("+0");
  });
});

describe("formatEffect", () => {
  it("substitutes signed and unsigned placeholders", () => {
    expect(formatEffect("Melee attack: %+n", "e", 4)).toBe("Melee attack: +4");
    expect(formatEffect("Melee attack: %+n", "e", -5)).toBe("Melee attack: -5");
    expect(formatEffect("Recruitment cost: %+n%", "e", -10)).toBe("Recruitment cost: -10%");
    expect(formatEffect("Armour: %n", "e", 20)).toBe("Armour: 20");
    expect(formatEffect("Chance: %n%", "e", 12.5)).toBe("Chance: 12.5%");
    expect(formatEffect("Odd: %-n%", "e", 7)).toBe("Odd: 7%");
  });

  it("appends the value when there is no placeholder or no description", () => {
    expect(formatEffect("Enables Rampage", "e", 1)).toBe("Enables Rampage (+1)");
    expect(formatEffect(null, "wh_effect_x", 3)).toBe("wh_effect_x (+3)");
  });
});

describe("scopeLabel", () => {
  it("humanises scopes", () => {
    expect(scopeLabel("faction_to_force_own")).toBe("faction to force own");
    expect(scopeLabel(null)).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run test/unit/gameText.test.ts test/unit/effectText.test.ts`
Expected: FAIL — cannot resolve `../../src/lib/gameText` and `../../src/lib/effectText`.

- [ ] **Step 3: Implement `web/src/lib/html.ts`**

```ts
export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
```

- [ ] **Step 4: Implement `web/src/lib/gameText.ts`**

```ts
/** Game UI markup: [[b]], [[i]], [[sl:…]], [[col:…]], [[overridecol:…]], [[img:…]], {{…}}, \n and title||body. */
import { escapeHtml } from "./html";

export type GameNode =
  | { kind: "text"; text: string }
  | { kind: "br" }
  | { kind: "img"; target: string }
  | { kind: "span"; style: "bold" | "italic" | "help" | "colour"; colour: string | null; children: GameNode[] };

type SpanNode = Extract<GameNode, { kind: "span" }>;

export interface ParsedGameText {
  title: GameNode[] | null;
  body: GameNode[];
}

export interface GameTextImages {
  inline: Record<string, string | null>;
  src: (path: string) => string | null;
}

export const KNOWN_COLOURS: readonly string[] = ["yellow", "white", "red", "green", "magic", "fe_white", "ancillary_unique"];

// [[/name:arg]] tags, {{…}} tokens, a literal backslash-n, or a real newline.
const TOKEN = /\[\[(\/?)([A-Za-z_]+)(?::([^\]]*))?\]\]|\{\{([^}]*)\}\}|\\n|\r?\n/g;

const STYLES: Record<string, SpanNode["style"]> = { b: "bold", i: "italic", sl: "help", col: "colour", overridecol: "colour" };

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
    const [, closing, name, arg, braces] = match;
    if (braces !== undefined) {
      pushText(braces);
      continue;
    }
    if (name === undefined) {
      current().push({ kind: "br" });
      continue;
    }
    const tag = name.toLowerCase();
    if (closing) {
      // Game data sometimes closes the wrong tag: close the innermost open one. [[/img]] closes nothing.
      if (tag !== "img" && stack.length) stack.pop();
      continue;
    }
    if (tag === "img") {
      if (arg) current().push({ kind: "img", target: arg });
      continue;
    }
    const style = STYLES[tag];
    if (!style) {
      pushText(arg !== undefined ? `${name}:${arg}` : name);
      continue;
    }
    const span: SpanNode = { kind: "span", style, colour: style === "colour" ? (arg ?? null) : null, children: [] };
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
          const inner = renderNodes(node.children, images);
          if (node.style === "bold") return `<strong>${inner}</strong>`;
          if (node.style === "italic") return `<em>${inner}</em>`;
          if (node.style === "help") return `<span class="gt-help">${inner}</span>`;
          const colourClass =
            node.colour && KNOWN_COLOURS.includes(node.colour) ? ` gt-col-${node.colour.replace(/_/g, "-")}` : "";
          return `<span class="gt-col${colourClass}">${inner}</span>`;
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
```

- [ ] **Step 5: Implement `web/src/lib/effectText.ts`**

```ts
export function formatNumber(value: number): string {
  return String(Number.isInteger(value) ? value : Number(value.toFixed(2)));
}

export function signed(value: number): string {
  const text = formatNumber(value);
  return value >= 0 ? `+${text}` : text;
}

/** Fill %+n, %n, %+n%, %n% and %-n% with the value; append the value when there is no placeholder. */
export function formatEffect(description: string | null, key: string, value: number): string {
  if (!description) return `${key} (${signed(value)})`;
  let substituted = false;
  const text = description.replace(/%([+-]?)n(%?)/g, (_match, sign: string, percent: string) => {
    substituted = true;
    return (sign === "+" ? signed(value) : formatNumber(value)) + percent;
  });
  return substituted ? text : `${description} (${signed(value)})`;
}

export function scopeLabel(scope: string | null): string | null {
  return scope ? scope.replace(/_/g, " ") : null;
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `npx vitest run test/unit/gameText.test.ts test/unit/effectText.test.ts`
Expected: PASS.

- [ ] **Step 7: Add game text styles**

Append to `web/src/styles/theme.css`:

```css
.gt-title { display: block; font-family: var(--serif); color: var(--gold); margin-bottom: 0.2rem; }
.gt-help { color: var(--gold); border-bottom: 1px dotted var(--border-accent); }
.gt-col-yellow { color: var(--col-yellow); }
.gt-col-white { color: var(--col-white); }
.gt-col-red { color: var(--col-red); }
.gt-col-green { color: var(--col-green); }
.gt-col-magic { color: var(--col-magic); }
.gt-col-fe-white { color: var(--col-fe-white); }
.gt-col-ancillary-unique { color: var(--col-ancillary-unique); }

.game-img { display: inline-block; object-fit: contain; vertical-align: middle; }
.game-img.placeholder { background: #3a2e1d; border: 1px solid var(--border-accent); }
.game-img-inline { width: 1.1em; height: 1.1em; margin: 0 0.15em; }
.game-img-icon { width: 24px; height: 24px; }
.game-img-large { width: 64px; height: 64px; }
.game-img-card { width: 60px; height: 130px; }
.game-img-portrait { width: 96px; height: 96px; }
.game-img-flag { width: 64px; height: 64px; }
```

- [ ] **Step 8: Run all unit tests and commit**

Run: `npm test`
Expected: PASS.

```bash
git add web/src/lib web/src/styles/theme.css web/test/unit/gameText.test.ts web/test/unit/effectText.test.ts
git commit -F - <<'EOF'
feat(web): render game text markup and effect values

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 5: Shared components, the entity route, and the first five page types

**Files:**
- Create: `web/src/data/images.ts`
- Create: `web/src/components/GameImage.astro`, `EntityLink.astro`, `GameText.astro`, `EffectList.astro`, `StatTable.astro`, `Section.astro`, `LinkList.astro`, `ResourceCost.astro`, `EntityHeader.astro` (all under `web/src/components/`)
- Create: `web/src/components/pages/registry.ts`, `UnitPage.astro`, `AbilityPage.astro`, `SkillPage.astro`, `ItemPage.astro`, `TraitPage.astro` (under `web/src/components/pages/`)
- Create: `web/src/pages/[segment]/[slug].astro`
- Modify: `web/src/styles/theme.css`
- Test: `web/test/unit/images.test.ts`

**Interfaces:**
- Consumes: `getSite`, `buildInfo` (Task 3); `Site`, `urlFor`, `imageSrc` (Task 2); `PAGE_TYPES`, `pageTypeInfo`, `PageType`, `hasPage` (Task 1); `renderGameTextHtml`, `formatEffect`, `formatNumber`, `scopeLabel` (Task 4); generated types via `site.model.entities`.
- Produces:
  - `type ImageKind = "icon" | "card" | "portrait" | "flag"`, `interface EntityImage { path: string | null; kind: ImageKind }`, `mainImage(site: Site, type: string, entity: Record<string, any>): EntityImage | null`
  - Components and props: `GameImage { path: string | null | undefined; kind: ImageKind | "large" | "inline"; alt?: string }`; `EntityLink { link: { type: string; key: string; name: string | null; missing: boolean } | null; showIcon?: boolean }`; `GameText { text: string | null | undefined; block?: boolean }`; `EffectList { applications: EffectApplication-like[] }`; `StatTable { rows: [string, string | number | boolean | null | undefined][] }`; `Section { title: string; show?: boolean }` with default slot; `LinkList { links: (Link | null)[] }`; `ResourceCost { cost: ResourceCost | null }`; `EntityHeader { type: PageType; entityKey: string; name: string | null; image: EntityImage | null }`
  - `PAGE_BODIES` in `components/pages/registry.ts`: map from page type to a body component taking `{ entityKey: string }`. Task 6 adds the remaining ten types; the route only generates pages for registered types.

- [ ] **Step 1: Write the failing test**

`web/test/unit/images.test.ts`:

```ts
import path from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import { mainImage } from "../../src/data/images";
import { loadModel } from "../../src/data/load";
import { type Site, createSite } from "../../src/data/site";

const FIXTURE = path.resolve(__dirname, "../fixtures/model");
let site: Site;
const get = (type: string, key: string) => (site.model.entities as any)[type].get(key);

beforeAll(async () => {
  site = await createSite(await loadModel(FIXTURE));
});

describe("mainImage", () => {
  it("uses the unit card, falling back to the portrait", () => {
    const gs = get("unit", "wh_main_emp_inf_greatswords");
    expect(mainImage(site, "unit", gs)).toEqual({ path: gs.card_image, kind: "card" });
    expect(mainImage(site, "unit", { card_image: null, portrait_image: "p.png" })).toEqual({ path: "p.png", kind: "portrait" });
  });

  it("uses the associated unit's portrait for characters", () => {
    const karl = get("character", "wh_main_emp_karl_franz");
    const unit = get("unit", karl.associated_unit.key);
    expect(mainImage(site, "character", karl)).toEqual({ path: unit.portrait_image ?? unit.card_image ?? null, kind: "portrait" });
  });

  it("uses flags for factions, icons for icon types, nothing for others", () => {
    const faction = get("faction", "wh_main_emp_empire");
    expect(mainImage(site, "faction", faction)).toEqual({ path: faction.flag_image, kind: "flag" });
    const skill = [...site.model.entities.skill.values()][0];
    expect(mainImage(site, "skill", skill)).toEqual({ path: skill.icon_image, kind: "icon" });
    expect(mainImage(site, "region", get("region", "wh3_main_combi_region_altdorf"))).toBeNull();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run test/unit/images.test.ts`
Expected: FAIL — cannot resolve `../../src/data/images`.

- [ ] **Step 3: Implement `web/src/data/images.ts`**

```ts
import type { Site } from "./site";

export type ImageKind = "icon" | "card" | "portrait" | "flag";

export interface EntityImage {
  path: string | null;
  kind: ImageKind;
}

const ICON_TYPES = new Set(["skill", "ability", "technology", "building_level", "item", "trait", "effect", "effect_bundle"]);

/** The picture that represents an entity in headers, links and search results. */
export function mainImage(site: Site, type: string, entity: Record<string, any>): EntityImage | null {
  if (type === "unit") {
    return entity.card_image ? { path: entity.card_image, kind: "card" } : { path: entity.portrait_image ?? null, kind: "portrait" };
  }
  if (type === "character") {
    const unit = entity.associated_unit ? site.model.entities.unit.get(entity.associated_unit.key) : undefined;
    return { path: unit?.portrait_image ?? unit?.card_image ?? null, kind: "portrait" };
  }
  if (type === "faction") return { path: entity.flag_image ?? null, kind: "flag" };
  if (ICON_TYPES.has(type)) return { path: entity.icon_image ?? null, kind: "icon" };
  return null;
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npx vitest run test/unit/images.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Create the shared components**

`web/src/components/GameImage.astro`:

```astro
---
import type { ImageKind } from "../data/images";
import { getSite } from "../data/model";
import { imageSrc } from "../data/site";

interface Props {
  path: string | null | undefined;
  kind: ImageKind | "large" | "inline";
  alt?: string;
}

const { path, kind, alt = "" } = Astro.props;
const site = await getSite();
const src = imageSrc(site, path);
---
{src
  ? <img class={`game-img game-img-${kind}`} src={src} alt={alt} loading="lazy" decoding="async" />
  : <span class={`game-img game-img-${kind} placeholder`} data-placeholder-image aria-hidden="true"></span>}
```

`web/src/components/GameText.astro`:

```astro
---
import { getSite } from "../data/model";
import { imageSrc } from "../data/site";
import { renderGameTextHtml } from "../lib/gameText";

interface Props {
  text: string | null | undefined;
  block?: boolean;
}

const { text, block = false } = Astro.props;
const site = await getSite();
const html = renderGameTextHtml(text, { inline: site.model.inline, src: (p) => imageSrc(site, p) });
const Tag = block ? "p" : "span";
---
{html && <Tag class="game-text" set:html={html} />}
```

`web/src/components/EntityLink.astro`:

```astro
---
import { mainImage } from "../data/images";
import { getSite } from "../data/model";
import { urlFor } from "../data/site";
import GameImage from "./GameImage.astro";
import GameText from "./GameText.astro";

interface Props {
  link: { type: string; key: string; name: string | null; missing: boolean } | null;
  showIcon?: boolean;
}

const { link, showIcon = true } = Astro.props;
const site = await getSite();
const url = link && !link.missing ? urlFor(site, link.type, link.key) : null;
const entity = link && url ? (site.model.entities as Record<string, Map<string, Record<string, any>>>)[link.type]?.get(link.key) : undefined;
const image = link && entity && showIcon ? mainImage(site, link.type, entity) : null;
---
{link && (url
  ? (
    <a class="entity-link" href={url}>
      {image && <GameImage path={image.path} kind="icon" />}
      <span class:list={[{ unnamed: !link.name }]}>{link.name ? <GameText text={link.name} /> : link.key}</span>
    </a>
  )
  : link.missing
    ? <span class="entity-link missing" data-missing-link title="Not in the game data">{link.name ?? link.key}</span>
    : <span class="entity-link">{link.name ? <GameText text={link.name} /> : link.key}</span>)}
```

`web/src/components/EffectList.astro`:

```astro
---
import { getSite } from "../data/model";
import { formatEffect, formatNumber, scopeLabel } from "../lib/effectText";
import GameImage from "./GameImage.astro";
import GameText from "./GameText.astro";

interface Application {
  effect: { key: string };
  scope: string | null;
  value: number;
  value_damaged?: number | null;
  value_ruined?: number | null;
  context_requirement?: string | null;
  advancement_stage?: string | null;
}

interface Props {
  applications: Application[];
}

const site = await getSite();
const rows = Astro.props.applications.map((application) => {
  const effect = site.model.entities.effect.get(application.effect.key);
  return {
    application,
    icon: effect?.icon_image ?? null,
    text: formatEffect(effect?.description ?? null, application.effect.key, application.value),
  };
});
---
{rows.length > 0 && (
  <ul class="effect-list">
    {rows.map(({ application: a, icon, text }) => (
      <li>
        <GameImage path={icon} kind="icon" />
        <span class="effect-text"><GameText text={text} /></span>
        {scopeLabel(a.scope) && <span class="muted effect-note">{scopeLabel(a.scope)}</span>}
        {a.value_damaged != null && <span class="muted effect-note">damaged {formatNumber(a.value_damaged)}</span>}
        {a.value_ruined != null && <span class="muted effect-note">ruined {formatNumber(a.value_ruined)}</span>}
        {a.context_requirement && <span class="muted effect-note">when {a.context_requirement}</span>}
        {a.advancement_stage && <span class="muted effect-note">{a.advancement_stage.replace(/_/g, " ")}</span>}
      </li>
    ))}
  </ul>
)}
```

`web/src/components/StatTable.astro`:

```astro
---
import { formatNumber } from "../lib/effectText";

interface Props {
  rows: [string, string | number | boolean | null | undefined][];
}

const shown = Astro.props.rows.filter(([, value]) => value !== null && value !== undefined && value !== "");
const display = (value: string | number | boolean) =>
  typeof value === "number" ? formatNumber(value) : typeof value === "boolean" ? (value ? "Yes" : "No") : value;
---
{shown.length > 0 && (
  <table class="stats">
    <tbody>
      {shown.map(([label, value]) => (
        <tr><th scope="row">{label}</th><td>{display(value!)}</td></tr>
      ))}
    </tbody>
  </table>
)}
```

`web/src/components/Section.astro`:

```astro
---
interface Props {
  title: string;
  show?: boolean;
}

const { title, show = true } = Astro.props;
---
{show && (
  <section class="panel">
    <h2>{title}</h2>
    <slot />
  </section>
)}
```

`web/src/components/LinkList.astro`:

```astro
---
import EntityLink from "./EntityLink.astro";

interface Props {
  links: ({ type: string; key: string; name: string | null; missing: boolean } | null)[];
}

const links = Astro.props.links.filter((l) => l !== null);
---
{links.length > 0 && (
  <ul class="link-list">
    {links.map((link) => <li><EntityLink link={link} /></li>)}
  </ul>
)}
```

`web/src/components/ResourceCost.astro`:

```astro
---
import { formatNumber } from "../lib/effectText";

interface Props {
  cost: {
    key: string;
    treasury_cost: number;
    pooled_resources: { pooled_resource_factor: string; amount: number; context: string }[];
    trade_resources: string[];
  } | null;
}

const { cost } = Astro.props;
---
{cost && (
  <ul class="resource-cost">
    {cost.treasury_cost !== 0 && <li>Treasury: {formatNumber(cost.treasury_cost)}</li>}
    {cost.pooled_resources.map((r) => (
      <li>{r.pooled_resource_factor.replace(/_/g, " ")}: {formatNumber(r.amount)} <span class="muted">({r.context})</span></li>
    ))}
    {cost.trade_resources.length > 0 && <li>Trade resources: {cost.trade_resources.join(", ")}</li>}
  </ul>
)}
```

`web/src/components/EntityHeader.astro`:

```astro
---
import type { EntityImage } from "../data/images";
import { pageTypeInfo, type PageType } from "../data/pageTypes";
import GameImage from "./GameImage.astro";

interface Props {
  type: PageType;
  entityKey: string;
  name: string | null;
  image: EntityImage | null;
}

const { type, entityKey, name, image } = Astro.props;
const info = pageTypeInfo(type)!;
const kind = image ? (image.kind === "icon" ? "large" : image.kind) : null;
---
<nav class="breadcrumbs" aria-label="Breadcrumbs">
  <a href="/">Home</a> › <a href={`/${info.segment}/`}>{info.label}</a>
</nav>
<header class="entity-header">
  {image && kind && <GameImage path={image.path} kind={kind} alt={name ?? entityKey} />}
  <div>
    <h1 class:list={[{ unnamed: !name }]}>{name ?? entityKey}</h1>
    <p class="muted entity-meta">{info.singular} · <code>{entityKey}</code></p>
  </div>
</header>
```

- [ ] **Step 6: Create the five page bodies and the registry**

`web/src/components/pages/UnitPage.astro`:

```astro
---
import { getSite } from "../../data/model";
import GameText from "../GameText.astro";
import LinkList from "../LinkList.astro";
import Section from "../Section.astro";
import StatTable from "../StatTable.astro";

interface Props {
  entityKey: string;
}

const site = await getSite();
const unit = site.model.entities.unit.get(Astro.props.entityKey)!;
const s = unit.base_stats;
const melee = unit.melee_weapon;
const missile = unit.missile_weapon;
const projectile = missile?.projectile ?? null;
const shield = unit.shield;
---
<Section title="Overview">
  <GameText text={unit.short_description} block />
  <StatTable rows={[
    ["Caste", unit.caste_name ?? unit.caste],
    ["Category", unit.category_name ?? unit.category],
    ["Class", unit.class_name ?? unit.unit_class],
    ["Tier", unit.tier],
    ["Naval", unit.is_naval],
    ["Recruitment cost", unit.recruitment_cost],
    ["Upkeep", unit.upkeep_cost],
    ["Multiplayer cost", unit.multiplayer_cost],
    ["Campaign cap", unit.campaign_cap >= 0 ? unit.campaign_cap : null],
    ["Mount", unit.mount],
  ]} />
</Section>
{s && (
  <Section title="Base stats">
    <StatTable rows={[
      ["Men", s.num_men],
      ["Hit points per entity", s.hit_points_per_entity],
      ["Bonus hit points", s.bonus_hit_points],
      ["Melee attack", s.melee_attack],
      ["Melee defence", s.melee_defence],
      ["Charge bonus", s.charge_bonus],
      ["Armour", s.armour],
      ["Leadership", s.morale],
      ["Walk speed", s.walk_speed],
      ["Run speed", s.run_speed],
      ["Charge speed", s.charge_speed],
      ["Fly speed", s.fly_speed || null],
      ["Mass", s.mass],
      ["Accuracy", s.accuracy || null],
      ["Reload", s.reload || null],
      ["Ammunition", s.primary_ammo || null],
      ["Physical resistance", s.damage_mod_physical || null],
      ["Magic resistance", s.damage_mod_magic || null],
      ["Fire resistance", s.damage_mod_flame || null],
      ["Missile resistance", s.damage_mod_missile || null],
      ["Ward save", s.damage_mod_all || null],
      ["Healing power", s.healing_power],
      ["Spell mastery", s.spell_mastery],
      ["Rank depth", s.rank_depth],
    ]} />
  </Section>
)}
{melee && (
  <Section title="Melee weapon">
    <StatTable rows={[
      ["Weapon", melee.key],
      ["Base damage", melee.damage],
      ["Armour-piercing damage", melee.ap_damage],
      ["Bonus vs large", melee.bonus_v_large || null],
      ["Bonus vs infantry", melee.bonus_v_infantry || null],
      ["Magical", melee.is_magical],
      ["Attack interval", melee.melee_attack_interval],
      ["Splash target size", melee.splash_attack_target_size],
      ["Splash attacks", melee.splash_attack_max_attacks || null],
      ["Building damage multiplier", melee.building_damage_multiplier],
      ["Ignition", melee.ignition_amount || null],
    ]} />
  </Section>
)}
{missile && (
  <Section title="Missile weapon">
    <StatTable rows={[
      ["Weapon", missile.key],
      ["Base damage", projectile?.damage],
      ["Armour-piercing damage", projectile?.ap_damage],
      ["Bonus vs large", projectile?.bonus_v_large || null],
      ["Bonus vs infantry", projectile?.bonus_v_infantry || null],
      ["Range", projectile?.effective_range],
      ["Minimum range", projectile?.minimum_range || null],
      ["Reload time", projectile?.base_reload_time],
      ["Projectiles per shot", projectile?.projectile_number],
      ["Shots per volley", projectile?.shots_per_volley],
      ["Burst size", projectile?.burst_size],
      ["Magical", projectile?.is_magical],
      ["Ignition", projectile?.ignition_amount || null],
      ["Explosion", projectile?.explosion_type],
    ]} />
  </Section>
)}
{shield && (
  <Section title="Shield">
    <StatTable rows={[
      ["Defence", shield.shield_defence_value],
      ["Armour", shield.shield_armour_value],
      ["Missile block chance", shield.missile_block_chance],
    ]} />
  </Section>
)}
<Section title="Attributes" show={unit.attributes.length > 0}>
  <ul class="plain-list">
    {unit.attributes.map((a) => <li><GameText text={a.name ?? a.key} />{a.description && <> — <GameText text={a.description} /></>}</li>)}
  </ul>
</Section>
<Section title="Abilities" show={unit.abilities.length > 0}><LinkList links={unit.abilities} /></Section>
<Section title="Characters" show={unit.characters.length > 0}><LinkList links={unit.characters} /></Section>
<Section title="Recruited at" show={unit.recruited_by_buildings.length > 0}><LinkList links={unit.recruited_by_buildings} /></Section>
<Section title="Custom battle factions" show={unit.custom_battle_factions.length > 0}><LinkList links={unit.custom_battle_factions} /></Section>
```

`web/src/components/pages/AbilityPage.astro`:

```astro
---
import { getSite } from "../../data/model";
import GameText from "../GameText.astro";
import LinkList from "../LinkList.astro";
import Section from "../Section.astro";
import StatTable from "../StatTable.astro";

interface Props {
  entityKey: string;
}

const site = await getSite();
const ability = site.model.entities.ability.get(Astro.props.entityKey)!;
const act = ability.activation;
---
<Section title="Overview">
  <GameText text={ability.description} block />
  <StatTable rows={[
    ["Type", ability.type_name ? null : ability.type],
    ["Source", ability.source_type_name ?? ability.source_type],
    ["Unit upgrade", ability.is_unit_upgrade],
    ["Needs enabling effect", ability.requires_effect_enabling],
    ["Hidden in game UI", ability.is_hidden_in_ui],
  ]} />
  {ability.type_name && <p>Type: <GameText text={ability.type_name} /></p>}
</Section>
{act && (
  <Section title="Activation">
    <StatTable rows={[
      ["Passive", act.passive],
      ["Active time", act.active_time],
      ["Recharge time", act.recharge_time],
      ["Initial recharge", act.initial_recharge],
      ["Uses", act.num_uses],
      ["Range", act.effect_range],
      ["Minimum range", act.min_range || null],
      ["Mana cost", act.mana_cost || null],
      ["Wind-up time", act.wind_up_time || null],
      ["Miscast chance", act.miscast_chance || null],
      ["Targets self", act.target_self],
      ["Targets allies", act.target_friends],
      ["Targets enemies", act.target_enemies],
      ["Targets ground", act.target_ground],
      ["Affects self", act.affect_self],
      ["Allied units affected", act.num_effected_friendly_units],
      ["Enemy units affected", act.num_effected_enemy_units],
      ["Spawned unit", act.spawned_unit],
      ["Projectile", act.activated_projectile],
      ["Bombardment", act.bombardment],
      ["Vortex", act.vortex],
    ]} />
  </Section>
)}
{ability.phases.map((phase) => (
  <Section title={`Phase ${phase.order + 1}`}>
    <StatTable rows={[
      ["Phase", phase.key],
      ["Duration", phase.duration],
      ["Effect type", phase.effect_type],
      ["Affects self", phase.target_self],
      ["Affects allies", phase.target_friends],
      ["Affects enemies", phase.target_enemies],
      ["Damage", phase.damage_amount || null],
      ["Heal amount", phase.heal_amount || null],
      ["Hit point change frequency", phase.hp_change_frequency || null],
      ["Resurrects", phase.resurrect || null],
      ["Imbues magical attacks", phase.imbue_magical || null],
      ["Replenishes ammunition", phase.replenish_ammo || null],
      ["Fatigue change", phase.fatigue_change_ratio || null],
      ["Ability recharge change", phase.ability_recharge_change || null],
      ["Cannot move", phase.cant_move || null],
      ["Execute below health", phase.execute_ratio || null],
    ]} />
    {phase.stat_effects.length > 0 && (
      <table class="phase-stats">
        <thead><tr><th>Stat</th><th>Change</th><th>Value</th></tr></thead>
        <tbody>
          {phase.stat_effects.map((e) => <tr><td><GameText text={e.stat_name ?? e.stat} /></td><td>{e.how}</td><td>{e.value}</td></tr>)}
        </tbody>
      </table>
    )}
    {phase.attribute_effects.length > 0 && (
      <p>Attributes: {phase.attribute_effects.map((a) => `${a.attribute} (${a.attribute_type})`).join(", ")}</p>
    )}
  </Section>
))}
<Section title="Units" show={ability.units.length > 0}><LinkList links={ability.units} /></Section>
<Section title="Characters" show={ability.characters.length > 0}><LinkList links={ability.characters} /></Section>
<Section title="Modified by effects" show={ability.modified_by_effects.length > 0}><LinkList links={ability.modified_by_effects} /></Section>
```

`web/src/components/pages/SkillPage.astro`:

```astro
---
import { getSite } from "../../data/model";
import EffectList from "../EffectList.astro";
import GameText from "../GameText.astro";
import LinkList from "../LinkList.astro";
import Section from "../Section.astro";
import StatTable from "../StatTable.astro";

interface Props {
  entityKey: string;
}

const site = await getSite();
const skill = site.model.entities.skill.get(Astro.props.entityKey)!;
---
<Section title="Overview">
  <GameText text={skill.description} block />
  <StatTable rows={[
    ["Unlocks at rank", skill.unlocked_at_rank || null],
    ["Background skill", skill.is_background_skill],
  ]} />
</Section>
<Section title="Levels" show={skill.levels.length > 0}>
  {skill.levels.map((level) => (
    <div class="skill-level">
      <h3>Level {level.level}{level.unlocked_at_rank != null && <span class="muted"> · unlocks at rank {level.unlocked_at_rank}</span>}</h3>
      <EffectList applications={level.effects} />
    </div>
  ))}
</Section>
<Section title="Characters" show={skill.characters.length > 0}><LinkList links={skill.characters} /></Section>
```

`web/src/components/pages/ItemPage.astro`:

```astro
---
import { getSite } from "../../data/model";
import EffectList from "../EffectList.astro";
import EntityLink from "../EntityLink.astro";
import GameText from "../GameText.astro";
import LinkList from "../LinkList.astro";
import Section from "../Section.astro";
import StatTable from "../StatTable.astro";

interface Props {
  entityKey: string;
}

const site = await getSite();
const item = site.model.entities.item.get(Astro.props.entityKey)!;
---
<Section title="Overview">
  <GameText text={item.description} block />
  <GameText text={item.explanation} block />
  <StatTable rows={[
    ["Type", item.type],
    ["Category", item.category],
    ["Subcategory", item.subcategory],
    ["Legendary", item.legendary],
    ["Applies to", item.applies_to],
    ["Transferable", item.transferrable],
    ["Unique in the world", item.unique_to_world],
    ["Unique to faction", item.unique_to_faction],
    ["Agent types", item.agent_types.join(", ")],
  ]} />
  {item.bodyguard_unit && <p>Bodyguard unit: <EntityLink link={item.bodyguard_unit} /></p>}
</Section>
<Section title="Effects" show={item.effects.length > 0}><EffectList applications={item.effects} /></Section>
<Section title="Characters" show={item.agent_subtypes.length > 0}><LinkList links={item.agent_subtypes} /></Section>
<Section title="Required skills" show={item.required_skills.length > 0}>
  <ul class="link-list">
    {item.required_skills.map((r) => <li><EntityLink link={r.skill} /> <span class="muted">level {r.level}</span></li>)}
  </ul>
</Section>
```

`web/src/components/pages/TraitPage.astro`:

```astro
---
import { getSite } from "../../data/model";
import EffectList from "../EffectList.astro";
import GameText from "../GameText.astro";
import LinkList from "../LinkList.astro";
import Section from "../Section.astro";
import StatTable from "../StatTable.astro";

interface Props {
  entityKey: string;
}

const site = await getSite();
const trait = site.model.entities.trait.get(Astro.props.entityKey)!;
---
<Section title="Overview">
  <StatTable rows={[
    ["Hidden", trait.hidden],
    ["Precedence", trait.precedence],
    ["No going back from level", trait.no_going_back_level || null],
  ]} />
</Section>
{trait.levels.map((level) => (
  <Section title={`Level ${level.level}`}>
    <h3 class:list={[{ unnamed: !level.name }]}><GameText text={level.name ?? level.key} /></h3>
    <GameText text={level.description} block />
    <StatTable rows={[["Threshold points", level.threshold_points]]} />
    <EffectList applications={level.effects} />
  </Section>
))}
<Section title="Antitraits" show={trait.antitraits.length > 0}><LinkList links={trait.antitraits} /></Section>
```

`web/src/components/pages/registry.ts`:

```ts
import AbilityPage from "./AbilityPage.astro";
import ItemPage from "./ItemPage.astro";
import SkillPage from "./SkillPage.astro";
import TraitPage from "./TraitPage.astro";
import UnitPage from "./UnitPage.astro";

/** Body component per page type; the entity route only builds pages for registered types. */
export const PAGE_BODIES = {
  unit: UnitPage,
  ability: AbilityPage,
  skill: SkillPage,
  item: ItemPage,
  trait: TraitPage,
};
```

- [ ] **Step 7: Create the entity route**

`web/src/pages/[segment]/[slug].astro`:

```astro
---
import EntityHeader from "../../components/EntityHeader.astro";
import { PAGE_BODIES } from "../../components/pages/registry";
import { mainImage } from "../../data/images";
import { getSite } from "../../data/model";
import { PAGE_TYPES, pageTypeInfo, type PageType } from "../../data/pageTypes";
import Layout from "../../layouts/Layout.astro";

export async function getStaticPaths() {
  const site = await getSite();
  return PAGE_TYPES.filter((info) => info.type in PAGE_BODIES).flatMap((info) =>
    [...site.model.entities[info.type].keys()].map((key) => ({
      params: { segment: info.segment, slug: site.slugs[info.type].get(key)! },
      props: { type: info.type, entityKey: key },
    })),
  );
}

interface Props {
  type: PageType;
  entityKey: string;
}

const { type, entityKey } = Astro.props;
const site = await getSite();
const entity = (site.model.entities as Record<string, Map<string, Record<string, any>>>)[type].get(entityKey)!;
const name: string | null = entity.name ?? null;
const info = pageTypeInfo(type)!;
const Body = PAGE_BODIES[type as keyof typeof PAGE_BODIES];
---
<Layout title={name ?? entityKey} description={`${info.singular}: ${name ?? entityKey} — Total War: WARHAMMER III`}>
  <EntityHeader type={type} entityKey={entityKey} name={name} image={mainImage(site, type, entity)} />
  <div class="entity-body">
    <Body entityKey={entityKey} />
  </div>
</Layout>
```

- [ ] **Step 8: Add component styles**

Append to `web/src/styles/theme.css`:

```css
.breadcrumbs { font-size: 0.8rem; color: var(--muted); margin: 0.25rem 0 0.75rem; }
.breadcrumbs a { color: var(--muted); }
.entity-header { display: flex; gap: 1rem; align-items: flex-start; margin-bottom: 1rem; }
.entity-header h1 { margin: 0; }
.entity-meta { margin: 0.2rem 0 0; font-size: 0.85rem; }
.entity-meta code, .site-footer code { color: var(--muted); }
.entity-body { display: grid; grid-template-columns: repeat(auto-fit, minmax(22rem, 1fr)); gap: 0 1rem; align-items: start; }
.entity-link { display: inline-flex; gap: 0.35rem; align-items: center; }
.link-list, .plain-list, .effect-list, .resource-cost { list-style: none; margin: 0; padding: 0; }
.link-list li, .plain-list li, .effect-list li { padding: 0.2rem 0; border-bottom: 1px solid #3a2e1d; }
.effect-list li { display: flex; flex-wrap: wrap; gap: 0.2rem 0.5rem; align-items: center; }
.effect-note { font-size: 0.8rem; }
.skill-level + .skill-level { margin-top: 0.75rem; }
.phase-stats { margin-top: 0.5rem; }
```

- [ ] **Step 9: Build against the fixture**

Run: `MODEL_DIR=test/fixtures/model npm run build`
Expected: Astro `Complete!`; page counts: `dist/units/` 2 pages, `dist/skills/` 51, `dist/abilities/` 1, `dist/items/` 1, `dist/traits/` none.

Run: `grep -o "Melee attack</th><td>32" dist/units/wh_main_emp_inf_greatswords/index.html`
Expected: one match (Astro may add attributes; if the literal is not found, `grep -c "Melee attack" …` must be ≥ 1 and the `32` must appear in the same row).

Run: `grep -c "data-placeholder-image" dist/units/wh_main_emp_inf_greatswords/index.html`
Expected: ≥ 1 (the fixture has no image files).

- [ ] **Step 10: Run all unit tests and commit**

Run: `npm test`
Expected: PASS.

```bash
git add web/src web/test/unit/images.test.ts
git commit -F - <<'EOF'
feat(web): entity route with unit, ability, skill, item and trait pages

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 6: Remaining page bodies (except regions) and browse pages

**Files:**
- Create under `web/src/components/pages/`: `CharacterPage.astro`, `TechnologyPage.astro`, `TechnologyTreePage.astro`, `BuildingLevelPage.astro`, `BuildingChainPage.astro`, `FactionPage.astro`, `CulturePage.astro`, `SubculturePage.astro`, `ProvincePage.astro`
- Modify: `web/src/components/pages/registry.ts`
- Create: `web/src/data/browse.ts`, `web/src/pages/[segment]/index.astro`, `web/src/islands/BrowseFilter.tsx`
- Modify: `web/src/styles/theme.css`
- Test: `web/test/unit/browse.test.ts`

**Interfaces:**
- Consumes: components from Task 5 (`EntityLink`, `LinkList`, `Section`, `StatTable`, `GameText`, `GameImage`, `EffectList`, `ResourceCost`); `getSite`, `urlFor`, `mainImage`, `formatNumber`.
- Produces:
  - `BROWSE_FIELDS: Record<PageType, { field: string; label: string }[]>`
  - `interface BrowseRow { key: string; name: string; unnamed: boolean; url: string; image: EntityImage | null; values: string[] }`
  - `interface BrowseFilterSpec { index: number; label: string; options: string[] }`
  - `cellText(value: unknown): string`, `browseRows(site: Site, type: PageType): BrowseRow[]`, `browseFilters(type: PageType, rows: BrowseRow[]): BrowseFilterSpec[]`
  - `BrowseFilter` island props `{ tableId: string; filters: BrowseFilterSpec[]; total: number }`; rows carry `data-search` (lower-case name and key) and `data-f<index>` attributes
  - `PAGE_BODIES` covers 14 page types (all but `region`, added in Task 8). `CharacterPage` and `TechnologyTreePage` render simple node tables that Task 7 replaces with tree views.

- [ ] **Step 1: Write the failing test**

`web/test/unit/browse.test.ts`:

```ts
import path from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import { BROWSE_FIELDS, browseFilters, browseRows, cellText } from "../../src/data/browse";
import { loadModel } from "../../src/data/load";
import { PAGE_TYPES } from "../../src/data/pageTypes";
import { type Site, createSite } from "../../src/data/site";

const FIXTURE = path.resolve(__dirname, "../fixtures/model");
let site: Site;

beforeAll(async () => {
  site = await createSite(await loadModel(FIXTURE));
});

describe("cellText", () => {
  it("formats values for table cells", () => {
    expect(cellText(["general", "wizard"])).toBe("general, wizard");
    expect(cellText(true)).toBe("Yes");
    expect(cellText(false)).toBe("No");
    expect(cellText(2.5)).toBe("2.5");
    expect(cellText(null)).toBe("");
    expect(cellText(undefined)).toBe("");
    expect(cellText("melee_infantry")).toBe("melee_infantry");
  });
});

describe("browseRows", () => {
  it("covers every page type", () => {
    expect(Object.keys(BROWSE_FIELDS).sort()).toEqual(PAGE_TYPES.map((p) => p.type).sort());
  });

  it("lists every entity with URL, name and field values, sorted by name", () => {
    const rows = browseRows(site, "unit");
    expect(rows).toHaveLength(site.model.entities.unit.size);
    const names = rows.map((r) => r.name);
    expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b)));
    const gs = rows.find((r) => r.key === "wh_main_emp_inf_greatswords")!;
    expect(gs.url).toBe("/units/wh_main_emp_inf_greatswords/");
    expect(gs.name).toBe("Greatswords");
    expect(gs.values).toHaveLength(BROWSE_FIELDS.unit.length);
    expect(gs.values[3]).toBe("3");
  });
});

describe("browseFilters", () => {
  it("offers dropdowns only for columns with 2 to 40 distinct values", () => {
    const filters = browseFilters("unit", browseRows(site, "unit"));
    expect(filters.map((f) => f.label)).toContain("Caste");
    expect(filters.map((f) => f.label)).not.toContain("Naval");
    const caste = filters.find((f) => f.label === "Caste")!;
    expect(caste.index).toBe(0);
    expect(caste.options).toEqual([...caste.options].sort());
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run test/unit/browse.test.ts`
Expected: FAIL — cannot resolve `../../src/data/browse`.

- [ ] **Step 3: Implement `web/src/data/browse.ts`**

```ts
import { formatNumber } from "../lib/effectText";
import { type EntityImage, mainImage } from "./images";
import type { PageType } from "./pageTypes";
import { type Site, urlFor } from "./site";

export const BROWSE_FIELDS: Record<PageType, { field: string; label: string }[]> = {
  unit: [
    { field: "caste", label: "Caste" },
    { field: "category", label: "Category" },
    { field: "unit_class", label: "Class" },
    { field: "tier", label: "Tier" },
    { field: "is_naval", label: "Naval" },
  ],
  character: [
    { field: "agent_types", label: "Agent types" },
    { field: "is_caster", label: "Caster" },
  ],
  skill: [{ field: "unlocked_at_rank", label: "Unlock rank" }],
  ability: [
    { field: "type", label: "Type" },
    { field: "source_type", label: "Source" },
  ],
  technology: [{ field: "is_hidden", label: "Hidden" }],
  technology_tree: [],
  building_level: [
    { field: "level", label: "Level" },
    { field: "cultures", label: "Cultures" },
  ],
  building_chain: [{ field: "category", label: "Category" }],
  item: [
    { field: "category", label: "Category" },
    { field: "legendary", label: "Legendary" },
  ],
  trait: [{ field: "hidden", label: "Hidden" }],
  faction: [],
  culture: [],
  subculture: [],
  region: [
    { field: "campaign", label: "Campaign" },
    { field: "is_settlement", label: "Settlement" },
    { field: "template_source", label: "Templates" },
  ],
  province: [{ field: "campaign", label: "Campaign" }],
};

export interface BrowseRow {
  key: string;
  name: string;
  unnamed: boolean;
  url: string;
  image: EntityImage | null;
  values: string[];
}

export interface BrowseFilterSpec {
  index: number;
  label: string;
  options: string[];
}

export function cellText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.map(cellText).join(", ");
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return formatNumber(value);
  return String(value);
}

export function browseRows(site: Site, type: PageType): BrowseRow[] {
  const fields = BROWSE_FIELDS[type];
  const rows: BrowseRow[] = [];
  for (const entity of (site.model.entities[type] as Map<string, Record<string, any>>).values()) {
    const name: string | null = entity.name ?? null;
    rows.push({
      key: entity.key,
      name: name ?? entity.key,
      unnamed: !name,
      url: urlFor(site, type, entity.key)!,
      image: mainImage(site, type, entity),
      values: fields.map((f) => cellText(entity[f.field])),
    });
  }
  return rows.sort((a, b) => a.name.localeCompare(b.name) || a.key.localeCompare(b.key));
}

export function browseFilters(type: PageType, rows: BrowseRow[]): BrowseFilterSpec[] {
  return BROWSE_FIELDS[type].flatMap((field, index) => {
    const options = [...new Set(rows.map((r) => r.values[index]).filter((v) => v !== ""))].sort();
    return options.length >= 2 && options.length <= 40 ? [{ index, label: field.label, options }] : [];
  });
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npx vitest run test/unit/browse.test.ts`
Expected: PASS.

- [ ] **Step 5: Create the browse filter island and browse route**

`web/src/islands/BrowseFilter.tsx`:

```tsx
import { useEffect, useState } from "react";

interface FilterSpec {
  index: number;
  label: string;
  options: string[];
}

interface Props {
  tableId: string;
  filters: FilterSpec[];
  total: number;
}

export default function BrowseFilter({ tableId, filters, total }: Props) {
  const [text, setText] = useState("");
  const [selected, setSelected] = useState<Record<number, string>>({});
  const [shown, setShown] = useState(total);

  useEffect(() => {
    const needle = text.trim().toLowerCase();
    let count = 0;
    document.querySelectorAll<HTMLTableRowElement>(`#${tableId} tbody tr`).forEach((row) => {
      const matches =
        (!needle || (row.dataset.search ?? "").includes(needle)) &&
        Object.entries(selected).every(([index, value]) => !value || row.getAttribute(`data-f${index}`) === value);
      row.hidden = !matches;
      if (matches) count += 1;
    });
    setShown(count);
  }, [text, selected, tableId]);

  return (
    <div className="browse-filter" role="search">
      <input
        type="search"
        placeholder="Filter by name or key"
        aria-label="Filter by name or key"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      {filters.map((f) => (
        <label key={f.index}>
          {f.label}{" "}
          <select value={selected[f.index] ?? ""} onChange={(e) => setSelected({ ...selected, [f.index]: e.target.value })}>
            <option value="">All</option>
            {f.options.map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
        </label>
      ))}
      <span className="muted">
        {shown} of {total}
      </span>
    </div>
  );
}
```

`web/src/pages/[segment]/index.astro`:

```astro
---
import GameImage from "../../components/GameImage.astro";
import { BROWSE_FIELDS, browseFilters, browseRows } from "../../data/browse";
import { getSite } from "../../data/model";
import { PAGE_TYPES, pageTypeInfo, type PageType } from "../../data/pageTypes";
import BrowseFilter from "../../islands/BrowseFilter.tsx";
import Layout from "../../layouts/Layout.astro";

export async function getStaticPaths() {
  return PAGE_TYPES.map((info) => ({ params: { segment: info.segment }, props: { type: info.type } }));
}

interface Props {
  type: PageType;
}

const { type } = Astro.props;
const site = await getSite();
const info = pageTypeInfo(type)!;
const rows = browseRows(site, type);
const fields = BROWSE_FIELDS[type];
const filters = browseFilters(type, rows);
---
<Layout title={info.label} description={`All ${rows.length} ${info.label.toLowerCase()} in Total War: WARHAMMER III`}>
  <nav class="breadcrumbs" aria-label="Breadcrumbs"><a href="/">Home</a></nav>
  <h1>{info.label}</h1>
  <BrowseFilter client:visible tableId="browse-table" filters={filters} total={rows.length} />
  <div class="table-wrap">
    <table id="browse-table" class="browse">
      <thead>
        <tr><th>Name</th><th>Key</th>{fields.map((f) => <th>{f.label}</th>)}</tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr data-search={`${row.name} ${row.key}`.toLowerCase()} {...Object.fromEntries(row.values.map((v, i) => [`data-f${i}`, v]))}>
            <td>
              <a class="entity-link" href={row.url}>
                {row.image && <GameImage path={row.image.path} kind="icon" />}
                <span class:list={[{ unnamed: row.unnamed }]}>{row.name}</span>
              </a>
            </td>
            <td><code>{row.key}</code></td>
            {row.values.map((v) => <td>{v}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
</Layout>
```

- [ ] **Step 6: Create the nine page bodies**

`web/src/components/pages/CharacterPage.astro`:

```astro
---
import { getSite } from "../../data/model";
import EntityLink from "../EntityLink.astro";
import GameText from "../GameText.astro";
import LinkList from "../LinkList.astro";
import Section from "../Section.astro";
import StatTable from "../StatTable.astro";

interface Props {
  entityKey: string;
}

const site = await getSite();
const character = site.model.entities.character.get(Astro.props.entityKey)!;
---
<Section title="Overview">
  {character.title && <p class="muted"><GameText text={character.title} /></p>}
  <GameText text={character.description} block />
  <StatTable rows={[
    ["Agent types", character.agent_types.join(", ")],
    ["Lore of magic", character.lore_of_magic?.name ?? character.lore_of_magic?.key],
    ["Spellcaster", character.is_caster],
    ["Can equip items", character.can_equip_ancillaries],
    ["Recruitable", character.recruitable],
    ["Gains experience", character.can_gain_xp],
    ["Cost", character.cost],
    ["Cap", character.cap >= 0 ? character.cap : null],
  ]} />
  {character.associated_unit && <p>Unit: <EntityLink link={character.associated_unit} /></p>}
</Section>
<Section title="Abilities" show={character.abilities.length > 0}><LinkList links={character.abilities} /></Section>
<Section title="Factions" show={character.factions.length > 0}><LinkList links={character.factions} /></Section>
<Section title="Items" show={character.items.length > 0}><LinkList links={character.items} /></Section>
{character.skill_trees.map((tree) => (
  <Section title={`Skill tree: ${tree.key}`}>
    <table>
      <thead><tr><th>Skill</th><th>Tier</th><th>Line</th></tr></thead>
      <tbody>
        {tree.nodes.filter((n) => n.visible_in_ui).map((n) => (
          <tr><td><EntityLink link={n.skill} /></td><td>{n.tier}</td><td>{n.indent}</td></tr>
        ))}
      </tbody>
    </table>
  </Section>
))}
```

`web/src/components/pages/TechnologyPage.astro`:

```astro
---
import { getSite } from "../../data/model";
import EffectList from "../EffectList.astro";
import EntityLink from "../EntityLink.astro";
import GameText from "../GameText.astro";
import LinkList from "../LinkList.astro";
import ResourceCost from "../ResourceCost.astro";
import Section from "../Section.astro";
import StatTable from "../StatTable.astro";

interface Props {
  entityKey: string;
}

const site = await getSite();
const tech = site.model.entities.technology.get(Astro.props.entityKey)!;
---
<Section title="Overview">
  <GameText text={tech.description} block />
  <GameText text={tech.long_description} block />
  <StatTable rows={[
    ["Civil", tech.is_civil],
    ["Engineering", tech.is_engineering],
    ["Military", tech.is_military],
    ["Hidden", tech.is_hidden],
  ]} />
  {tech.unlocked_by_building && <p>Unlocked by: <EntityLink link={tech.unlocked_by_building} /></p>}
</Section>
<Section title="Effects" show={tech.effects.length > 0}><EffectList applications={tech.effects} /></Section>
<Section title="Research" show={tech.placements.length > 0}>
  <table>
    <thead><tr><th>Tree</th><th>Research points</th><th>Cost per turn</th><th>Resource cost</th></tr></thead>
    <tbody>
      {tech.placements.map((p) => (
        <tr>
          <td><EntityLink link={p.tree} /></td>
          <td>{p.research_points_required}</td>
          <td>{p.cost_per_round || ""}</td>
          <td><ResourceCost cost={p.resource_cost} /></td>
        </tr>
      ))}
    </tbody>
  </table>
</Section>
<Section title="Requires technologies" show={tech.required_technologies.length > 0}><LinkList links={tech.required_technologies} /></Section>
<Section title="Requires buildings" show={tech.required_buildings.length > 0}><LinkList links={tech.required_buildings} /></Section>
```

`web/src/components/pages/TechnologyTreePage.astro`:

```astro
---
import { getSite } from "../../data/model";
import EntityLink from "../EntityLink.astro";
import Section from "../Section.astro";
import StatTable from "../StatTable.astro";

interface Props {
  entityKey: string;
}

const site = await getSite();
const tree = site.model.entities.technology_tree.get(Astro.props.entityKey)!;
---
<Section title="Scope">
  <StatTable rows={[["Campaign", tree.campaign], ["Technologies", tree.nodes.length]]} />
  {tree.culture && <p>Culture: <EntityLink link={tree.culture} /></p>}
  {tree.subculture && <p>Subculture: <EntityLink link={tree.subculture} /></p>}
  {tree.faction && <p>Faction: <EntityLink link={tree.faction} /></p>}
</Section>
<Section title="Technologies">
  <table>
    <thead><tr><th>Technology</th><th>Tier</th><th>Row</th><th>Research points</th></tr></thead>
    <tbody>
      {tree.nodes.map((n) => (
        <tr><td><EntityLink link={n.technology} /></td><td>{n.tier}</td><td>{n.indent}</td><td>{n.research_points_required}</td></tr>
      ))}
    </tbody>
  </table>
</Section>
```

`web/src/components/pages/BuildingLevelPage.astro`:

```astro
---
import { getSite } from "../../data/model";
import EffectList from "../EffectList.astro";
import EntityLink from "../EntityLink.astro";
import GameText from "../GameText.astro";
import LinkList from "../LinkList.astro";
import ResourceCost from "../ResourceCost.astro";
import Section from "../Section.astro";
import StatTable from "../StatTable.astro";

interface Props {
  entityKey: string;
}

const site = await getSite();
const level = site.model.entities.building_level.get(Astro.props.entityKey)!;
---
<Section title="Overview">
  <GameText text={level.short_description} block />
  {level.chain && <p>Chain: <EntityLink link={level.chain} /></p>}
  <StatTable rows={[
    ["Level", level.level],
    ["Construction time", level.create_time],
    ["Construction cost", level.create_cost],
    ["Upkeep", level.upkeep_cost || null],
    ["Development points", level.development_point_cost || null],
    ["Food", level.food_cost || null],
    ["Capital only", level.only_in_capital],
    ["Faction unique", level.faction_unique],
    ["Can convert", level.can_convert],
    ["Shown in game UI", level.visible_in_ui],
    ["Cultures", level.cultures.join(", ")],
  ]} />
  <ResourceCost cost={level.resource_cost} />
</Section>
<Section title="Effects" show={level.effects.length > 0}><EffectList applications={level.effects} /></Section>
<Section title="Recruits" show={level.units_recruited.length > 0}><LinkList links={level.units_recruited} /></Section>
```

`web/src/components/pages/BuildingChainPage.astro`:

```astro
---
import { getSite } from "../../data/model";
import EntityLink from "../EntityLink.astro";
import LinkList from "../LinkList.astro";
import Section from "../Section.astro";
import StatTable from "../StatTable.astro";

interface Props {
  entityKey: string;
}

const site = await getSite();
const chain = site.model.entities.building_chain.get(Astro.props.entityKey)!;
---
<Section title="Overview">
  <StatTable rows={[["Category", chain.category], ["In encyclopedia", chain.in_encyclopedia]]} />
</Section>
<Section title="Levels" show={chain.levels.length > 0}><LinkList links={chain.levels} /></Section>
<Section title="Available to" show={chain.availability.length > 0}>
  <table>
    <thead><tr><th>Culture</th><th>Subculture</th><th>Faction</th><th>Campaign</th></tr></thead>
    <tbody>
      {chain.availability.map((a) => (
        <tr>
          <td><EntityLink link={a.culture} /></td>
          <td><EntityLink link={a.subculture} /></td>
          <td><EntityLink link={a.faction} /></td>
          <td>{a.campaign ?? ""}</td>
        </tr>
      ))}
    </tbody>
  </table>
</Section>
```

`web/src/components/pages/FactionPage.astro`:

```astro
---
import { getSite } from "../../data/model";
import EntityLink from "../EntityLink.astro";
import LinkList from "../LinkList.astro";
import Section from "../Section.astro";
import StatTable from "../StatTable.astro";

interface Props {
  entityKey: string;
}

const site = await getSite();
const faction = site.model.entities.faction.get(Astro.props.entityKey)!;
---
<Section title="Overview">
  <StatTable rows={[
    ["Adjective", faction.adjective],
    ["Category", faction.category],
    ["Rebels", faction.is_rebel],
    ["Quest faction", faction.is_quest_faction],
    ["Colour", faction.primary_colour],
  ]} />
  {faction.culture && <p>Culture: <EntityLink link={faction.culture} /></p>}
  {faction.subculture && <p>Subculture: <EntityLink link={faction.subculture} /></p>}
</Section>
<Section title="Units" show={faction.units.length > 0}><LinkList links={faction.units} /></Section>
<Section title="Characters" show={faction.characters.length > 0}><LinkList links={faction.characters} /></Section>
```

`web/src/components/pages/CulturePage.astro`:

```astro
---
import { getSite } from "../../data/model";
import LinkList from "../LinkList.astro";
import Section from "../Section.astro";

interface Props {
  entityKey: string;
}

const site = await getSite();
const culture = site.model.entities.culture.get(Astro.props.entityKey)!;
---
<Section title="Subcultures" show={culture.subcultures.length > 0}><LinkList links={culture.subcultures} /></Section>
<Section title="Factions" show={culture.factions.length > 0}><LinkList links={culture.factions} /></Section>
```

`web/src/components/pages/SubculturePage.astro`:

```astro
---
import { getSite } from "../../data/model";
import EntityLink from "../EntityLink.astro";
import LinkList from "../LinkList.astro";
import Section from "../Section.astro";

interface Props {
  entityKey: string;
}

const site = await getSite();
const subculture = site.model.entities.subculture.get(Astro.props.entityKey)!;
---
<Section title="Overview" show={subculture.culture !== null}>
  <p>Culture: <EntityLink link={subculture.culture} /></p>
</Section>
<Section title="Factions" show={subculture.factions.length > 0}><LinkList links={subculture.factions} /></Section>
```

`web/src/components/pages/ProvincePage.astro`:

```astro
---
import { getSite } from "../../data/model";
import EntityLink from "../EntityLink.astro";
import LinkList from "../LinkList.astro";
import Section from "../Section.astro";
import StatTable from "../StatTable.astro";

interface Props {
  entityKey: string;
}

const site = await getSite();
const province = site.model.entities.province.get(Astro.props.entityKey)!;
---
<Section title="Overview">
  <StatTable rows={[["Campaign", province.campaign], ["Regions", province.regions.length]]} />
  {province.capital && <p>Capital: <EntityLink link={province.capital} /></p>}
</Section>
<Section title="Regions" show={province.regions.length > 0}><LinkList links={province.regions} /></Section>
```

Replace `web/src/components/pages/registry.ts` with:

```ts
import AbilityPage from "./AbilityPage.astro";
import BuildingChainPage from "./BuildingChainPage.astro";
import BuildingLevelPage from "./BuildingLevelPage.astro";
import CharacterPage from "./CharacterPage.astro";
import CulturePage from "./CulturePage.astro";
import FactionPage from "./FactionPage.astro";
import ItemPage from "./ItemPage.astro";
import ProvincePage from "./ProvincePage.astro";
import SkillPage from "./SkillPage.astro";
import SubculturePage from "./SubculturePage.astro";
import TechnologyPage from "./TechnologyPage.astro";
import TechnologyTreePage from "./TechnologyTreePage.astro";
import TraitPage from "./TraitPage.astro";
import UnitPage from "./UnitPage.astro";

/** Body component per page type; the entity route only builds pages for registered types. */
export const PAGE_BODIES = {
  unit: UnitPage,
  character: CharacterPage,
  skill: SkillPage,
  ability: AbilityPage,
  technology: TechnologyPage,
  technology_tree: TechnologyTreePage,
  building_level: BuildingLevelPage,
  building_chain: BuildingChainPage,
  item: ItemPage,
  trait: TraitPage,
  faction: FactionPage,
  culture: CulturePage,
  subculture: SubculturePage,
  province: ProvincePage,
};
```

- [ ] **Step 7: Add styles**

Append to `web/src/styles/theme.css`:

```css
.table-wrap { overflow-x: auto; }
table.browse td, table.browse th { white-space: nowrap; }
.browse-filter { display: flex; flex-wrap: wrap; gap: 0.5rem 1rem; align-items: center; margin: 0.5rem 0 1rem; }
input[type="search"], select {
  background: var(--panel); color: var(--text); border: 1px solid var(--border-accent); padding: 0.35rem 0.5rem; font: inherit;
}
```

- [ ] **Step 8: Build against the fixture**

Run: `MODEL_DIR=test/fixtures/model npm run build`
Expected: `Complete!`; `dist/units/index.html`, `dist/regions/index.html` (browse page, no region entity pages yet), `dist/characters/wh_main_emp_karl_franz/index.html`, `dist/technology-trees/emp_civ_reworkd/index.html`, `dist/building-chains/wh_main_empire_barracks/index.html` and `dist/provinces/wh3_main_combi_province_reikland/index.html` all exist.

Run: `grep -c "data-search=" dist/units/index.html`
Expected: `2`.

- [ ] **Step 9: Run all unit tests and commit**

Run: `npm test`
Expected: PASS.

```bash
git add web/src web/test/unit/browse.test.ts
git commit -F - <<'EOF'
feat(web): character, technology, building, faction and province pages; browse pages

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 7: Skill and technology tree views

**Files:**
- Create: `web/src/lib/treeLayout.ts`, `web/src/lib/detailHtml.ts`, `web/src/data/trees.ts`
- Create: `web/src/islands/TreeView.tsx`, `web/src/components/TreeStaticList.astro`
- Modify: `web/src/components/pages/CharacterPage.astro`, `web/src/components/pages/TechnologyTreePage.astro`, `web/src/styles/theme.css`
- Test: `web/test/unit/treeLayout.test.ts`, `web/test/unit/trees.test.ts`

**Interfaces:**
- Consumes: `Site`, `urlFor`, `imageSrc` (Task 2); `renderGameTextHtml`, `formatEffect`, `formatNumber`, `scopeLabel`, `escapeHtml` (Task 4); `Section` styles (Task 5).
- Produces:
  - `interface TreeNodeInput { id: string; row: number; column: number; label: string; icon: string | null; url: string | null; hidden: boolean; detailHtml: string }`
  - `interface TreeLinkInput { parent: string; child: string }`
  - `interface TreeCell { node: TreeNodeInput; rowIndex: number; column: number }`, `interface TreeGroup { row: number; nodes: TreeNodeInput[] }`
  - `interface TreeLayout { rows: number[]; columns: number; cells: TreeCell[]; links: { from: string; to: string }[]; groups: TreeGroup[] }`
  - `HIDDEN_ROW = 99`, `layoutTree(nodes: TreeNodeInput[], links: TreeLinkInput[]): TreeLayout`
  - `effectsHtml(site, applications): string`, `skillDetailHtml(site: Site, skillKey: string): string`, `technologyDetailHtml(site: Site, node): string`
  - `skillTreeLayout(site: Site, tree: SkillTree): TreeLayout`, `technologyTreeLayout(site: Site, tree: TechnologyTree): TreeLayout`
  - `TreeView` island props `{ layout: TreeLayout; ariaLabel: string }`: desktop grid of `button.tree-node` (label text inside) with SVG links and `aside.tree-panel` showing the selected node's label in an `h3`; below 768 px wide it renders `.tree-lines` with collapsible `details` per row.

- [ ] **Step 1: Write the failing tests**

`web/test/unit/treeLayout.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { HIDDEN_ROW, type TreeNodeInput, layoutTree } from "../../src/lib/treeLayout";

const node = (id: string, row: number, column: number, hidden = false): TreeNodeInput => ({
  id, row, column, label: id.toUpperCase(), icon: null, url: null, hidden, detailHtml: `<p>${id}</p>`,
});

describe("layoutTree", () => {
  it("removes hidden nodes and the hidden row, compacting row indexes", () => {
    const layout = layoutTree(
      [node("a", 0, 0), node("b", 2, 1), node("c", 2, 0), node("h", 1, 0, true), node("x", HIDDEN_ROW, 0)],
      [],
    );
    expect(layout.rows).toEqual([0, 2]);
    expect(layout.cells.map((c) => [c.node.id, c.rowIndex, c.column])).toEqual([
      ["a", 0, 0],
      ["c", 1, 0],
      ["b", 1, 1],
    ]);
    expect(layout.columns).toBe(2);
    expect(layout.groups.map((g) => [g.row, g.nodes.map((n) => n.id)])).toEqual([
      [0, ["a"]],
      [2, ["c", "b"]],
    ]);
  });

  it("keeps links between visible nodes only, without duplicates", () => {
    const layout = layoutTree(
      [node("a", 0, 0), node("b", 0, 1), node("h", 0, 2, true)],
      [
        { parent: "a", child: "b" },
        { parent: "a", child: "b" },
        { parent: "b", child: "h" },
        { parent: "missing", child: "a" },
      ],
    );
    expect(layout.links).toEqual([{ from: "a", to: "b" }]);
  });

  it("moves a node that shares a row and column to the next free column", () => {
    const layout = layoutTree([node("a", 0, 1), node("b", 0, 1)], []);
    expect(layout.cells.map((c) => [c.node.id, c.column])).toEqual([
      ["a", 1],
      ["b", 2],
    ]);
    expect(layout.columns).toBe(3);
  });

  it("handles an empty tree", () => {
    expect(layoutTree([], [])).toEqual({ rows: [], columns: 0, cells: [], links: [], groups: [] });
  });
});
```

`web/test/unit/trees.test.ts`:

```ts
import path from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import { loadModel } from "../../src/data/load";
import { type Site, createSite } from "../../src/data/site";
import { skillTreeLayout, technologyTreeLayout } from "../../src/data/trees";
import { HIDDEN_ROW } from "../../src/lib/treeLayout";

const FIXTURE = path.resolve(__dirname, "../fixtures/model");
let site: Site;

beforeAll(async () => {
  site = await createSite(await loadModel(FIXTURE));
});

describe("skillTreeLayout", () => {
  it("lays out Karl Franz's visible skills with links and details", () => {
    const tree = site.model.entities.character.get("wh_main_emp_karl_franz")!.skill_trees[0];
    const layout = skillTreeLayout(site, tree);
    const visible = tree.nodes.filter((n) => n.visible_in_ui && n.indent !== HIDDEN_ROW);
    expect(layout.cells).toHaveLength(visible.length);
    const charge = layout.cells.find((c) => c.node.label === "Devastating Charge")!;
    expect(charge.node.url).toBe("/skills/wh2_dlc11_skill_all_lord_self_devastating_charge/");
    expect(charge.node.detailHtml).toContain("Level 1");
    expect(layout.links.length).toBeGreaterThan(0);
  });
});

describe("technologyTreeLayout", () => {
  it("lays out Empire Civil Tech with research costs in the details", () => {
    const tree = site.model.entities.technology_tree.get("emp_civ_reworkd")!;
    const layout = technologyTreeLayout(site, tree);
    expect(layout.cells).toHaveLength(tree.nodes.length);
    const heavy = layout.cells.find((c) => c.node.label === "Improved Heavy Weapons")!;
    expect(heavy.node.url).toBe("/technologies/wh2_dlc13_tech_emp_infantry_1_c/");
    expect(heavy.node.detailHtml).toContain("Research points: 900");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run test/unit/treeLayout.test.ts test/unit/trees.test.ts`
Expected: FAIL — cannot resolve `../../src/lib/treeLayout` and `../../src/data/trees`.

- [ ] **Step 3: Implement `web/src/lib/treeLayout.ts`**

```ts
export interface TreeNodeInput {
  id: string;
  row: number;
  column: number;
  label: string;
  icon: string | null;
  url: string | null;
  hidden: boolean;
  detailHtml: string;
}

export interface TreeLinkInput {
  parent: string;
  child: string;
}

export interface TreeCell {
  node: TreeNodeInput;
  rowIndex: number;
  column: number;
}

export interface TreeGroup {
  row: number;
  nodes: TreeNodeInput[];
}

export interface TreeLayout {
  rows: number[];
  columns: number;
  cells: TreeCell[];
  links: { from: string; to: string }[];
  groups: TreeGroup[];
}

/** Skill tree row used by the game for nodes it never shows. */
export const HIDDEN_ROW = 99;

export function layoutTree(nodes: TreeNodeInput[], links: TreeLinkInput[]): TreeLayout {
  const visible = nodes
    .filter((n) => !n.hidden && n.row !== HIDDEN_ROW)
    .sort((a, b) => a.row - b.row || a.column - b.column || a.id.localeCompare(b.id));
  const rows = [...new Set(visible.map((n) => n.row))];
  const rowIndex = new Map(rows.map((row, index) => [row, index]));

  const occupied = new Set<string>();
  const cells: TreeCell[] = visible.map((n) => {
    let column = n.column;
    while (occupied.has(`${n.row}:${column}`)) column += 1;
    occupied.add(`${n.row}:${column}`);
    return { node: n, rowIndex: rowIndex.get(n.row)!, column };
  });

  const ids = new Set(visible.map((n) => n.id));
  const seen = new Set<string>();
  const treeLinks: { from: string; to: string }[] = [];
  for (const link of links) {
    const id = `${link.parent}>${link.child}`;
    if (!ids.has(link.parent) || !ids.has(link.child) || seen.has(id)) continue;
    seen.add(id);
    treeLinks.push({ from: link.parent, to: link.child });
  }

  return {
    rows,
    columns: cells.length ? Math.max(...cells.map((c) => c.column)) + 1 : 0,
    cells,
    links: treeLinks,
    groups: rows.map((row) => ({ row, nodes: cells.filter((c) => c.node.row === row).map((c) => c.node) })),
  };
}
```

- [ ] **Step 4: Implement `web/src/lib/detailHtml.ts`**

```ts
/** HTML for tree detail panels, built at build time and passed to the TreeView island. */
import { type Site, imageSrc } from "../data/site";
import { formatEffect, formatNumber, scopeLabel } from "./effectText";
import { renderGameTextHtml } from "./gameText";
import { escapeHtml } from "./html";

interface ApplicationRef {
  effect: { key: string };
  scope: string | null;
  value: number;
}

function images(site: Site) {
  return { inline: site.model.inline, src: (p: string) => imageSrc(site, p) };
}

export function effectsHtml(site: Site, applications: ApplicationRef[]): string {
  if (!applications.length) return "";
  const items = applications.map((a) => {
    const effect = site.model.entities.effect.get(a.effect.key);
    const text = renderGameTextHtml(formatEffect(effect?.description ?? null, a.effect.key, a.value), images(site));
    const scope = scopeLabel(a.scope);
    return `<li>${text}${scope ? ` <span class="muted effect-note">${escapeHtml(scope)}</span>` : ""}</li>`;
  });
  return `<ul class="effect-list">${items.join("")}</ul>`;
}

export function skillDetailHtml(site: Site, skillKey: string): string {
  const skill = site.model.entities.skill.get(skillKey);
  if (!skill) return `<p class="missing" data-missing-link>${escapeHtml(skillKey)}</p>`;
  const parts: string[] = [];
  const description = renderGameTextHtml(skill.description, images(site));
  if (description) parts.push(`<p>${description}</p>`);
  if (skill.unlocked_at_rank) parts.push(`<p class="muted">Unlocks at rank ${skill.unlocked_at_rank}</p>`);
  for (const level of skill.levels) {
    const rank = level.unlocked_at_rank != null ? ` <span class="muted">· rank ${level.unlocked_at_rank}</span>` : "";
    parts.push(`<h4>Level ${level.level}${rank}</h4>${effectsHtml(site, level.effects)}`);
  }
  return parts.join("");
}

interface TechNodeRef {
  technology: { key: string };
  research_points_required: number;
  cost_per_round: number;
  resource_cost: { pooled_resources: { pooled_resource_factor: string; amount: number }[] } | null;
}

export function technologyDetailHtml(site: Site, node: TechNodeRef): string {
  const tech = site.model.entities.technology.get(node.technology.key);
  const parts: string[] = [];
  const description = tech ? renderGameTextHtml(tech.description, images(site)) : "";
  if (description) parts.push(`<p>${description}</p>`);
  const perTurn = node.cost_per_round ? ` · cost per turn ${formatNumber(node.cost_per_round)}` : "";
  parts.push(`<p class="muted">Research points: ${formatNumber(node.research_points_required)}${perTurn}</p>`);
  for (const r of node.resource_cost?.pooled_resources ?? []) {
    parts.push(`<p class="muted">${escapeHtml(r.pooled_resource_factor.replace(/_/g, " "))}: ${formatNumber(r.amount)}</p>`);
  }
  if (tech) parts.push(effectsHtml(site, tech.effects));
  return parts.join("");
}
```

- [ ] **Step 5: Implement `web/src/data/trees.ts`**

```ts
import type { SkillTree } from "../generated/character";
import type { TechnologyTree } from "../generated/technology_tree";
import { skillDetailHtml, technologyDetailHtml } from "../lib/detailHtml";
import { type TreeLayout, layoutTree } from "../lib/treeLayout";
import { type Site, imageSrc, urlFor } from "./site";

export function skillTreeLayout(site: Site, tree: SkillTree): TreeLayout {
  const nodes = tree.nodes.map((n) => {
    const skill = site.model.entities.skill.get(n.skill.key);
    return {
      id: n.key,
      row: n.indent,
      column: n.tier,
      label: n.skill.name ?? n.skill.key,
      icon: imageSrc(site, skill?.icon_image),
      url: urlFor(site, "skill", n.skill.key),
      hidden: !n.visible_in_ui,
      detailHtml: skillDetailHtml(site, n.skill.key),
    };
  });
  return layoutTree(nodes, tree.links.map((l) => ({ parent: l.parent, child: l.child })));
}

export function technologyTreeLayout(site: Site, tree: TechnologyTree): TreeLayout {
  const nodes = tree.nodes.map((n) => {
    const tech = site.model.entities.technology.get(n.technology.key);
    return {
      id: n.key,
      row: n.indent,
      column: n.tier,
      label: n.technology.name ?? n.technology.key,
      icon: imageSrc(site, tech?.icon_image),
      url: urlFor(site, "technology", n.technology.key),
      hidden: false,
      detailHtml: technologyDetailHtml(site, n),
    };
  });
  return layoutTree(nodes, tree.links.map((l) => ({ parent: l.parent, child: l.child })));
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `npx vitest run test/unit/treeLayout.test.ts test/unit/trees.test.ts`
Expected: PASS.

- [ ] **Step 7: Create the `TreeView` island**

`web/src/islands/TreeView.tsx`:

```tsx
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { TreeLayout } from "../lib/treeLayout";

interface Props {
  layout: TreeLayout;
  ariaLabel: string;
}

interface Line {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

function TreeGrid({ layout, selected, onSelect }: { layout: TreeLayout; selected: string | null; onSelect: (id: string) => void }) {
  const gridRef = useRef<HTMLDivElement>(null);
  const [lines, setLines] = useState<Line[]>([]);

  useLayoutEffect(() => {
    const grid = gridRef.current;
    if (!grid) return;
    const measure = () => {
      const box = grid.getBoundingClientRect();
      const rects = new Map<string, DOMRect>();
      grid.querySelectorAll<HTMLElement>("[data-node]").forEach((el) => rects.set(el.dataset.node!, el.getBoundingClientRect()));
      setLines(
        layout.links.flatMap((link) => {
          const a = rects.get(link.from);
          const b = rects.get(link.to);
          if (!a || !b) return [];
          return [{ x1: a.right - box.left, y1: a.top + a.height / 2 - box.top, x2: b.left - box.left, y2: b.top + b.height / 2 - box.top }];
        }),
      );
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(grid);
    return () => observer.disconnect();
  }, [layout]);

  return (
    <div className="tree-grid-wrap">
      <div ref={gridRef} className="tree-grid" style={{ gridTemplateColumns: `repeat(${layout.columns}, minmax(8rem, 1fr))` }}>
        <svg className="tree-links" aria-hidden="true">
          {lines.map((l, i) => (
            <line key={i} x1={l.x1} y1={l.y1} x2={l.x2} y2={l.y2} />
          ))}
        </svg>
        {layout.cells.map((cell) => (
          <button
            key={cell.node.id}
            type="button"
            data-node={cell.node.id}
            className={cell.node.id === selected ? "tree-node selected" : "tree-node"}
            style={{ gridRow: cell.rowIndex + 1, gridColumn: cell.column + 1 }}
            aria-pressed={cell.node.id === selected}
            onClick={() => onSelect(cell.node.id)}
          >
            {cell.node.icon && <img src={cell.node.icon} alt="" width={24} height={24} />}
            <span>{cell.node.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function TreeLines({ layout }: { layout: TreeLayout }) {
  return (
    <div className="tree-lines">
      {layout.groups.map((group, index) => (
        <details key={group.row} open={index === 0}>
          <summary>Line {index + 1} ({group.nodes.length})</summary>
          <ul>
            {group.nodes.map((node) => (
              <li key={node.id}>
                <details>
                  <summary>
                    {node.icon && <img src={node.icon} alt="" width={20} height={20} />} {node.label}
                  </summary>
                  <div dangerouslySetInnerHTML={{ __html: node.detailHtml }} />
                  {node.url && <a href={node.url}>Open page</a>}
                </details>
              </li>
            ))}
          </ul>
        </details>
      ))}
    </div>
  );
}

export default function TreeView({ layout, ariaLabel }: Props) {
  const [selected, setSelected] = useState<string | null>(layout.cells[0]?.node.id ?? null);
  const [narrow, setNarrow] = useState(false);

  useEffect(() => {
    const query = window.matchMedia("(max-width: 767px)");
    const update = () => setNarrow(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  const byId = useMemo(() => new Map(layout.cells.map((c) => [c.node.id, c.node])), [layout]);
  const current = selected ? byId.get(selected) ?? null : null;

  if (layout.cells.length === 0) return <p className="muted">No visible nodes.</p>;
  if (narrow) return <TreeLines layout={layout} />;
  return (
    <div className="tree" role="group" aria-label={ariaLabel}>
      <TreeGrid layout={layout} selected={selected} onSelect={setSelected} />
      <aside className="tree-panel" aria-live="polite">
        {current && (
          <>
            <h3>{current.label}</h3>
            <div dangerouslySetInnerHTML={{ __html: current.detailHtml }} />
            {current.url && <a href={current.url}>Open page</a>}
          </>
        )}
      </aside>
    </div>
  );
}
```

- [ ] **Step 8: Create `web/src/components/TreeStaticList.astro`**

```astro
---
import type { TreeLayout } from "../lib/treeLayout";

interface Props {
  layout: TreeLayout;
  title: string;
}

const { layout, title } = Astro.props;
---
<details class="tree-static">
  <summary>{title} (text list)</summary>
  {layout.groups.map((group, index) => (
    <div>
      <h3>Line {index + 1}</h3>
      <ul class="plain-list">
        {group.nodes.map((node) => (
          <li>
            <strong>{node.url ? <a href={node.url}>{node.label}</a> : node.label}</strong>
            <div set:html={node.detailHtml} />
          </li>
        ))}
      </ul>
    </div>
  ))}
</details>
```

- [ ] **Step 9: Use the tree view on character and technology tree pages**

In `web/src/components/pages/CharacterPage.astro`, add to the frontmatter imports:

```ts
import { skillTreeLayout } from "../../data/trees";
import TreeView from "../../islands/TreeView.tsx";
import TreeStaticList from "../TreeStaticList.astro";
```

and replace the whole `{character.skill_trees.map((tree) => ( <Section …> … </Section> ))}` block with:

```astro
{character.skill_trees.map((tree) => {
  const layout = skillTreeLayout(site, tree);
  return (
    <section class="panel wide-panel">
      <h2>Skill tree</h2>
      <p class="muted"><code>{tree.key}</code></p>
      <TreeView client:visible layout={layout} ariaLabel={`Skill tree ${tree.key}`} />
      <TreeStaticList layout={layout} title="All skills" />
    </section>
  );
})}
```

In `web/src/components/pages/TechnologyTreePage.astro`, add to the frontmatter imports:

```ts
import { technologyTreeLayout } from "../../data/trees";
import TreeView from "../../islands/TreeView.tsx";
import TreeStaticList from "../TreeStaticList.astro";
```

add `const layout = technologyTreeLayout(site, tree);` after the `tree` constant, and replace the `<Section title="Technologies"> … </Section>` block with:

```astro
<section class="panel wide-panel">
  <h2>Technologies</h2>
  <TreeView client:visible layout={layout} ariaLabel={`Technology tree ${tree.key}`} />
  <TreeStaticList layout={layout} title="All technologies" />
</section>
```

Remove the now unused `EntityLink` import from `TechnologyTreePage.astro` only if nothing else uses it (the Scope section still does — keep it).

- [ ] **Step 10: Add tree styles**

Append to `web/src/styles/theme.css`:

```css
.wide-panel { grid-column: 1 / -1; }
.tree { display: grid; grid-template-columns: minmax(0, 1fr) 18rem; gap: 1rem; }
.tree-grid-wrap { overflow-x: auto; }
.tree-grid { position: relative; display: grid; gap: 0.6rem 1.4rem; padding: 0.5rem; }
.tree-links { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; overflow: visible; }
.tree-links line { stroke: var(--border-accent); stroke-width: 1.5; }
.tree-node {
  position: relative; display: flex; gap: 0.4rem; align-items: center; min-height: 2.4rem; padding: 0.3rem 0.45rem;
  background: #1c150e; color: var(--text); border: 1px solid var(--border-accent); font: 0.8rem/1.2 var(--sans);
  text-align: left; cursor: pointer;
}
.tree-node:hover { border-color: var(--gold); }
.tree-node.selected { border-color: var(--gold); box-shadow: 0 0 0 1px var(--gold); }
.tree-panel { border-left: 1px solid var(--border); padding-left: 1rem; }
.tree-panel h4, .tree-static h4 { margin: 0.6rem 0 0.2rem; color: var(--muted); font-weight: normal; }
.tree-lines details { border-bottom: 1px solid #3a2e1d; padding: 0.3rem 0; }
.tree-lines ul { list-style: none; margin: 0; padding: 0 0 0 0.75rem; }
.tree-static { margin-top: 1rem; }
.tree-static summary { cursor: pointer; color: var(--muted); }
@media (max-width: 767px) {
  .tree { grid-template-columns: 1fr; }
}
```

- [ ] **Step 11: Build and check the tree pages**

Run: `MODEL_DIR=test/fixtures/model npm run build`
Expected: `Complete!`.

Run: `grep -c "astro-island" dist/characters/wh_main_emp_karl_franz/index.html dist/technology-trees/emp_civ_reworkd/index.html`
Expected: each ≥ 1.

Run: `grep -c "Devastating Charge" dist/characters/wh_main_emp_karl_franz/index.html`
Expected: ≥ 1 (server-rendered grid and static list).

- [ ] **Step 12: Run all unit tests and commit**

Run: `npm test`
Expected: PASS.

```bash
git add web/src web/test/unit/treeLayout.test.ts web/test/unit/trees.test.ts
git commit -F - <<'EOF'
feat(web): skill and technology tree views with detail panel

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 8: Region pages and the culture picker

**Files:**
- Create: `web/src/lib/regionCultures.ts`, `web/src/pages/data/culture-chains.json.ts`, `web/src/islands/CulturePicker.tsx`, `web/src/components/pages/RegionPage.astro`
- Modify: `web/src/components/pages/registry.ts`, `web/src/styles/theme.css`
- Test: `web/test/unit/regionCultures.test.ts`

**Interfaces:**
- Consumes: `Site`, `urlFor`, `imageSrc`, `chainsByCulture` (Task 2); components from Task 5.
- Produces:
  - `interface ChainOption { key: string; name: string; url: string | null; icon: string | null }`
  - `interface ChainGroup { category: string; chains: ChainOption[] }`, `interface CultureChoice { key: string; name: string }`
  - `cultureChoices(site: Site): CultureChoice[]`, `defaultCulture(site: Site, region: { starting_owner: { key: string } | null }): string | null`, `chainGroups(site: Site, cultureKey: string): ChainGroup[]`, `allCultureChains(site: Site): Record<string, ChainGroup[]>`
  - Static file `/data/culture-chains.json` = `allCultureChains(site)`
  - `CulturePicker` island props `{ cultures: CultureChoice[]; initialCulture: string; initialGroups: ChainGroup[]; dataUrl: string }`; renders a `select` and `.chain-group` lists
  - `PAGE_BODIES` covers all 15 page types

- [ ] **Step 1: Write the failing test**

`web/test/unit/regionCultures.test.ts`:

```ts
import path from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import { loadModel } from "../../src/data/load";
import { type Site, createSite } from "../../src/data/site";
import { allCultureChains, chainGroups, cultureChoices, defaultCulture } from "../../src/lib/regionCultures";

const FIXTURE = path.resolve(__dirname, "../fixtures/model");
let site: Site;

beforeAll(async () => {
  site = await createSite(await loadModel(FIXTURE));
});

describe("region cultures", () => {
  it("lists cultures by name", () => {
    expect(cultureChoices(site)).toEqual([{ key: "wh_main_emp_empire", name: "The Empire" }]);
  });

  it("defaults to the starting owner's culture, else the first culture", () => {
    const altdorf = site.model.entities.region.get("wh3_main_combi_region_altdorf")!;
    expect(defaultCulture(site, altdorf)).toBe("wh_main_emp_empire");
    expect(defaultCulture(site, { starting_owner: null })).toBe("wh_main_emp_empire");
    expect(defaultCulture(site, { starting_owner: { key: "not_a_faction" } })).toBe("wh_main_emp_empire");
  });

  it("groups a culture's chains by category", () => {
    const groups = chainGroups(site, "wh_main_emp_empire");
    expect(groups.map((g) => g.category)).toEqual(["happiness", "military", "money"]);
    const all = groups.flatMap((g) => g.chains);
    expect(all).toHaveLength(site.chainsByCulture.get("wh_main_emp_empire")!.length);
    const major = all.find((c) => c.key === "wh_main_EMPIRE_settlement_major")!;
    expect(major.url).toBe("/building-chains/wh_main_empire_settlement_major/");
    expect(major.icon).toBeNull();
    expect(chainGroups(site, "no_such_culture")).toEqual([]);
  });

  it("builds the shared culture file", () => {
    expect(Object.keys(allCultureChains(site))).toEqual(["wh_main_emp_empire"]);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run test/unit/regionCultures.test.ts`
Expected: FAIL — cannot resolve `../../src/lib/regionCultures`.

- [ ] **Step 3: Implement `web/src/lib/regionCultures.ts`**

```ts
import { type Site, imageSrc, urlFor } from "../data/site";

export interface ChainOption {
  key: string;
  name: string;
  url: string | null;
  icon: string | null;
}

export interface ChainGroup {
  category: string;
  chains: ChainOption[];
}

export interface CultureChoice {
  key: string;
  name: string;
}

export function cultureChoices(site: Site): CultureChoice[] {
  return [...site.model.entities.culture.values()]
    .map((c) => ({ key: c.key, name: c.name ?? c.key }))
    .sort((a, b) => a.name.localeCompare(b.name) || a.key.localeCompare(b.key));
}

export function defaultCulture(site: Site, region: { starting_owner: { key: string } | null }): string | null {
  const owner = region.starting_owner ? site.model.entities.faction.get(region.starting_owner.key) : undefined;
  const ownerCulture = owner?.culture?.key;
  if (ownerCulture && site.model.entities.culture.has(ownerCulture)) return ownerCulture;
  return cultureChoices(site)[0]?.key ?? null;
}

/** Chains a culture can build, grouped by chain category (categories sorted, chains in name order). */
export function chainGroups(site: Site, cultureKey: string): ChainGroup[] {
  const byCategory = new Map<string, ChainOption[]>();
  for (const key of site.chainsByCulture.get(cultureKey) ?? []) {
    const chain = site.model.entities.building_chain.get(key)!;
    const firstLevel = chain.levels[0] ? site.model.entities.building_level.get(chain.levels[0].key) : undefined;
    const option: ChainOption = {
      key,
      name: chain.name ?? key,
      url: urlFor(site, "building_chain", key),
      icon: imageSrc(site, firstLevel?.icon_image),
    };
    const category = chain.category ?? "other";
    const list = byCategory.get(category);
    if (list) list.push(option);
    else byCategory.set(category, [option]);
  }
  return [...byCategory.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([category, chains]) => ({ category, chains }));
}

export function allCultureChains(site: Site): Record<string, ChainGroup[]> {
  return Object.fromEntries(cultureChoices(site).map((c) => [c.key, chainGroups(site, c.key)]));
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npx vitest run test/unit/regionCultures.test.ts`
Expected: PASS.

- [ ] **Step 5: Create the shared data file route**

`web/src/pages/data/culture-chains.json.ts`:

```ts
import type { APIRoute } from "astro";
import { getSite } from "../../data/model";
import { allCultureChains } from "../../lib/regionCultures";

export const GET: APIRoute = async () =>
  new Response(JSON.stringify(allCultureChains(await getSite())), {
    headers: { "Content-Type": "application/json" },
  });
```

- [ ] **Step 6: Create the `CulturePicker` island**

`web/src/islands/CulturePicker.tsx`:

```tsx
import { useState } from "react";
import type { ChainGroup, CultureChoice } from "../lib/regionCultures";

interface Props {
  cultures: CultureChoice[];
  initialCulture: string;
  initialGroups: ChainGroup[];
  dataUrl: string;
}

let allChains: Promise<Record<string, ChainGroup[]>> | null = null;

function loadAllChains(url: string): Promise<Record<string, ChainGroup[]>> {
  allChains ??= fetch(url).then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  });
  return allChains;
}

export default function CulturePicker({ cultures, initialCulture, initialGroups, dataUrl }: Props) {
  const [culture, setCulture] = useState(initialCulture);
  const [groups, setGroups] = useState(initialGroups);
  const [status, setStatus] = useState<"ready" | "loading" | "error">("ready");

  async function choose(key: string) {
    setCulture(key);
    if (key === initialCulture) {
      setGroups(initialGroups);
      setStatus("ready");
      return;
    }
    setStatus("loading");
    try {
      const all = await loadAllChains(dataUrl);
      setGroups(all[key] ?? []);
      setStatus("ready");
    } catch {
      allChains = null;
      setStatus("error");
    }
  }

  const count = groups.reduce((n, g) => n + g.chains.length, 0);
  return (
    <div className="culture-picker">
      <label>
        Culture{" "}
        <select value={culture} onChange={(e) => void choose(e.target.value)}>
          {cultures.map((c) => (
            <option key={c.key} value={c.key}>{c.name}</option>
          ))}
        </select>
      </label>{" "}
      <span className="muted" aria-live="polite">
        {status === "loading" ? "Loading…" : status === "error" ? "Could not load building data." : `${count} building chains`}
      </span>
      {status === "ready" && count === 0 && <p className="muted">This culture has no building chains.</p>}
      {groups.map((group) => (
        <div key={group.category} className="chain-group">
          <h3>{group.category}</h3>
          <ul className="link-list">
            {group.chains.map((chain) => (
              <li key={chain.key}>
                {chain.url ? (
                  <a className="entity-link" href={chain.url}>
                    {chain.icon && <img className="game-img game-img-icon" src={chain.icon} alt="" />}
                    <span>{chain.name}</span>
                  </a>
                ) : (
                  chain.name
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 7: Create `web/src/components/pages/RegionPage.astro`**

```astro
---
import { getSite } from "../../data/model";
import CulturePicker from "../../islands/CulturePicker.tsx";
import { chainGroups, cultureChoices, defaultCulture } from "../../lib/regionCultures";
import EntityLink from "../EntityLink.astro";
import GameImage from "../GameImage.astro";
import LinkList from "../LinkList.astro";
import Section from "../Section.astro";
import StatTable from "../StatTable.astro";

interface Props {
  entityKey: string;
}

const site = await getSite();
const region = site.model.entities.region.get(Astro.props.entityKey)!;
const initialCulture = region.is_settlement ? defaultCulture(site, region) : null;
---
<Section title="Overview">
  <StatTable rows={[
    ["Campaign", region.campaign],
    ["Settlement", region.is_settlement],
    ["Province capital", region.is_province_capital],
    ["Faction capital at start", region.is_faction_capital],
    ["Building slots", region.slot_cap],
    ["Slot templates", region.template_source === "special" ? "Special settlement" : "Generic"],
    ["Region groups", region.region_groups.join(", ")],
  ]} />
  {region.province && <p>Province: <EntityLink link={region.province} /></p>}
  {region.starting_owner && <p>Starting owner: <EntityLink link={region.starting_owner} /></p>}
  {region.cultural_originator && <p>Cultural originator: <EntityLink link={region.cultural_originator} /></p>}
</Section>
<Section title="Special settlement slots" show={region.slot_templates.length > 0}>
  {region.slot_templates.map((template) => (
    <div class="slot-template">
      <h3>{template.role}{template.variant && <span class="muted"> · {template.variant}</span>}</h3>
      <p class="muted"><code>{template.key}</code></p>
      {template.resource && (
        <p>Resource: <GameImage path={template.resource.icon_image} kind="icon" /> {template.resource.name ?? template.resource.key}</p>
      )}
      <details>
        <summary>{template.permitted_chains.length} permitted building chains</summary>
        <LinkList links={template.permitted_chains} />
      </details>
    </div>
  ))}
</Section>
{initialCulture && (
  <section class="panel wide-panel">
    <h2>Buildings by culture</h2>
    <p class="muted">Building chains each culture can construct. Special settlement slots above apply on top of these.</p>
    <CulturePicker
      client:visible
      cultures={cultureChoices(site)}
      initialCulture={initialCulture}
      initialGroups={chainGroups(site, initialCulture)}
      dataUrl="/data/culture-chains.json"
    />
  </section>
)}
```

In `web/src/components/pages/registry.ts` add `import RegionPage from "./RegionPage.astro";` and the entry `region: RegionPage,` before `province`.

- [ ] **Step 8: Add styles**

Append to `web/src/styles/theme.css`:

```css
.slot-template + .slot-template { margin-top: 0.9rem; padding-top: 0.6rem; border-top: 1px solid #3a2e1d; }
.slot-template h3 { text-transform: capitalize; }
.culture-picker .chain-group { margin-top: 0.8rem; }
.culture-picker .chain-group h3 { text-transform: capitalize; }
.culture-picker .link-list { columns: 16rem; }
```

- [ ] **Step 9: Build and check**

Run: `MODEL_DIR=test/fixtures/model npm run build`
Expected: `Complete!`; `dist/regions/wh3_main_combi_region_altdorf/index.html` contains `wh_main_special_altdorf_primary` and `Buildings by culture`; `dist/data/culture-chains.json` exists.

Run: `node -e "const d=require('./dist/data/culture-chains.json'); console.log(Object.keys(d), d.wh_main_emp_empire.length)"`
Expected: `[ 'wh_main_emp_empire' ] 3`.

- [ ] **Step 10: Run all unit tests and commit**

Run: `npm test`
Expected: PASS.

```bash
git add web/src web/test/unit/regionCultures.test.ts
git commit -F - <<'EOF'
feat(web): region pages with special slots and a culture building picker

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 9: Site-wide search

**Files:**
- Create: `web/src/lib/search.ts` (browser-safe), `web/src/data/searchIndex.ts` (build time), `web/src/islands/SearchBox.tsx`
- Modify: `web/scripts/prebuild.ts`, `web/src/layouts/Layout.astro`, `web/src/styles/theme.css`
- Test: `web/test/unit/search.test.ts`

**Interfaces:**
- Consumes: `PAGE_TYPES` (Task 1); `loadModel` (Task 2); `createSite`, `urlFor`, `imageSrc` (Task 2); `mainImage` (Task 5).
- Produces:
  - `interface SearchDocument { id: string; type: string; typeLabel: string; key: string; name: string; culture: string; category: string; icon: string | null; url: string }`
  - `SEARCH_OPTIONS` (MiniSearch constructor/loadJSON options: `idField: "id"`, `fields: ["name", "key", "culture", "category"]`, `storeFields: ["type", "typeLabel", "key", "name", "icon", "url"]`), `SEARCH_QUERY` (`prefix: true`, `fuzzy: 0.2`, `boost: { name: 3 }`, `combineWith: "AND"`)
  - `interface SearchHit { id: string; type: string; typeLabel: string; key: string; name: string; icon: string | null; url: string }`, `interface ResultGroup { type: string; typeLabel: string; items: SearchHit[] }`, `groupResults(results: SearchResult[], perType?: number): ResultGroup[]`
  - `buildSearchDocuments(site: Site): SearchDocument[]`, `createSearchIndexJson(site: Site): string`
  - Prebuild writes `public/search-index.json`
  - `SearchBox` island props `{ indexUrl: string }`, rendered in the header as `.site-search input[type=search]`; results are `a.search-hit` links grouped under type labels

- [ ] **Step 1: Write the failing test**

`web/test/unit/search.test.ts`:

```ts
import MiniSearch, { type SearchResult } from "minisearch";
import path from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import { loadModel } from "../../src/data/load";
import { PAGE_TYPES } from "../../src/data/pageTypes";
import { buildSearchDocuments, createSearchIndexJson } from "../../src/data/searchIndex";
import { type Site, createSite } from "../../src/data/site";
import { SEARCH_OPTIONS, SEARCH_QUERY, groupResults } from "../../src/lib/search";

const FIXTURE = path.resolve(__dirname, "../fixtures/model");
let site: Site;

beforeAll(async () => {
  site = await createSite(await loadModel(FIXTURE));
});

describe("buildSearchDocuments", () => {
  it("indexes every entity of every page type", () => {
    const docs = buildSearchDocuments(site);
    const expected = PAGE_TYPES.reduce((n, p) => n + site.model.entities[p.type].size, 0);
    expect(docs).toHaveLength(expected);
    expect(new Set(docs.map((d) => d.id)).size).toBe(docs.length);
  });

  it("stores names, URLs and facts", () => {
    const docs = buildSearchDocuments(site);
    const gs = docs.find((d) => d.id === "unit:wh_main_emp_inf_greatswords")!;
    expect(gs).toMatchObject({ type: "unit", typeLabel: "Unit", name: "Greatswords", url: "/units/wh_main_emp_inf_greatswords/", icon: null });
    expect(gs.category).not.toBe("");
    const chain = docs.find((d) => d.id === "building_chain:wh_main_EMPIRE_barracks")!;
    expect(chain.culture).toContain("The Empire");
    const faction = docs.find((d) => d.id === "faction:wh_main_emp_empire")!;
    expect(faction.culture).toBe("The Empire");
  });
});

describe("search index", () => {
  it("round-trips through JSON and finds Greatswords first", () => {
    const index = MiniSearch.loadJSON(createSearchIndexJson(site), SEARCH_OPTIONS);
    const results = index.search("greatswords", SEARCH_QUERY);
    expect(results[0].id).toBe("unit:wh_main_emp_inf_greatswords");
    expect(results[0].url).toBe("/units/wh_main_emp_inf_greatswords/");
  });
});

describe("groupResults", () => {
  it("groups by type in first-appearance order and caps each group", () => {
    const hit = (id: string, type: string): SearchResult =>
      ({ id, score: 1, terms: [], queryTerms: [], match: {}, type, typeLabel: type.toUpperCase(), key: id, name: id, icon: null, url: `/${id}/` }) as SearchResult;
    const results = [hit("s1", "skill"), hit("u1", "unit"), hit("s2", "skill"), hit("s3", "skill")];
    const groups = groupResults(results, 2);
    expect(groups.map((g) => [g.type, g.items.map((i) => i.id)])).toEqual([
      ["skill", ["s1", "s2"]],
      ["unit", ["u1"]],
    ]);
    expect(groups[0].typeLabel).toBe("SKILL");
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run test/unit/search.test.ts`
Expected: FAIL — cannot resolve `../../src/data/searchIndex` and `../../src/lib/search`.

- [ ] **Step 3: Implement `web/src/lib/search.ts`**

```ts
/** Search options and result grouping; imported by the browser island, so no Node imports here. */
import type { Options, SearchOptions, SearchResult } from "minisearch";

export interface SearchDocument {
  id: string;
  type: string;
  typeLabel: string;
  key: string;
  name: string;
  culture: string;
  category: string;
  icon: string | null;
  url: string;
}

export const SEARCH_OPTIONS: Options<SearchDocument> = {
  idField: "id",
  fields: ["name", "key", "culture", "category"],
  storeFields: ["type", "typeLabel", "key", "name", "icon", "url"],
};

export const SEARCH_QUERY: SearchOptions = { prefix: true, fuzzy: 0.2, boost: { name: 3 }, combineWith: "AND" };

export interface SearchHit {
  id: string;
  type: string;
  typeLabel: string;
  key: string;
  name: string;
  icon: string | null;
  url: string;
}

export interface ResultGroup {
  type: string;
  typeLabel: string;
  items: SearchHit[];
}

export function groupResults(results: SearchResult[], perType = 8): ResultGroup[] {
  const groups = new Map<string, ResultGroup>();
  for (const result of results) {
    const hit: SearchHit = {
      id: String(result.id),
      type: result.type,
      typeLabel: result.typeLabel,
      key: result.key,
      name: result.name,
      icon: result.icon ?? null,
      url: result.url,
    };
    let group = groups.get(hit.type);
    if (!group) {
      group = { type: hit.type, typeLabel: hit.typeLabel, items: [] };
      groups.set(hit.type, group);
    }
    if (group.items.length < perType) group.items.push(hit);
  }
  return [...groups.values()];
}
```

- [ ] **Step 4: Implement `web/src/data/searchIndex.ts`**

```ts
import MiniSearch from "minisearch";
import { SEARCH_OPTIONS, type SearchDocument } from "../lib/search";
import { mainImage } from "./images";
import { PAGE_TYPES, type PageType } from "./pageTypes";
import { type Site, imageSrc, urlFor } from "./site";

type Entity = Record<string, any>;

function cultureNames(site: Site, keys: (string | null | undefined)[]): string {
  const names = keys.filter((k): k is string => Boolean(k)).map((k) => site.model.entities.culture.get(k)?.name ?? k);
  return [...new Set(names)].join(" ");
}

function searchCulture(site: Site, type: PageType, e: Entity): string {
  switch (type) {
    case "faction":
    case "subculture":
    case "technology_tree":
      return cultureNames(site, [e.culture?.key]);
    case "building_level":
      return cultureNames(site, e.cultures ?? []);
    case "building_chain":
      return cultureNames(site, (e.availability ?? []).map((a: Entity) => a.culture?.key));
    default:
      return "";
  }
}

function searchCategory(type: PageType, e: Entity): string {
  switch (type) {
    case "unit":
      return e.category_name ?? e.category ?? "";
    case "item":
    case "building_chain":
      return e.category ?? "";
    case "ability":
      return e.type ?? "";
    default:
      return "";
  }
}

export function buildSearchDocuments(site: Site): SearchDocument[] {
  const docs: SearchDocument[] = [];
  for (const info of PAGE_TYPES) {
    for (const entity of (site.model.entities[info.type] as Map<string, Entity>).values()) {
      docs.push({
        id: `${info.type}:${entity.key}`,
        type: info.type,
        typeLabel: info.singular,
        key: entity.key,
        name: entity.name ?? entity.key,
        culture: searchCulture(site, info.type, entity),
        category: searchCategory(info.type, entity),
        icon: imageSrc(site, mainImage(site, info.type, entity)?.path),
        url: urlFor(site, info.type, entity.key)!,
      });
    }
  }
  return docs;
}

export function createSearchIndexJson(site: Site): string {
  const index = new MiniSearch<SearchDocument>(SEARCH_OPTIONS);
  index.addAll(buildSearchDocuments(site));
  return JSON.stringify(index);
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `npx vitest run test/unit/search.test.ts`
Expected: PASS.

- [ ] **Step 6: Write the index during prebuild**

In `web/scripts/prebuild.ts`:

- change the import line `import { ModelLoadError, type Manifest } from "../src/data/load";` to `import { ModelLoadError, type Manifest, loadModel } from "../src/data/load";`
- add these imports:

```ts
import { createSearchIndexJson } from "../src/data/searchIndex";
import { createSite } from "../src/data/site";
```

- add this function before `prebuild()`:

```ts
async function writeSearchIndex(modelDir: string): Promise<void> {
  const site = await createSite(await loadModel(modelDir));
  const json = createSearchIndexJson(site);
  await mkdir(path.join(webRoot, "public"), { recursive: true });
  await writeFile(path.join(webRoot, "public", "search-index.json"), json);
  const megabytes = Buffer.byteLength(json) / 1024 / 1024;
  console.log(`prebuild: search index ${megabytes.toFixed(1)} MB`);
  if (megabytes > 10) console.warn("prebuild: search index is over the 10 MB target");
}
```

- call it at the end of `prebuild()`: `await writeSearchIndex(modelDir);`

- [ ] **Step 7: Create the `SearchBox` island**

`web/src/islands/SearchBox.tsx`:

```tsx
import MiniSearch from "minisearch";
import { type FocusEvent, type KeyboardEvent, useEffect, useMemo, useState } from "react";
import { type ResultGroup, SEARCH_OPTIONS, SEARCH_QUERY, type SearchDocument, groupResults } from "../lib/search";

interface Props {
  indexUrl: string;
}

let loadedIndex: Promise<MiniSearch<SearchDocument>> | null = null;

function loadIndex(url: string): Promise<MiniSearch<SearchDocument>> {
  loadedIndex ??= fetch(url)
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.text();
    })
    .then((text) => MiniSearch.loadJSON<SearchDocument>(text, SEARCH_OPTIONS));
  return loadedIndex;
}

export default function SearchBox({ indexUrl }: Props) {
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState<MiniSearch<SearchDocument> | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  function ensureIndex() {
    if (status !== "idle") return;
    setStatus("loading");
    loadIndex(indexUrl).then(
      (loaded) => {
        setIndex(loaded);
        setStatus("ready");
      },
      () => {
        loadedIndex = null;
        setStatus("error");
      },
    );
  }

  const trimmed = query.trim();
  const groups: ResultGroup[] = useMemo(
    () => (index && trimmed.length >= 2 ? groupResults(index.search(trimmed, SEARCH_QUERY)) : []),
    [index, trimmed],
  );
  const hits = useMemo(() => groups.flatMap((g) => g.items), [groups]);
  useEffect(() => setActive(0), [trimmed]);

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((a) => Math.min(a + 1, hits.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (event.key === "Enter" && hits[active]) {
      event.preventDefault();
      window.location.href = hits[active].url;
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  function onBlur(event: FocusEvent<HTMLDivElement>) {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false);
  }

  let position = -1;
  return (
    <div className="site-search" onBlur={onBlur}>
      <input
        type="search"
        placeholder="Search units, skills, regions…"
        aria-label="Search the wiki"
        role="combobox"
        aria-expanded={open && hits.length > 0}
        aria-controls="search-results"
        autoComplete="off"
        value={query}
        onFocus={() => {
          ensureIndex();
          setOpen(true);
        }}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
        }}
        onKeyDown={onKeyDown}
      />
      {open && trimmed.length >= 2 && (
        <div id="search-results" className="search-results" role="listbox">
          {status === "loading" && <p className="muted">Loading search…</p>}
          {status === "error" && <p className="muted">Search is unavailable.</p>}
          {status === "ready" && hits.length === 0 && <p className="muted">No matches.</p>}
          {groups.map((group) => (
            <div key={group.type} className="search-group">
              <div className="search-group-label">{group.typeLabel}</div>
              {group.items.map((item) => {
                position += 1;
                const itemPosition = position;
                return (
                  <a
                    key={item.id}
                    href={item.url}
                    role="option"
                    aria-selected={itemPosition === active}
                    className={itemPosition === active ? "search-hit active" : "search-hit"}
                    onMouseEnter={() => setActive(itemPosition)}
                  >
                    {item.icon ? <img src={item.icon} alt="" width={20} height={20} /> : <span className="search-hit-blank" />}
                    <span>{item.name}</span>
                  </a>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 8: Put search in the header**

In `web/src/layouts/Layout.astro` add to the frontmatter:

```ts
import SearchBox from "../islands/SearchBox.tsx";
```

and replace `<slot name="header" />` with:

```astro
<SearchBox client:idle indexUrl="/search-index.json" />
```

Append to `web/src/styles/theme.css`:

```css
.site-search { position: relative; flex: 1 1 18rem; max-width: 26rem; }
.site-search input { width: 100%; }
.search-results {
  position: absolute; z-index: 20; top: calc(100% + 2px); left: 0; right: 0; max-height: 70vh; overflow-y: auto;
  background: var(--panel); border: 1px solid var(--border-accent); padding: 0.4rem;
}
.search-group + .search-group { margin-top: 0.4rem; }
.search-group-label { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
.search-hit { display: flex; gap: 0.4rem; align-items: center; padding: 0.25rem 0.3rem; color: var(--text); }
.search-hit.active, .search-hit:hover { background: #3a2e1d; text-decoration: none; }
.search-hit-blank { display: inline-block; width: 20px; height: 20px; }
```

- [ ] **Step 9: Build and check**

Run: `MODEL_DIR=test/fixtures/model npm run build`
Expected: prebuild prints `search index … MB`; `Complete!`; `dist/search-index.json` exists; `dist/index.html` contains `Search the wiki`.

- [ ] **Step 10: Run all unit tests and commit**

Run: `npm test`
Expected: PASS.

```bash
git add web/scripts/prebuild.ts web/src web/test/unit/search.test.ts
git commit -F - <<'EOF'
feat(web): site-wide search over names and key facts

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 10: Home page, 404 page and the build report

**Files:**
- Modify: `web/src/pages/index.astro`, `web/package.json` (build script), `web/src/styles/theme.css`
- Create: `web/src/pages/404.astro`, `web/scripts/build-report.ts`
- Test: `web/test/unit/buildReport.test.ts`

**Interfaces:**
- Consumes: `getSite`, `buildInfo` (Task 3); `PAGE_TYPES` (Task 1); `LinkList` (Task 5).
- Produces:
  - `interface DistSummary { pages: Record<string, number>; total: number; missingLinks: number; placeholderImages: number; searchIndexBytes: number }`
  - `summarizeDist(distDir: string): Promise<DistSummary>`; running the script prints the summary
  - `npm run build` = `astro build` followed by the report

- [ ] **Step 1: Write the failing test**

`web/test/unit/buildReport.test.ts`:

```ts
import { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { summarizeDist } from "../../scripts/build-report";

async function page(dist: string, relative: string, html: string) {
  await mkdir(path.join(dist, relative), { recursive: true });
  await writeFile(path.join(dist, relative, "index.html"), html);
}

describe("summarizeDist", () => {
  it("counts pages per segment, gaps and the search index size", async () => {
    const dist = await mkdtemp(path.join(tmpdir(), "dist-"));
    await page(dist, ".", "<html>home</html>");
    await page(dist, "units", "<html>browse</html>");
    await page(dist, "units/a", '<span data-missing-link>x</span><span data-placeholder-image></span>');
    await page(dist, "units/b", '<span data-placeholder-image></span>');
    await page(dist, "regions/c", "<html>region</html>");
    await writeFile(path.join(dist, "search-index.json"), "12345");

    const summary = await summarizeDist(dist);

    expect(summary.pages).toEqual({ "(root)": 1, units: 3, regions: 1 });
    expect(summary.total).toBe(5);
    expect(summary.missingLinks).toBe(1);
    expect(summary.placeholderImages).toBe(2);
    expect(summary.searchIndexBytes).toBe(5);
  });

  it("reports zero for a search index that is not there", async () => {
    const dist = await mkdtemp(path.join(tmpdir(), "dist-"));
    await page(dist, ".", "<html>home</html>");
    expect((await summarizeDist(dist)).searchIndexBytes).toBe(0);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run test/unit/buildReport.test.ts`
Expected: FAIL — cannot resolve `../../scripts/build-report`.

- [ ] **Step 3: Implement `web/scripts/build-report.ts`**

```ts
/** Prints what the build produced: pages per type, gaps rendered, search index size. */
import { readFile, readdir, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

export interface DistSummary {
  pages: Record<string, number>;
  total: number;
  missingLinks: number;
  placeholderImages: number;
  searchIndexBytes: number;
}

export async function summarizeDist(distDir: string): Promise<DistSummary> {
  const entries = await readdir(distDir, { recursive: true, withFileTypes: true });
  const pages: Record<string, number> = {};
  let total = 0;
  let missingLinks = 0;
  let placeholderImages = 0;

  for (const entry of entries) {
    if (!entry.isFile() || entry.name !== "index.html") continue;
    const file = path.join(entry.parentPath, entry.name);
    const relative = path.relative(distDir, file).split(path.sep).join("/");
    const segment = relative.includes("/") ? relative.split("/")[0] : "(root)";
    pages[segment] = (pages[segment] ?? 0) + 1;
    total += 1;
    const html = await readFile(file, "utf-8");
    missingLinks += (html.match(/data-missing-link/g) ?? []).length;
    placeholderImages += (html.match(/data-placeholder-image/g) ?? []).length;
  }

  const searchIndexBytes = await stat(path.join(distDir, "search-index.json")).then(
    (s) => s.size,
    () => 0,
  );
  return { pages, total, missingLinks, placeholderImages, searchIndexBytes };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const distDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "dist");
  const summary = await summarizeDist(distDir);
  console.log("\nbuild report");
  for (const [segment, count] of Object.entries(summary.pages).sort(([a], [b]) => a.localeCompare(b))) {
    console.log(`  ${segment.padEnd(18)} ${count}`);
  }
  console.log(`  ${"total pages".padEnd(18)} ${summary.total}`);
  console.log(`  ${"missing links".padEnd(18)} ${summary.missingLinks}`);
  console.log(`  ${"placeholder images".padEnd(18)} ${summary.placeholderImages}`);
  console.log(`  ${"search index".padEnd(18)} ${(summary.searchIndexBytes / 1024 / 1024).toFixed(1)} MB`);
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npx vitest run test/unit/buildReport.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the report after every build**

In `web/package.json` change the build script to:

```json
"build": "astro build && tsx scripts/build-report.ts"
```

- [ ] **Step 6: Write the home page**

Replace `web/src/pages/index.astro` with:

```astro
---
import LinkList from "../components/LinkList.astro";
import { buildInfo, getSite } from "../data/model";
import { PAGE_TYPES } from "../data/pageTypes";
import Layout from "../layouts/Layout.astro";

const site = await getSite();
const types = PAGE_TYPES.map((info) => ({ ...info, count: site.model.entities[info.type].size }));
const trees = [...site.model.entities.technology_tree.values()]
  .sort((a, b) => (a.name ?? a.key).localeCompare(b.name ?? b.key))
  .slice(0, 12)
  .map((tree) => ({ type: "technology_tree", key: tree.key, name: tree.name, missing: false }));
---
<Layout title="Home" description="Units, characters, skills, buildings, technologies and regions of Total War: WARHAMMER III">
  <h1>Total War: WARHAMMER III wiki</h1>
  <p class="muted">
    Every unit, character, skill, ability, building, technology and region from game build <code>{buildInfo.buildId}</code>.
  </p>
  <section class="panel">
    <h2>Browse</h2>
    <ul class="type-grid">
      {types.map((type) => (
        <li><a href={`/${type.segment}/`}>{type.label}</a> <span class="muted">{type.count}</span></li>
      ))}
    </ul>
  </section>
  <section class="panel">
    <h2>Technology trees</h2>
    <LinkList links={trees} />
    <p><a href="/technology-trees/">All technology trees</a></p>
  </section>
  <section class="panel">
    <h2>Region building browser</h2>
    <p>Open a region to see its special settlement slots, resources, and the building chains each culture can construct there.</p>
    <p><a href="/regions/">Browse regions</a></p>
  </section>
</Layout>
```

- [ ] **Step 7: Write the 404 page**

`web/src/pages/404.astro`:

```astro
---
import Layout from "../layouts/Layout.astro";
import { PAGE_TYPES } from "../data/pageTypes";
---
<Layout title="Page not found">
  <h1>Page not found</h1>
  <p class="muted">That page does not exist in this wiki. Effects, effect bundles, difficulty levels and campaign variables have no pages of their own; they appear on the pages that use them.</p>
  <ul class="type-grid">
    {PAGE_TYPES.map((info) => <li><a href={`/${info.segment}/`}>{info.label}</a></li>)}
  </ul>
</Layout>
```

Append to `web/src/styles/theme.css`:

```css
.type-grid { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr)); gap: 0.35rem 1rem; }
```

- [ ] **Step 8: Build against the fixture and check the report**

Run: `MODEL_DIR=test/fixtures/model npm run build`
Expected: after `Complete!`, a `build report` listing `units 3` (browse plus two units), `characters 2`, `regions 5`, `total pages`, `missing links`, `placeholder images` and the search index size. `dist/404.html` exists.

- [ ] **Step 9: Run all unit tests and commit**

Run: `npm test`
Expected: PASS.

```bash
git add web/package.json web/scripts/build-report.ts web/src web/test/unit/buildReport.test.ts
git commit -F - <<'EOF'
feat(web): home page, 404 page and a build report

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 11: Full build, end-to-end tests and documentation

**Files:**
- Modify: `web/package.json` (Playwright dependency and `test:e2e` script), `README.md`
- Create: `web/playwright.config.ts`, `web/test/e2e/wiki.spec.ts`

**Interfaces:**
- Consumes: everything built so far.
- Produces: `npm run test:e2e` runs Playwright against a real build served by `astro preview`; README documents the web app.

This task downloads the Chromium browser Playwright drives (about 150 MB) and builds all 26,621 entity pages against the real model. Both take a few minutes.

- [ ] **Step 1: Add Playwright**

Run (from `web/`): `npm install --no-audit --no-fund --save-dev @playwright/test@1.63.0`
Then: `npx playwright install chromium`
Expected: Chromium downloads and installs.

Add to `web/package.json` `scripts`: `"test:e2e": "playwright test"`.

- [ ] **Step 2: Configure Playwright**

`web/playwright.config.ts`:

```ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "test/e2e",
  timeout: 30_000,
  fullyParallel: true,
  reporter: [["list"]],
  use: { baseURL: "http://localhost:4321", trace: "off" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run preview -- --port 4321",
    url: "http://localhost:4321/",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
```

- [ ] **Step 3: Build the real site**

Run: `npm run build`
Expected: prebuild names model `1eb25ce70f3a` and copies images; Astro reports about 26,637 pages (26,621 entity pages, 15 browse pages, the home page); the build report lists `units 2610`, `skills 5945`, `regions 946`, `technology-trees 34`, and a search index of a few MB. Note the wall-clock time and the missing-link and placeholder-image counts for the report.

If the build fails with a JavaScript heap out of memory error, change the build script to `node --max-old-space-size=8192 node_modules/astro/astro.js build && tsx scripts/build-report.ts` (check the path exists first with `ls node_modules/astro/astro.js`) and note it in the report.

- [ ] **Step 4: Write the end-to-end tests**

`web/test/e2e/wiki.spec.ts`:

```ts
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const distIndex = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../dist/index.html");

test.describe("wiki", () => {
  test.skip(!existsSync(distIndex), "run `npm run build` first");

  test("unit page shows stats and a card image", async ({ page }) => {
    await page.goto("/units/wh_main_emp_inf_greatswords/");
    await expect(page.locator("h1")).toHaveText("Greatswords");
    const row = page.locator("tr", { has: page.getByRole("rowheader", { name: "Melee attack", exact: true }) });
    await expect(row.locator("td")).toHaveText("32");
    const card = page.locator("img.game-img-card").first();
    await expect(card).toBeVisible();
    expect(await card.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBeGreaterThan(0);
  });

  test("skill tree shows details for the selected skill", async ({ page }) => {
    await page.goto("/characters/wh_main_emp_karl_franz/");
    const node = page.locator("button.tree-node", { hasText: "Devastating Charge" }).first();
    await node.scrollIntoViewIfNeeded();
    await node.click();
    await expect(page.locator(".tree-panel h3")).toHaveText("Devastating Charge");
  });

  test("skill tree collapses to lines on a narrow screen", async ({ page }) => {
    await page.setViewportSize({ width: 400, height: 800 });
    await page.goto("/characters/wh_main_emp_karl_franz/");
    await expect(page.locator(".tree-lines").first()).toBeVisible();
  });

  test("region page lists special slots and swaps chains per culture", async ({ page }) => {
    await page.goto("/regions/wh3_main_combi_region_altdorf/");
    await expect(page.getByText("wh_main_special_altdorf_primary")).toBeVisible();
    const picker = page.locator(".culture-picker");
    await picker.scrollIntoViewIfNeeded();
    const chains = picker.locator(".chain-group li");
    const before = await chains.count();
    expect(before).toBeGreaterThan(0);
    const select = picker.locator("select");
    const other = await select.locator("option").nth(3).getAttribute("value");
    await select.selectOption(other!);
    await expect(picker.getByText("building chains")).toBeVisible();
    await expect.poll(async () => chains.count(), { timeout: 10_000 }).not.toBe(before);
  });

  test("search finds a unit and opens it", async ({ page }) => {
    await page.goto("/");
    const box = page.getByLabel("Search the wiki");
    await box.click();
    await box.fill("greatswords");
    const hit = page.locator("a.search-hit", { hasText: "Greatswords" }).first();
    await expect(hit).toBeVisible({ timeout: 15_000 });
    await box.press("Enter");
    await expect(page).toHaveURL(/\/units\//);
  });

  test("browse page lists every unit", async ({ page }) => {
    await page.goto("/units/");
    await expect(page.locator("#browse-table tbody tr")).toHaveCount(2609);
  });

  test("unknown pages show the 404 page", async ({ page }) => {
    const response = await page.goto("/effects/anything/");
    expect(response?.status()).toBe(404);
    await expect(page.locator("h1")).toHaveText("Page not found");
  });
});
```

- [ ] **Step 5: Run the end-to-end tests**

Run: `npm run test:e2e`
Expected: 7 passed. If the culture-swap test is flaky because the second culture has the same number of chains, change `nth(3)` to another option index and say so in the report.

- [ ] **Step 6: Document the web app in `README.md`**

Add this section after the "Game data model" section:

```markdown
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
npm run test:e2e   # Playwright tests against web/dist (needs npm run build)
npm run fixtures   # regenerate web/test/fixtures/model from the real model
```

`MODEL_DIR=test/fixtures/model npm run build` builds the small fixture site in
seconds, which is the quickest way to check a change.

The site has a page for each of the 15 entity types with pages (effects,
effect bundles, difficulty levels and campaign variables are shown inline on
the pages that use them), skill and technology tree views, a region building
browser with a culture picker, and search over names and key facts. Pages are
addressed by a slug derived from the entity key.

`web/dist/` is plain static files: it deploys to any static host, and no
server is needed. Everything it serves comes from the model build, so a new
game build means: extract, load, model, then rebuild the site.
```

(The nested code fence above is part of the README text: use a normal fenced block in the README, not a nested one.)

- [ ] **Step 7: Run everything and commit**

Run: `npm test`
Expected: PASS.

```bash
git add web/package.json web/package-lock.json web/playwright.config.ts web/test/e2e README.md
git commit -F - <<'EOF'
test(web): end-to-end tests against a real build; document the web app

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```
