# Game Data Model — Design

**Date:** 2026-09-15
**Status:** Approved in brainstorming, pending written-spec review
**Sub-project:** 1 of 5

## Context

The pipeline already extracts Total War: WARHAMMER III data from RPFM's vanilla
dependency cache and loads it into `twwiki.duckdb`: 1,520 typed tables, 1.1M
rows, 241,972 loc entries, with every column's key and reference flags in
`_columns`.

The end goal is a hosted web app with a wiki and a campaign designer. It is
split into five sub-projects, built in this order, each with its own spec,
plan and implementation:

1. **Game data model** (this spec): raw tables into curated entities.
2. **Wiki**: cross-linked, searchable pages built on the model.
3. **Stat engine**: unit + effects to final stats. Preceded by a feasibility
   spike, because how the game combines bonuses lives partly in compiled code
   and Lua scripts rather than data.
4. **Character planner**: skill trees, items and traits feeding the engine.
5. **Army composition planner**: rosters, caps, costs and lord effects
   feeding the engine.

Decisions that constrain this spec:

- The app is a **hosted TypeScript full-stack web app**. The stat engine will
  run in both browser and server.
- The only server-side user feature is **shareable build links**. No accounts,
  no multi-patch comparison, no mod support.
- Wiki v1 covers **all four content areas**: units; lords and heroes with skill
  trees; abilities, spells and effects; campaign content.
- The model lives in **a Python stage of the existing pipeline**. The web app
  consumes its output and never reads the 1,520 raw tables.

## Goals

- One curated, display-ready document per game entity, with names resolved
  and cross-references as links.
- Effects kept structured enough for the future stat engine to compute from,
  without re-deriving targeting from raw tables.
- A single typed contract shared by the Python model and the TypeScript app.
- Gaps in game data are visible and counted, never silently dropped.

## Non-goals

