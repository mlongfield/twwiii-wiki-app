# Wiki Data: Regions and Images — Design

**Date:** 2026-09-15
**Status:** Approved in brainstorming, pending written-spec review
**Sub-project:** 2a of the wiki (sub-project 2)

> **Revised 2026-09-16:** hosting and related decisions changed; see "Decisions revised" in `2026-09-16-firebase-platform-design.md`.

## Context

Sub-project 1 (game data model) is merged: `python -m twwiki.model` turns
`twwiki.duckdb` into 17 entity types in `model/<build_id>/` (spec:
`docs/superpowers/specs/2026-09-15-game-data-model-design.md`).

Sub-project 2 is the public wiki. Brainstorming settled its requirements and
split it into two parts:

- **2a (this spec):** extend the extraction pipeline and data model with the
  data the wiki needs but the model lacks: campaign regions and provinces,
  building-chain availability, and game images.
- **2b (later spec):** the TypeScript web app built on 2a's output.

Decisions that constrain this spec and 2b:

- The wiki is **public and search-engine friendly**: every entity gets its own
  crawlable page.
- **Hosting is undecided**; 2b must be host-agnostic.
- Wiki v1 features: entity pages, **skill-tree views**, **technology-tree
  views**, a **region building browser** (pick a real campaign region),
  **site-wide search**, and **game icons and images**.
- Images in v1: ability, skill, technology, effect and effect-bundle icons;
  unit cards and unit portraits; item icons; faction flags; building and
  resource icons; inline text icons.
- Region data comes **from the extracted tables now**; decoding the campaign
  start-position files (`startpos.esf`) is a later enhancement.

## Findings this design relies on

Verified against game build `fb20553df5af` and rpfm_server 5.0.6.

**Regions**
- `regions` has 945 keys (e.g. `wh3_main_combi_region_altdorf`); all have a
  name at `regions_onscreen_<key>`. 119 have no start position: seas and
  rivers (e.g. `wh3_main_chaos_region_kraken_sea`).
- `start_pos_regions` (826 rows: 569 `wh3_main_combi`, 242 `wh3_main_chaos`,
  15 `wh3_main_prologue`) gives campaign, `faction_capital`, `slot_cap`
  (4 for 537 regions, 8 for 220, 10 for 49, plus a few 2, 6 and 12),
  `cultural_originator` (subculture) and `owning_faction`.
- `owning_faction` is a numeric id that joins `start_pos_factions.ID`, whose
  `faction` column is the faction key. 801 of 826 resolve; the rest start
  unowned.
- `region_to_province_junctions` (826) gives each region's province and
  `is_capital`; `provinces` has 316 keys named at `provinces_onscreen_<key>`.
- `regions_to_region_groups_junctions` (6,850) lists region groups.
- No table assigns an ordinary region to a slot template, settlement type or
  resource; that assignment lives in `startpos.esf`, which RPFM decodes only
  with its "Enable ESF Editor" setting on.
- Special settlements have named slot templates. Taking the region key's text
  after `_region_` as the stem and matching
  `…_special_<stem>_(primary|secondary|port)(_<variant>)*` finds templates for
  283 of 826 start-position regions (153 with one template, 115 with two, 15
  with three or four), 178 of which carry a resource (e.g.
  `wh_main_special_altdorf_primary` / `_secondary`). Variants follow the role
  (e.g. `wh3_cp1_special_shi_wu_secondary_obsidian`). The match uses 320 of the
  489 `_special_` templates; the other 169 use names that are not region
  stems (e.g. `wh2_dlc14_special_gnoblar_country_pigbarter_primary`,
  `wh3_dlc20_special_ashrak_major_secondary_obsidian`).

**Building rules**
- `slot_templates` (646) has an optional `resource`.
- `slot_template_permitted_building_chains` (1,748) permits by `chain`,
  `chain_set` or `super_chain`, with a `remove` flag.
- `building_chain_sets` (312) has `parent_set`; `building_chain_set_items`
  (2,428) adds or removes chains or superchains.
- Resolving `wh3_main_primary_core_generic_major` gives 54 chains; filtering by
  Empire availability leaves `wh_main_EMPIRE_settlement_major`.
- `building_chain_availability_sets` (3,307) and
  `building_chain_availabilities` (44) give availability by culture,
  subculture, faction and campaign for 1,821 of 1,943 chains.

