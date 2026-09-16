# Mining Total War: Warhammer 3 Game Files to Build a Claude Knowledge Base

## TL;DR
- **Best path:** Extract the game's DB tables and `.loc` files with **Rusted PackFile Manager (RPFM)**, load them into **DuckDB/SQLite** with foreign-key joins, resolve keys to English via the loc files, then generate denormalized per-entity markdown/JSON documents and expose them to Claude through an **MCP server with a SQL query tool** — not pure RAG embeddings.
- **Two 2025-26 shifts to know:** RPFM 5.0 (v5.0.1, 13 Jun 2025) **removed the standalone `rpfm_cli`** and replaced it with a headless **RPFM Server exposing a native MCP endpoint with "150+ tools, prompts and resources for AI agents"**; and the official **Assembly Kit (DAVE/BOB)** can export the vanilla database as human-readable, labelled XML that is cleaner than raw pack extraction for some tables.
- **Don't reinvent extraction:** community dumps (Shazbot/WH3-Dump, OwenTanzer/computational-total-war, honga.net) already parse most of the data; leverage them to bootstrap and validate, but run your own RPFM extraction as the source of truth for patch currency and completeness.

## Key Findings

1. **File structure.** Game data lives in `.pack` files in `.../Total War WARHAMMER III/data/` (Steam appid 1142710). The most important is `data.pack`, holding the `db/` folder (schema-defined binary tables), Lua campaign scripts, and CA's own scripting documentation. Localisation lives in `local_*.pack` (e.g., `local_en.pack`) as `.loc` files under `text/db/`. DLC ships as additional packs whose content carries `wh3_dlcNN` key prefixes. Each DB table is a binary file at `db/<table_name>_tables/<file_name>` with typed columns.

2. **Primary tool — RPFM.** RPFM (by Frodo45127) is the actively maintained, de-facto standard. It decodes every DB table and loc via community-maintained RON schemas and offers GUI mass-export to TSV, TSV/JSON round-tripping, reference lookups, and diagnostics. As of RPFM 5.0 the CLI is gone; automation now uses `rpfm_server` over WebSocket (`ws://127.0.0.1:45127/ws`) and MCP.

3. **Assembly Kit** (free on Steam Tools, appid 1880380) is CA's official toolset: DAVE (database editor), Terry/TEd (maps), BOB (packer). Its `raw_data/db/*.xml` gives clean, labelled XML for vanilla tables and is authoritative for some data (e.g., startpos), though modders find it slower and clunkier than RPFM.

4. **Existing community data.** honga.net has a browsable WH3 unit/faction/spell database; several GitHub repos already dump the data, including **OwenTanzer/computational-total-war**, which is purpose-built for AI agents.

5. **Hardcoded mechanics.** Damage formulas (armour, armour-piercing split, ward save, charge/mass impact), leadership, and campaign AI are engine behaviours not fully in DB tables; these are documented by CA dev blogs, wikis, and community writeups and must be captured as prose mechanics guides.

6. **Legal.** SEGA/CA's EULA permits non-commercial modding using the provided tools; extracting files for private personal use and knowledge sits inside normal modding practice. Do not sell mods, do not redistribute assets commercially, and avoid Games Workshop IP (40k/Age of Sigmar) or offensive content.

## Details

### 1. Game file structure — what lives where

Warhammer 3 packages nearly all its configuration data in **PackFiles** (`.pack`) inside `<SteamLibrary>/steamapps/common/Total War WARHAMMER III/data/`. A PackFile is a virtual filesystem the engine mounts at load; patches ship as updated packs. The load-order types are boot, release, patch, mod, and movie packs. For a knowledge base you care about the CA data packs:

- **`data.pack`** — the mother lode. Contains the `db/` folder (the database), Lua campaign/battle scripts under `script/`, and CA's scripting documentation under `/documentation/`.
- **`local_en.pack`** (and other `local_xx.pack`) — localisation `.loc` files under `text/db/`, mapping string keys to display text.
- **DLC packs** — add units, lords, etc., with `dlcNN`/`wh3_dlcNN` key prefixes.