- Calculating final stats. That is the stat engine (sub-project 3).
- Display grouping or deduplication of near-identical records (for example,
  Alarielle's four character records). The model keeps every record; the wiki
  decides presentation.
- Effects applied by Lua scripts (`data_script.pack`).
- Mods, multiple game builds side by side, non-English text.
- Rendering game text markup. Text is passed through with markup intact.

## Architecture

The pipeline gains a fourth stage:

```
extract → raw/<build_id>/ → load → twwiki.duckdb → model → model/<build_id>/ → web app
```

`python -m twwiki.model` reads `twwiki.duckdb` read-only and writes
`model/<build_id>/`. The build id comes from the database's `_build` table.

Code lives in a `twwiki/model/` package:

| Module | Responsibility |
|---|---|
| `context.py` | DuckDB connection, loc resolver, link registry, manifest counters |
| `schemas.py` | Pydantic models for every entity type (the contract) |
| `effects.py` | Effects, effect bundles, bonus targets, unit-set membership |
| `abilities.py` | Unit abilities, special-ability parameters, phases |
| `units.py` | Units with base stats, weapons, abilities, availability |
| `characters.py` | Characters, skills, skill trees |
| `campaign.py` | Buildings, technologies, items, traits, factions, cultures |
| `build.py` | Orchestration, reverse links, indexes, schema export, manifest |
| `__main__.py` | CLI entry point |

### Output layout

```
model/<build_id>/
    manifest.json
    entities/<type>.jsonl          one entity per line
    index/<type>.json              browse/search lists
    schema/<type>.schema.json      JSON Schema per entity type
```

Entity types: `unit`, `character`, `skill`, `ability`, `effect`,
`effect_bundle`, `building_level`, `building_chain`, `technology`, `item`,
`trait`, `faction`, `culture`, `subculture`. Roughly 45,000 entities in total.

JSON Lines per type keeps files diffable line by line without writing 45,000
separate files.

## Shared shapes

**Link**, used for every reference between entities:

```
{ "type": "unit", "key": "wh_main_emp_inf_greatswords", "name": "Greatswords" }
{ "type": "unit", "key": "some_key", "name": null, "missing": true }
```

**EffectApplication**, used everywhere an effect is applied: skill levels,
items, buildings, technologies, trait levels, effect bundles.

```
{ "effect": Link, "scope": "force_to_force_own", "value": 4.0,
  "source": Link,
  "value_damaged": 2.0, "value_ruined": 0.0 }   # buildings only
```

**Text**: display strings keep game markup (`[[img:…]]`, `[[col:…]]`,
`[[sl:…]]`, `[[url:…]]`, `[[i]]`, `[[b]]`) and placeholders (`%+n`, `%n`)
unchanged. A missing or empty loc entry is `null`.

## Entity contents

### unit
Key: `main_units.unit` (2,609).

- Identity: name, caste, category, class; link to its `character` if it is a
  lord or hero.
- Cost: recruitment cost, upkeep cost, campaign and multiplayer caps.
- Base battle stats as components, not totals: number of men, hit points per
  entity (`battle_entities.hit_points`), bonus hit points, walk/run/charge
  speeds, melee attack, melee defence, charge bonus, morale, armour value
  (`unit_armour_types`), shield, damage modifiers (physical, magic, flame,
  missile, all).
- Weapons: melee weapon record (damage, AP damage, bonus vs large/infantry,
  splash); missile weapon with its projectile embedded (damage, AP damage,
  bonuses, range, reload, projectile count, shots per volley); ammo.
- Links: mount, abilities (`land_units_to_unit_abilites_junctions`),
  attributes (via `attribute_group`).
- Unit sets: the resolved list of unit sets this unit belongs to. Sets with an
  experience-level range are included with `conditional: true` and their range.
- Availability: custom-battle factions (`units_custom_battle_permissions`) and
  campaign buildings that recruit it (`building_units_allowed`).

### character and skill
Character key: agent subtype (613).

- Name, agent type (`general`, `wizard`, `champion`, `dignitary`, `spy`,
  `runesmith`, `engineer`), permitted factions
  (`faction_agent_permitted_subtypes`), associated unit, lore of magic.
- Skill trees: one per node set (`character_skill_node_sets`), each with its
  faction, subculture and campaign restrictions, and:
  - nodes (`character_skill_node_set_items` → `character_skill_nodes`): skill
    link, indent, tier, points on creation, required number of parents,
    visibility
  - links (`character_skill_node_links`): parent, child, `REQUIRED` or
    `SUBSET_REQUIRED`, initial descent tiers
  - locks (`character_skill_nodes_skill_locks`)

Skill key: `character_skills.key` (5,944). Name, description, image, unlock
rank, background-skill flags, and per level a list of `EffectApplication`
(`character_skill_level_to_effects_junctions`).

### ability
Key: `unit_abilities.key` (2,899).

- Name, description, type, source type, icon, hidden flags.
- Activation parameters (`unit_special_abilities`): active time, recharge,
  initial recharge, uses, range, targets (self/friends/enemies/ground),
  passive, mana cost, wind-up time, miscast chance, spawned unit link,
  activated projectile link.
- Phases, in order (`special_ability_to_special_ability_phase_junctions` →
  `special_ability_phases`): targets, duration, stat changes
  `{stat, value, how}` from `special_ability_phase_stat_effects` where `how` is
  `add` or `mult`, attribute changes, damage, heal, and other phase fields.
- Reverse links: units and characters that have it; effects that grant or
  modify it.

### effect and effect_bundle
Effect key: `effects.effect` (15,064). Description template, category, icon,
priority, `is_positive_value_good`, and **bonus targets**: the 53
`effect_bonus_value_*` tables normalised to one list

```
{ "bonus_value_id": "melee_attack_mod", "target_kind": "unit_set",
  "target": Link, "source_table": "effect_bonus_value_ids_unit_sets" }
```

`target` is null for tables with no target column (for example
`effect_bonus_value_basic_junction`). Reverse links: every source that applies
this effect.

Effect bundle key: `effect_bundles.key` (5,855). Title, description, target,
global flag, and a list of `EffectApplication`.

### Campaign content

- **building_level** (5,259): name (culture-variant loc, generic variant
  first), chain link, level, create time, costs, upkeep, cultures, effects
  (`building_effects_junction`, including damaged/ruined values), units
  recruited.
- **building_chain**: name, levels in order.
- **technology** (1,869): name, description, icon, civil/engineering/military
  and hidden flags, building level that unlocks it, tree node and links
  (`technology_nodes`, `technology_node_links`), required technologies and
  buildings, effects (`technology_effects_junction`). Research cost is out of
  scope for this spec: `technologies` has no cost column and its source has
  not been confirmed.
- **item** (2,671): name, description, type, category, subcategory, legendary
  flag, allowed agents and subtypes, required skills, effects
  (`ancillary_to_effects`).
- **trait** (744): name, levels (`character_trait_levels`), each with effects
  (`trait_level_effects`), antitraits.
- **faction** (717), **culture**, **subculture**: names, hierarchy, and the
  units, lords and heroes each can use.

## Build flow

1. Create the context: open DuckDB read-only, load the loc lookup into memory,
   start the link registry.
2. Build effects and bonus targets.
3. Resolve unit-set membership once: evaluate each set's
   `unit_set_to_unit_junctions` rules (unit record, caste, category, class,
   `exclude`) against every unit.
4. Build abilities, then units, then skills and characters, then campaign
   content.
5. Reverse-link pass from the link registry.
6. Validate every entity with its Pydantic model while writing.
7. Write indexes, export JSON Schemas, write the manifest.
8. Write to `model/<build_id>.partial/` and rename to `model/<build_id>/`
   only when every step succeeds. An existing `.partial` directory is removed
   first.

Target: a full model build in under two minutes on the current dataset.

## Contract with the web app

- Pydantic models in `schemas.py` are the single source of truth.
- The build exports `schema/<type>.schema.json` from them.
- The web app (sub-project 2, in `web/` in this repo) generates its TypeScript
  types from those files with `json-schema-to-typescript`.
- New dependency: `pydantic` (v2).

## Error handling

The principle: **gaps in the game data are reported; bugs in the model stop the
build.**

| Situation | Behaviour |
|---|---|
| Loc entry missing or empty | Field is `null`; manifest counts missing names per type |
| Reference to a record that does not exist | Link kept with `name: null, missing: true`; manifest counts per link type |
| Source table absent (failed to decode) | Entity type marked `partial` in manifest with the missing table; build continues |
| Entity fails schema validation | Build fails; nothing is published |

`manifest.json` contains: build id, model version, generated-at timestamp,
entity counts per type, missing-name counts, missing-link counts, partial types.

## Testing

pytest, with three layers:

1. **Pure logic** against small in-memory DuckDB fixtures: unit-set rule
   evaluation (including `exclude`), bonus-target normalisation across table
   shapes, the link registry and missing-link handling, markup passed through
   unchanged.
2. **Known entities**, checked against the current build:
   - Greatswords (`wh_main_emp_inf_greatswords`): 120 men, 8 hit points per
     entity plus 68 bonus, melee attack 32, melee defence 30, weapon
     `wh_main_emp_greatsword` with 10 damage and 25 AP damage, armour 95.
   - Karl Franz (`wh_main_emp_karl_franz`): one tree
     (`wh_main_skill_node_set_emp_karl_franz`) with 51 nodes; Leader of Men
     grants leadership aura size +50%.
   - Hold the Line! (`wh_main_lord_passive_hold_the_line`): passive, effect
     range 35, one phase with melee defence +5 (`add`) and morale +4 (`add`),
     linked from 18 land units.
   - Training Field (`wh_main_emp_barracks_1`): chain
     `wh_main_EMPIRE_barracks`, level 0, create cost 750, culture
     `wh_main_emp_empire`.
3. **Whole-build checks**: entity counts equal source row counts (for example
   units = 2,609); every entity validates; missing-link rate per link type does
   not exceed the baseline recorded in the tests.

Tests that need the real database are skipped with a clear message when
`twwiki.duckdb` is absent.

## Data findings this design relies on

- Each vanilla DB table is one `data__` file in `db.pack`; loc files come from
  `local_en.pack`; no duplicate keys in any table or in loc.
- Effect descriptions: 14,550 of 15,064 effects have loc text.
- Effects reach units through bonus value ids (`melee_attack_mod`,
  `melee_damage_mod_mult`, …) and unit sets whose membership is defined by
  unit, caste, category or class rules.
- Ability phase stat changes state `add` or `mult` explicitly.
- Skill tree links are `REQUIRED` (10,470) or `SUBSET_REQUIRED` (10,120).
- Building names come from `building_culture_variants_name_` + building +
  culture + subculture + faction, concatenated without separators.