**Images**
- RPFM exports images from the game files with `ExtractPackedFiles` and source
  `GameFiles`, both single files and whole folders (`{"Folder": …}`): the
  technology icon folder exported 1,506 PNGs, 13.9 MB, in 1.6 s.
- The icon folders total roughly 15,000 files; an estimated 150–250 MB per
  build.
- Every image referenced so far is PNG.
- Reference resolution against the game file list:

| Reference | Distinct values | Resolved |
|---|---|---|
| `unit_abilities.icon_name` (folder `ui/battle ui/ability_icons`) | 1,965 | 1,959 |
| `technologies.icon_name` (folder `ui/campaign ui/technologies`) | 1,475 | 1,474 |
| `character_skills.image_path` (folder `ui/campaign ui/skills`, then unique file name) | 998 | 987 |
| `effects.icon` (folder `ui/campaign ui/effect_bundles`, then unique file name) | 578 | 552 |
| `effect_bundles.ui_icon` (same) | 605 | 538 |
| `trait_categories.icon_path` (full path) | 55 | 54 |
| `unit_variants.unit_card` (folder `ui/units/icons`) | 1,225 | 1,021 |
| `building_culture_variants.icon` (folder `ui/buildings/icons`) | 1,177 | 1,176 |
| `resources.icon_filepath` (full path, backslashes) | 29 | 29 |
| `settlement_types.icon` (full path) | 16 | 16 |
| inline `[[img:…]]` targets in all loc text (`ui_tagged_images`, else the target as a path) | 659 | 646 |
| `ancillary_types.ui_icon` via `ancillaries.type` (full path) | 521 | 521 |
| `factions.flags_path` + `/mon_64.png` | 717 | 717 |
| `units_custom_battle_permissions.general_portrait` (full path) | 450 | 450 |

- `unit_variants` maps a land unit (`unit`) to `unit_card`, with an optional
  `faction` override; Greatswords map to `wh_main_emp_greatswords`. 718 of the
  2,486 default cards are not in `ui/units/icons`; 695 of those are characters.
- `units_custom_battle_permissions.general_portrait` (450 distinct files in
  `ui/portraits/portholes`) gives a portrait for 1,119 units and covers 615
  of the 718 missing cards (e.g. `wh3_dlc26_ogr_cha_paymaster` →
  `ui/portraits/portholes/no_culture/ogr_paymaster_campaign_01_0.png`).
- `ui_tagged_images` (589 rows: `key`, `image_path`) is the game's table for
  inline `[[img:<key>]]` text icons, e.g. `icon_hero` →
  `ui/skins/default/icon_agent_small.png`, `brt_aquitaine` →
  `UI/Flags/wh_dlc05_brt_aquitaine/mon_24.png`. The remaining targets are
  written as paths.
- Items: `ancillaries.type` → `ancillary_types.ui_icon` (full path) resolves for
  all 2,671 items (folders `ui/campaign ui/ancillaries`, `ui/campaign ui/mounts`,
  `ui/battle ui/ability_icons`, `ui/skins/default`).
- Factions: `factions.flags_path` (e.g. `ui\flags\wh_main_emp_empire`) holds
  `mon_24.png`, `mon_64.png` and `mon_256.png` for all 717 factions.
- Paths in tables can contain repeated separators (`UI\Flags\\wh_main_emp_empire`).

## Goals

- Region and province entities with every fact the tables provide, plus exact
  slot templates, resources and permitted chains for special settlements.
- Building-chain availability so the web app can show which chains a culture
  can build.
- Every image reference the wiki needs resolved to a real file shipped with
  the model output.
- Image and region gaps counted in the manifest, never silently dropped.

## Non-goals

- Decoding `startpos.esf`, and therefore exact slots and resources for the 543
  settlements without a matched special template.
- Matching the 169 special templates whose names are not region stems.
- Portraits other than a unit's custom-battle portrait (no faction-leader art,
  no campaign character portraits), 3D art, loading-screen art, DDS or TGA
  conversion.
- Per-faction unit card and portrait overrides (only the default card and the
  first custom-battle portrait).
- Anything in the web app (2b): rendering, search indexing, tree layout.

## Architecture

```
extract (+ image folders) → raw/<build_id>/ → load (unchanged) → twwiki.duckdb → model (+ regions, + images) → model/<build_id>/
```

### Extract stage