Inside a pack the key folders are:
- **`db/`** — the database. Each subfolder is a table type, e.g. `db/main_units_tables/`, `db/land_units_tables/`, `db/unit_abilities_tables/`. Each contains a binary file (often named `data__`) with rows of typed columns. **This is where ~90% of "gameplay knowledge" lives** — unit stats, abilities, skills, techs, buildings, effects, factions.
- **`text/db/*.loc`** — localisation tables (a minimal 3-column table: Key, Text, tooltip flag). Keys follow the pattern `<table>_<column>_<record_key>`.
- **`script/`** — Lua. Campaign scripts under `script/campaign/...`; battle scripts elsewhere. Realm of Chaos vs Immortal Empires campaign logic lives here (e.g., `wh3_main_chaos/realms/wh3_realm_common.lua` holds rift timings and Chaos event-chain start), alongside the CA campaign-manager (`cm:`) and battle-script APIs.
- **`variants/`, `variantmeshes/`, models, `twui/`** — 3D model/variant definitions and UI layout (`.twui.xml`). Mostly irrelevant to a mechanics KB except `variantmeshdefinitions` (visual assembly) and twui for UI logic.

**Immortal Empires vs Realm of Chaos** are distinguished at the campaign/startpos level. Community export keys: the Realm of Chaos campaign is `campaigns_wh3_main_chaos`; Immortal Empires is `wh3_main_combi` with map `wh3_main_combi_map_1` (in the Assembly Kit's EmpireDesigndata). Which units/factions/mechanics are enabled per campaign is governed by startpos data and permission tables, not the core stat tables.

### 2. Extraction tools and their 2025–2026 state

**Rusted PackFile Manager (RPFM) — the primary tool.** RPFM is a Rust + Qt6 reimplementation of the old PackFile Manager, actively maintained, supporting WH3 and every Total War since Empire. It ships schema-aware editors for DB tables, loc files, scripts, models, etc. Key facts:

- **Schemas are mandatory.** RPFM cannot decode binary DB tables without the matching schema. Schemas are RON files in `github.com/Frodo45127/rpfm-schemas`, updated over-the-air via **Update → Check for Schema Updates**. Keep them current after every game patch.
- **GUI mass export.** Right-click a pack → **Create → Mass-Export TSV** dumps every DB table and loc to TSV at once — the simplest bulk path. (This feature was disabled in some interim releases and later restored; if absent, extract the `db` folder and export tables individually, or use the server.) "Open with External Program" opens tables directly in Excel/Calc.
- **Dependencies cache.** For reference lookups and to pull in Assembly Kit data, run **Special Stuff → Generate Dependencies Cache** (needs the Assembly Kit installed on the same drive). This resolves cross-table references.
- **CLI is deprecated as of RPFM 5.0.** `rpfm_cli` existed and worked through the 4.x line (last CLI version 4.5.4, released 25 Jul 2025) with a confirmed pattern like `rpfm_cli --game warhammer_3 pack create -p my.pack ...` (`--game` is the global game selector; `pack` is the subcommand). **RPFM 5.0.1 (13 Jun 2025) is the first release whose changelog states "Removed cli tool. If you use it, consider migrating to the new RPFM Server."** If you need scripted extraction, either pin RPFM 4.x and run `rpfm_cli --help` / `rpfm_cli pack extract --help` for the version-exact flags, or move to the server. Note: the CLI also required schemas (from `rpfm-schemas`) to decode tables.
- **RPFM Server + MCP (the important new capability).** `rpfm_server` is a headless backend exposed over WebSocket (`ws://127.0.0.1:45127/ws`) and, per RPFM's official site, a native **"MCP endpoint. 150+ tools, prompts and resources for AI agents and any client speaking the Model Context Protocol."** The v5.0 changelog confirms "Implemented MCP Server support for RPFM." This is directly relevant: **you can point Claude Code at RPFM's own MCP server to read packs and tables without writing a bespoke extractor.**

To read/edit CA packs you must enable **PackFile → Preferences → Allow Editing of CA PackFiles**, and back up `data.pack` first.

**Assembly Kit (official CA tool).** Free under Steam → Tools (WH3 Assembly Kit, appid 1880380). Components: **DAVE** (Database Visual Editor), **Terry** (campaign map), **TEd** (battle maps), **BOB** (packer/exporter), Variant Editor. For a KB:
- The AK stores vanilla data as **XML in `assembly_kit/raw_data/db/*.xml`** — e.g., `land_units.xml` with named, labelled columns. This is cleaner and more self-describing than raw binary packs for many tables and is authoritative for startpos-related content. But the AK is slower/clunkier than RPFM, doesn't expose everything, and its `raw_data` may need a Steam "verify files" or fresh install to be pristine.
- BOB exports raw_data → working_data (binary) → `.pack`. For a read-only KB you want the raw_data XML, not BOB.
- **Verdict:** Use RPFM as the primary extractor (fast, complete, schema-aware). Use Assembly Kit raw_data XML as a secondary cross-check, especially for column names and startpos data RPFM handles less directly.

**Python / third-party libraries.** There is no single mature, actively maintained Python library that decodes WH3 packs end-to-end; tooling is built on RPFM's Rust crates (`rpfm_lib`, `rpfm_extensions`, on crates.io) or the old PackFileManager C# code. The pragmatic Python approach: export TSV/JSON with RPFM, then process with pandas/Pydantic. The C# `twwstats/twwstats-dataexporter` (built on PackFileManager) extracts tables from packs and/or Assembly Kit XML to JSON and pulls images — a useful reference implementation.

### 3. Existing community data sources

- **honga.net (Royal Military Academy)** — browsable WH3 factions, units, spells, stats, compare and army-builder. Good for human cross-checking; it's HTML, not a clean feed.
- **Shazbot/WH3-Dump (GitHub)** — "Data extracted from Total War: Warhammer 3," organized as `db/<table>_tables/data__.tsv`. A ready-made TSV dump of the DB (may be patch-lagged).
- **OwenTanzer/computational-total-war (GitHub)** — the most directly relevant: "Machine-readable Total War: WARHAMMER III context for AI agents," pinned to **Patch 8.1.1 / Steam build 24237342**. It ships source-backed CSVs for unit stats (24 race CSVs, ~2,000 rows), **skill trees (500 unique character files, 521 conditional node sets)**, **technology trees (104 faction files, 6,016 nodes, 1,620 technologies, 306 typed scripted-mechanic occurrences)**, economy/buildings (104 faction CSVs), and an **Immortal Empires campaign atlas GeoPackage (641 regions, 214 provinces, 104 playable starts)** plus 1,533 battle-map records and 1,348 catchment-selection rules — all with a `context_catalog.json` routing file and an `AGENTS.md` defining retrieval/evidence rules. This is close to a turnkey answer for the "structured data for an LLM" requirement and a strong design template.
- **SymmetricChaos/WarhammerStats & TotalWarWarhammer** — Python/pandas pickles of unit data (older).
- **tw-modding.com (Total War Modding wiki)** — the best documentation for table relationships, effects, skills, localisation, and Lua. **Da Modding Den Discord** is where RPFM releases and schema help are pinned.
- **QAston/total-war-many-more-stats-mod** — surfaces hidden base stats in-game; useful for understanding which stats are stored vs engine-derived.
- **tristan00/tw_stack** — a full autonomous WH3 campaign data-collection/decision harness, if you later want *live* campaign telemetry rather than static data.

**Verdict:** Bootstrap from OwenTanzer's AI-focused datasets and Shazbot's dump to move fast, but run your own RPFM extraction as the source of truth so you control patch currency and capture tables the dumps omit.

### 4. Key table relationships

The DB is a relational schema; joins are by string keys. The most important chains for a "complete working knowledge":

**Units (battle stats):**
- `main_units` (roster entry: costs, caps, UI, `land_unit` ref) → `land_units` (the battle stats block, animations, entity) → `melee_weapons`, `missile_weapons` → `projectiles` (+ explosions). `main_units` builds on `land_units` — the land_unit key must exist before it can be referenced in main_units.
- Many displayed stats (e.g., damage-per-10s, effective-armour rolls) are computed by the engine from base fields, not stored.

**Abilities/spells:**
- `unit_abilities` → `special_ability_phases` (phase durations/effects) → ability-type tables; unit↔ability wiring via `land_units_to_unit_abilities_junctions`. Army/vortex/summon abilities via related junction tables. Effects attach through `effect_bonus_value_*_junctions` (e.g., `effect_bonus_value_unit_ability_junctions`, `..._special_ability_phase_record_junctions`).

**Skills (lords/heroes):**
- `character_skill_nodes` (tree node position) + `character_skill_node_links` (prerequisites) + `character_skill_node_sets` (which character gets which tree) → `character_skills` (name/description) → `character_skill_level_to_effects_junctions` (effects per level) → `effects` + values. Mounts/ancillaries via `character_skill_level_to_ancillaries_junctions`. Campaign agent actions via `effect_bonus_value_agent_action_record_junctions`.

**Effects (the universal glue):**
- `effects` defines a bonus id; it is attached to a **scope** (source→target, e.g., `general_to_force_own`, `faction_to_X`, `character_to_character_own`) via a `X_to_effects_junctions` table, with a numeric **value**. Bonus values route to concrete targets through the large family of `effect_bonus_value_*_junctions` tables (unit_set, missile_weapon, military_force_ability, pooled_resource, building_set, subculture, religion, ritual, siege_item, and many more). The `Cpecific/twwh2_ctm` traits-manager repo enumerates dozens of these junction tables — a useful ingestion checklist.

**Buildings/economy:**
- `building_levels` (chain levels) → `building_units_allowed` (recruitment) + `building_effects_junction` → effects. Note some content (e.g., Warriors of Chaos recruitment) lives only in `building_levels_tables`, not `building_units_allowed_tables`.

**Technology:**
- `technologies` → technology-effects junctions (or `effect_bundles`) → effects; tech trees per faction/subculture.

**Factions/subcultures:**
- `factions`, `cultures`, `subcultures`, and `units_to_groupings_military_permissions` (which faction can field which unit), plus `recruitment_sources` for Regiments of Renown/mercs.

**Resolving keys to text:** Every human-readable label comes from a loc key `<table>_<column>_<record_key>` in `text/db/*.loc` (e.g., a unit's on-screen name resolves via a `..._onscreen_name_<key>` loc key). Your pipeline must join every entity key against the loc table to produce readable names, descriptions, and tooltips; effect descriptions resolve through their own loc keys.

**Most important tables to ingest first (80/20 coverage):** `main_units`, `land_units`, `melee_weapons`, `missile_weapons`, `projectiles`, `unit_abilities`, `special_ability_phases`, all `land_units_to_*_junctions`, `character_skills` + `character_skill_nodes` + `character_skill_node_links` + `character_skill_level_to_effects_junctions`, `effects`, all `effect_bonus_value_*_junctions`, `building_levels` + `building_units_allowed`, `technologies` + tech junctions, `factions`/`cultures`/`subcultures`, `agent_subtypes`, `character_traits`, startpos/region tables, and all matching `.loc`.

### 5. Mechanics not in DB tables (hardcoded engine behaviour)

Core systems are engine logic; the DB only holds the inputs. Capture these as prose "mechanics" documents so Claude can reason about them.

- **Damage model.** Each hit = base (non-AP) damage + armour-piercing damage. Per CA's official "Feature Focus #2: Damage" dev blog, **armour reduces only the Base (non-AP) portion, by a percentage rolled between 0.5× and 1× the armour value** (rolls above 100% are treated as 100%); the community's formula is `Mitigated Damage = Base × (100 − Armour × random(0.5, 1))%`, with armour value effectively capped at 100 for mitigation (max listed armour ~200). AP damage bypasses armour entirely. Per the Fandom Combat wiki (citing Patch 1.12.1), **charging units deal impact damage scaled by speed and mass, of which 70% is armour-piercing, and the Charge Bonus is applied to attacks for 15 seconds after charging.**
- **Resistances / ward save.** Resistances come in Fire, Spell, Physical, Missile, and **Ward Save**. Per the Fandom Ward Save wiki, **Ward Save is the only universal damage-mitigation resistance, is always applied first, cannot be bypassed, and — like all resistances — is capped at 90%.** Resistances stack additively toward that cap. Physical resistance applies to all damage except magical attacks and spells. Fire resistance applies to flaming damage and is the only one that can go negative (a weakness). Spell resistance applies to spell damage (winds/vortex/magic missiles) but not to units with Magical Attacks. **Magical attacks do NOT ignore armour** (a common misconception — CA's blog confirms they are treated as regular attacks for the armour calculation).
- **Leadership/morale, fatigue, mass/knockback, hit reactions** — engine-driven; the DB stores leadership and mass values but the routing/collision math is hardcoded.
- **Campaign AI, diplomacy weighting, replenishment, corruption spread** — largely engine + Lua + startpos; documented piecemeal.

**Where it's documented:** CA's own "Feature Focus" dev blogs (community.creative-assembly.com) are the authoritative primary source; the Total War: WARHAMMER Fandom wiki (Combat, Ward Save pages), Games Lantern and ScreenRant guides, and Steam community deep-dives fill in specifics. Treat forum posts as corroborating secondary sources.

### 6. Recommended pipeline for a Claude knowledge base

**Stage A — Extract.**
1. Install RPFM + latest schemas (Update → Check for Schema Updates) and the Assembly Kit (for the dependency cache and XML cross-check).
2. Generate the Dependencies Cache so references resolve.
3. Mass-export `data.pack`, the DLC packs, and `local_en.pack` DB tables + loc to TSV via the GUI (Create → Mass-Export TSV). For automation on RPFM 5.x, drive the **RPFM Server (WebSocket/MCP)** instead of the removed CLI; on RPFM 4.x you can still script `rpfm_cli`. Optionally also grab `assembly_kit/raw_data/db/*.xml` for clean column names.

**Stage B — Normalize into a query engine.**
4. Load all TSVs into **DuckDB** (ideal here: reads TSV/Parquet directly, fast joins, no server) or SQLite. Define **Pydantic models** per table for validation. Given your Databricks/Spark background, DuckDB locally + Parquet exports is the natural fit; push Parquet to Databricks only if you later want Spark SQL at scale — for a single-game dataset DuckDB is plenty.
5. Build **views** that resolve keys to English via the loc tables and pre-join the important chains (a `unit_full` view joining main_units→land_units→weapons→abilities→loc; a `skill_full` view; an `effect_resolved` view).

**Stage C — Generate entity documents.**
6. Emit **denormalized per-entity documents** — one markdown (or JSON) per unit, lord/hero, faction, building chain, technology, spell/ability — each self-contained with resolved names, stats, abilities, and source keys. This matches your Obsidian/markdown KB habit and gives Claude clean, chunkable context.
7. Write the hardcoded-mechanics prose docs (damage, resistances, leadership, charge/mass) as a small curated set.

**Stage D — Expose to Claude.**
8. **Preferred: an MCP server with a SQL query tool** over the DuckDB/SQLite database, plus typed convenience tools (`get_unit`, `compare_units`, `find_units_by_stat`, `resolve_effect`). This lets Claude *compute* answers (filter, sort, join, aggregate) rather than hope a retrieval hit contains them — far more reliable for precise stat questions and comparisons. FastAPI + an MCP wrapper is squarely in your wheelhouse.
9. **Secondary: flat markdown entity files** in the repo/Obsidian vault for Claude Code to read directly — good for narrative/mechanics questions and grounding.
10. **RAG embeddings: only a third layer** for fuzzy natural-language lookup over the mechanics prose and descriptions. Pure vector RAG is a poor fit for exact numeric/relational queries (it cannot reliably answer "which cavalry units have >60 charge bonus and armour-piercing"), so keep SQL as the primary tool.

**Tradeoffs for Claude specifically:** the full DB vastly exceeds the context window, so the winning pattern is **tool-use querying (SQL/MCP) + targeted retrieval of denormalized docs**, not dumping data into context. Consider reusing the existing **RPFM MCP server** for live pack inspection, and the **OwenTanzer/computational-total-war** repo (which already ships `context_catalog.json` + `AGENTS.md` retrieval rules) as a fast-start dataset or blueprint.

### 7. Keeping current + legal

**Patch/DLC currency.** Every patch can change stats and occasionally table schemas. Process after a patch: (1) update RPFM schemas, (2) re-run extraction, (3) reload DuckDB, (4) regenerate docs, (5) diff against the previous version — storing TSV in git makes this trivial (a stated community reason for wanting whole-DB TSV export). Automate as an extract → build → validate pipeline, mirroring how OwenTanzer's repo separates those stages, and pin the patch/build number in your dataset metadata.

**Legal / EULA.** SEGA's EULA and CA's modding terms explicitly encourage non-commercial modding via the provided tools and grant a limited, revocable licence to use the modding tools and assets to create mods. Key constraints: **don't sell mods or solicit payment for them, don't redistribute game assets commercially, don't use other IP (40k/Age of Sigmar), and don't create offensive/sexual content.** Extracting files for **private, personal** knowledge-base use sits comfortably inside normal modding practice. If you ever publish derived datasets, follow community repos: ship only derived/transformed data (keys, stats), not bulk copyrighted art or wholesale localisation text; include a NOTICE disclaiming affiliation with CA/SEGA/GW; keep it non-commercial. This is not legal advice — the EULA is the controlling document, and CA curates the Workshop and can revoke the modding licence.

## Recommendations

**Stage 1 — Fast bootstrap (~½ day).** Clone **OwenTanzer/computational-total-war** and **Shazbot/WH3-Dump**; load their CSV/TSV into DuckDB; sanity-check a few units against honga.net. You get a queryable dataset immediately and a reference schema. *Threshold to proceed:* if the dumps' patch version matches your installed game and coverage is adequate, you may not need full extraction yet.

**Stage 2 — Own extraction (1–2 days).** Install RPFM + schemas + Assembly Kit; generate the dependency cache; Mass-Export TSV from `data.pack`, DLC packs, and `local_en.pack`. This becomes your source of truth. *Threshold:* do this as soon as you need a patch newer than the community dumps, or tables they omit (traits, agent actions, campaign/startpos).

**Stage 3 — Normalize + resolve (2–3 days).** Model tables with Pydantic; load DuckDB; build loc-resolved, pre-joined views for units, skills, effects, buildings, techs, factions. Validate row counts against the community dumps.

**Stage 4 — Generate docs + mechanics prose (2–3 days).** Emit per-entity markdown/JSON; hand-write the damage/resistance/leadership/charge-mass mechanics docs from CA's Feature Focus blogs and the wikis, citing patch numbers.

**Stage 5 — Serve to Claude (2–4 days).** Build a FastAPI-style MCP server wrapping DuckDB with a `run_sql` tool + typed helpers; add the markdown vault for Claude Code; optionally embed only the prose for fuzzy search. Evaluate the **RPFM MCP server** as a complement for live pack queries.

**Stage 6 — Maintain.** Wire a rebuild script (extract → build → validate → diff) triggered per patch; keep RPFM schemas auto-updating; store TSVs in git for diffs; pin build numbers.

**What would change these recommendations:** If RPFM's MCP server exposes tables richly enough on its own, you could skip a custom extractor and let Claude query packs live (at the cost of needing the game files present and slower ad-hoc queries). If you only ask narrative/mechanics questions (not precise stat filters), downgrade the SQL/MCP layer and lean on markdown + RAG. If you need multi-patch historical analysis or very large joins, promote the Parquet layer into Databricks/Spark.

## Caveats
- **RPFM 5.0 removed the CLI.** If you rely on scripted `rpfm_cli`, either pin RPFM 4.x (last CLI 4.5.4, 25 Jul 2025) or migrate to the RPFM Server (WebSocket/MCP). The server/MCP tool surface is new and evolving — verify exact commands against the current manual.
- **Schemas can lag a brand-new patch** by hours/days; decoding may fail until `rpfm-schemas` updates. Community TSV dumps lag patches too — always check the patch/build number (e.g., OwenTanzer's set is pinned to Patch 8.1.1 / build 24237342).
- **Some stats are engine-derived,** not stored (e.g., damage-per-second style values, effective-armour rolls). Don't treat every displayed in-game number as a DB field.
- **Community-documented formulas** (the 0.5×–1× armour roll, 70%-AP charge impact, 15s charge window) come partly from reverse-engineering and specific patches (e.g., 1.12.1); CA has changed combat math across patches, so treat exact coefficients as patch-dependent and cite the patch.
- **Mass-Export TSV availability** has varied across RPFM releases; if absent, extract the db folder and export tables (or use the server).
- Honga.net and forum posts are secondary sources and can contain errors or stale values; prefer your own extraction + CA blogs for authoritative data.