A new module `twwiki/extract_images.py` runs after the tables inside
`extract()`:

- For each folder in `config.yaml` `images.folders`, it calls
  `ExtractPackedFiles` with `["", {"GameFiles": [{"Folder": <folder>}]}, <staging>/images, false]`.
- Initial `images.folders`: `ui/battle ui/ability_icons`,
  `ui/campaign ui/technologies`, `ui/campaign ui/skills`,
  `ui/campaign ui/effect_bundles`, `ui/campaign ui/ancillaries`,
  `ui/campaign ui/mounts`, `ui/campaign ui/climate_types`, `ui/units/icons`,
  `ui/buildings/icons`, `ui/portraits/portholes`, `ui/flags`,
  `ui/frontend ui/faction_bullets`, `ui/common ui/unit_category_icons`,
  `ui/cheat_sheet`, `ui/skins` (about 26,000 files).
- The extract manifest gains `images: {folders: {<folder>: <file count>}, failed_folders: [{folder, error}]}`.
- The build id additionally covers the packs that contain files under the
  configured folders, identified from the dependency cache listing
  (`container_name`). The existing `raw/fb20553df5af/` has no images, so the
  next extraction produces a new build directory; `raw/` stays append-only.

The load stage is unchanged: images never enter DuckDB.

### Model stage

New and changed modules in `twwiki/model/`:

| Module | Change |
|---|---|
| `images.py` (new) | `ImageIndex`: scan `raw/<build_id>/images` once; resolve references; record usage and gaps |
| `regions.py` (new) | `region` and `province` entities; slot-template and chain-set resolution |
| `context.py` | `Context` gains `images: ImageIndex` |
| `buildings.py` | `building_chain.availability`; `building_level.icon_image` |
| `abilities.py`, `characters.py`, `technologies.py`, `effects.py`, `items.py`, `units.py` | Add the `*_image` fields listed below |
| `schemas.py` | New models and fields |
| `build.py` | Register `regions`; copy images; write `images/inline.json`; manifest `images` section |

The model locates images at `<paths.raw_dir>/<build_id>/images`, where
`build_id` comes from the database's `_build` table.

## Entities

### region (945)

| Field | Type | Source |
|---|---|---|
| `key` | str | `regions.key` |
| `name` | str \| null | `regions_onscreen_<key>` |
| `campaign` | str \| null | `start_pos_regions.campaign` |
| `is_settlement` | bool | region has a `start_pos_regions` row |
| `province` | Link \| null | `region_to_province_junctions` |
| `is_province_capital` | bool | `region_to_province_junctions.is_capital` |
| `starting_owner` | Link (faction) \| null | `start_pos_regions.owning_faction` → `start_pos_factions.ID` → `faction` |
| `is_faction_capital` | bool | `start_pos_regions.faction_capital` |
| `slot_cap` | int \| null | `start_pos_regions.slot_cap` |
| `cultural_originator` | Link (subculture) \| null | `start_pos_regions.cultural_originator` |
| `region_groups` | list[str] | `regions_to_region_groups_junctions` |
| `template_source` | `"special"` \| `"generic"` | `special` when at least one slot template matched |
| `slot_templates` | list[SlotTemplate] | name-matched templates, sorted by role then key |

`SlotTemplate`:

```
{ "key": "wh_main_special_altdorf_primary",
  "role": "primary",                 # "primary", "secondary" or "port"
  "variant": null,                   # text after the role, e.g. "obsidian", "major"
  "resource": { "key": "res_rom_oil", "name": "…", "icon_image": "ui/…png" } | null,
  "permitted_chains": [Link, …] }    # building_chain links, sorted by key
```

Template matching: the stem is the region key's text after its first
`_region_` (this covers `wh3_main_combi_region_`, `wh3_main_chaos_region_` and
`wh3_prologue_region_` keys). A slot template matches when its key ends with
`_special_<stem>_<role>` optionally followed by `_<variant>` segments, where
role is `primary`, `secondary` or `port`; `variant` is the text after the role
joined with `_`, or null. All matches are included. Special templates that
match no region are counted, not guessed at. Resource names come from `resources_onscreen_text_<key>` (e.g.
`res_stone_trolls` → "Stone Trolls Den"), null when absent or empty.

Permitted chains for a template: for each
`slot_template_permitted_building_chains` row, a `chain` adds or removes that
chain, a `super_chain` adds or removes every chain with that
`building_superchain`, and a `chain_set` adds or removes that set's resolved
chains. A set's resolved chains are its own items (chains and superchains,
honouring `remove`) plus its `parent_set`'s resolved chains, recursively, with
cycle protection. Removals apply after additions.

### province (316)

| Field | Type | Source |
|---|---|---|
| `key` | str | `provinces.key` |
| `name` | str \| null | `provinces_onscreen_<key>` |
| `campaign` | str \| null | campaign of its regions (first non-null) |
| `regions` | list[Link] | `region_to_province_junctions`, sorted by key |
| `capital` | Link (region) \| null | the region with `is_capital` |

### Changes to existing entities

- **`building_chain.availability`**: list of
  `{culture: Link|null, subculture: Link|null, faction: Link|null, campaign: str|null}`
  from `building_chain_availability_sets` joined to
  `building_chain_availabilities` on `set_id = id`; empty strings become null;
  sorted by culture, subculture, faction, campaign; duplicates removed.
- **Image fields**: each holds a path relative to `model/<build_id>/images/`
  (lower-case, forward slashes) or null.

| Entity | New field | Resolved from |
|---|---|---|
| `ability` | `icon_image` | `icon` in `ui/battle ui/ability_icons` |
| `skill` | `icon_image` | `image` in `ui/campaign ui/skills`, then unique file name |
| `technology` | `icon_image` | `icon` in `ui/campaign ui/technologies` |
| `effect` | `icon_image`, `icon_negative_image` | `icon`, `icon_negative` in `ui/campaign ui/effect_bundles`, then unique file name |
| `effect_bundle` | `icon_image` | `icon` in `ui/campaign ui/effect_bundles`, then unique file name |
| `trait` | `icon_image` | `trait_categories.icon_path` for the trait's `icon` category |
| `unit` | `card_image` | `unit_variants.unit_card` for the unit's land unit where `faction` is empty, in `ui/units/icons` |
| `building_level` | `icon_image` | `building_culture_variants.icon` of the variant chosen for the name, in `ui/buildings/icons` |
| `region.slot_templates[].resource` | `icon_image` | `resources.icon_filepath` |
| `unit` | `portrait_image` | `units_custom_battle_permissions.general_portrait`, first non-empty by faction; the web app shows it where `card_image` is null |
| `item` | `icon_image` | `ancillary_types.ui_icon` for the item's `type` |
| `faction` | `flag_image` | `flags_path` + `/mon_64.png` |

- **`images/inline.json`**: an object mapping every distinct `[[img:<target>]]`
  target found in any entity text to its image path or null. A target that is
  a `ui_tagged_images` key resolves through that row's `image_path`; any other
  target is resolved as a path (folder `ui/skins/default`, then unique file
  name).

## Image resolution

`ImageIndex.resolve(field: str, value: str | None, folders: list[str]) -> str | None`:

1. Empty or null value → null (not counted).
2. Normalise: lower-case, backslashes to forward slashes, collapse repeated
   slashes, trim.
3. Try, in order: the value as a path; each `folder/value`; each of those
   with `.png` appended when the value has no extension.
4. Otherwise, if the file name (with `.png` appended when needed) occurs
   exactly once in the index, use it.
5. Otherwise null: counted as `ambiguous` when the file name occurs more than
   once, else `missing`.

Every resolved path is recorded as used; `build.py` copies exactly the used
files. Counts are kept per `field`, named `<entity type>.<field>`
(e.g. `unit.card_image`, `inline`).

## Build flow

1. Open context; build `ImageIndex` from `raw/<build_id>/images`
   (`available: false` when the directory is absent).
2. Register catalogs (now including `region` and `province`).
3. Build all entities; builders call `ctx.images.resolve(...)`.
4. Fill reverse links, validate, as today.
5. Write entities, indexes and schemas to `model/<build_id>.partial/`.
6. Copy used images to `images/`; write `images/inline.json`.
7. Write the manifest with the `images` section and
   `regions: {"special_templates_unmatched": <count>}`; rename to
   `model/<build_id>/` using the existing safe-replace sequence.

Manifest `images` section:

```
{ "available": true,
  "files_copied": <int>,
  "fields": { "unit.card_image": {"referenced": <int>, "resolved": <int>, "missing": <int>, "ambiguous": <int>}, … } }
```

## Error handling

| Situation | Behaviour |
|---|---|
| An image folder fails to export | Listed in extract manifest `images.failed_folders`; extraction continues |
| Image reference not found | Field null; counted as `missing` for that field |
| Image file name matches several files | Field null; counted as `ambiguous` for that field |
| `raw/<build_id>/images` absent | All image fields null; manifest `images.available: false`; build succeeds |
| Region's `owning_faction` id does not resolve | `starting_owner` null; counted as missing link `region.starting_owner->faction` |
| Settlement (`is_settlement` true) has no province row | `province` null; counted as missing link `region.province->province` (seas and rivers never have one and are not counted) |
| Special slot template matches no region | Counted in manifest `regions.special_templates_unmatched` |
| Chain-set cycle | Cycle broken; no error (guarded recursion) |
| Copying an image fails | Build fails; nothing is published |
| Entity fails schema validation | Build fails; nothing is published (unchanged) |

## Testing

pytest, following sub-project 1's layers.

**Unit tests (in-memory fixtures):**
- `ImageIndex`: exact path, folder, added `.png`, unique file name, ambiguous,
  missing, backslash and case normalisation, per-field counts, used-set.
- `extract_images`: calls `ExtractPackedFiles` once per configured folder with
  the folder form; records counts; a failing folder is listed and the others
  still run (fake client).
- Regions: template name matching including a variant suffix, a port role, a
  `wh3_prologue_region_` key, a region with no match, and the unmatched
  special-template count; permitted-chain resolution through a chain set with a parent
  set and a `remove` row; owner join including an unresolved id; a sea region
  (`is_settlement` false); province capital; schema validation.
- `building_chain.availability`: scoped rows, empty strings to null, sorting,
  de-duplication.
- Image fields on ability, skill, technology, effect, effect bundle, unit card
  (`unit_variants`) and portrait, item (via type), faction flag, trait (via
  category) and building level; inline targets through `ui_tagged_images`.
- `write_output`: copies only used images, writes `inline.json`, manifest
  `images` section; with images unavailable, image fields are null and the
  build succeeds.

**Real-data tests (skipped without `twwiki.duckdb`, and image assertions skipped
when the build has no `images/` directory):**
- Counts: 945 regions, 316 provinces; existing 17 counts unchanged.
- `wh3_main_combi_region_altdorf`: name "Altdorf", province
  `wh3_main_combi_province_reikland`, `is_province_capital` true,
  `starting_owner` `wh_main_emp_empire`, `is_faction_capital` true,
  `slot_cap` 10, `template_source` "special", slot template keys
  `wh_main_special_altdorf_primary` and `wh_main_special_altdorf_secondary`.
- `wh3_main_combi_region_grom_peak`: slot templates
  `wh2_dlc15_special_grom_peak_secondary` (resource `res_rom_oil`) and
  `wh3_main_special_grom_peak_primary` (resource `res_stone_trolls`).
- `wh3_main_chaos_region_kraken_sea`: `is_settlement` false.
- `wh_main_EMPIRE_settlement_major` availability includes culture
  `wh_main_emp_empire`.
- `unit` `wh_main_emp_inf_greatswords`: `card_image`
  `ui/units/icons/wh_main_emp_greatswords.png`.
- `ability` `wh2_dlc09_army_abilities_barrage_of_the_legion`: `icon_image`
  `ui/battle ui/ability_icons/wh2_dlc09_army_abilities_barrage_of_the_legion.png`.
- `item` `wh2_dlc09_anc_magic_standard_banner_of_the_hidden_dead`: `icon_image`
  `ui/campaign ui/ancillaries/wh2_dlc09_anc_magic_standard_banner_of_the_hidden_dead.png`.
- `faction` `wh_main_emp_empire`: `flag_image` `ui/flags/wh_main_emp_empire/mon_64.png`.
- `unit` `wh3_dlc26_ogr_cha_paymaster`: `portrait_image`
  `ui/portraits/portholes/no_culture/ogr_paymaster_campaign_01_0.png`.
- Missing and ambiguous image counts per field do not exceed
  `tests/model/missing_images_baseline.json`, generated from the first real
  build.

## Out-of-scope follow-ups

- Decode `startpos.esf` for exact slots, settlement types and resources of all
  settlements.
- Per-faction unit card and portrait overrides; faction-leader and campaign
  character portraits.
- Generic orphan-junction-row counter (offered as a separate task).
