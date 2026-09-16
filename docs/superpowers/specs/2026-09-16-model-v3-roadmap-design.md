# Game Data Model Refinement Roadmap — Design

**Date:** 2026-09-16
**Status:** Approved in brainstorming, pending written-spec review
**Scope:** Roadmap for model versions 3–8. Each area below gets its own detailed spec, plan and pull request.

## Context

The pipeline extracts DB tables and loc text through rpfm_server into `raw/<build_id>/`, loads them into `twwiki.duckdb`, and builds a curated model: 19 entity types, 48,599 entities, model version 2, written to `model/<build_id>/`. That model feeds the static wiki (`web/`), published to Firebase as https://twwiii-wiki.web.app. The stat engine, character planner and army planner are still to come.

On 2026-09-16 five audits compared the model and wiki with what a useful wiki and planning tool need. The reports are in `docs/superpowers/audits/`:

- `2026-09-16-model-audit.md`: builders, schemas, `twwiki.duckdb` and the link report, checked against the owner's research guide, `docs/superpowers/research/2026-09-16-tww3-game-data-pipeline-guide.md` ("Mining Total War: Warhammer 3 Game Files to Build a Claude Knowledge Base").
- `2026-09-16-wiki-page-code-audit.md`: consistency across the 15 page types, and which model fields the pages show.
- `2026-09-16-live-site-review.md`: the live site on desktop and at 375 px.
- `2026-09-16-game-docs-audit.md`: `documentation/` in `data.pack`, and the Lua campaign scripts in `data_script.pack`.
- `2026-09-16-game-ui-audit.md`: the `ui/` layout XML (`.twui.xml`, `metadata.json`, font and colour definitions).

All reports use build `1eb25ce70f3a` (game Patch 8.1, build 4194776). Their paths to extracted files point at a session scratchpad that no longer exists; the findings and counts stand on their own.

### What the audits found (summary)

- **Wrong numbers on unit pages.** 1,041 of 1,070 mounted units show rider speed and mass; entity size is not modelled; 48 artillery units have no missile weapon; 142 lose explosion damage; 490 lose melee contact effects.
- **Raw keys and placeholder text shown to readers.** Weapon keys, agent types, item types, campaign keys, a `%PLACEHOLDER%` culture, 638 building chains named "placeholder", doubled attribute titles, float artefacts, `-1` sentinels. The web game-text renderer prints about 3,900 unknown tags as raw keys and styles only 7 of the 44 colours in use.
- **Same-named records with nothing to tell them apart.** No campaign dimension; faction variants, unit variants, building chains and technology trees share names.
- **Rosters and recruitment.** 692 of 717 factions list no units; Regiments of Renown and mercenaries have no source; 310 units have no availability at all.
- **Characters and items.** 814 lord and hero unit variants are not linked to a character. Missing: XP and skill points, item eligibility and slots, and which abilities skills and items grant.
- **Effects.** Scopes, conditions and bonus-value meaning are unresolved; polarity and priority are unused.
- **Presentation rules already in the DB.** Stat order, bullet points, colours, unit groups, tree groups and link positions sit in `ui_*` and `technology_*` tables we extract but don't model.
- **Scripts.** Lua campaign scripts hold the XP formula, legendary hero unlocks, followers, item drops and Regiments of Renown per subculture.

## Decisions

- **Roadmap plus per-area specs.** This document fixes the areas, their order, their contents and the conventions they share. Each area gets its own detailed design, plan and pull request.
- **Campaigns: tag everything, default to Immortal Empires.** Every restriction carries its campaign(s). The wiki shows Immortal Empires by default and marks Realm of Chaos- or Prologue-only content. The planners filter by the chosen campaign.
- **Web app changes ship in the same pull request.** Each area bumps `MODEL_VERSION`, updates schemas and the pages that read changed fields, and deploys a working site. Misleading fields are replaced, not kept beside their fixes.
- **Two sources beyond DB tables:** parsed Lua campaign scripts, and small hand-curated files in the repository (a bonus-value dictionary and mechanics notes), both validated against the DB.

## Order and versioning

| Order | Area | Model version | Why here |
|---|---|---|---|
| 1 | A. Foundations and text | 3 | Every later area uses its campaign entity, campaign tags, text rules and effect presentation fields; it also fixes most raw keys and placeholder text. |
| 2 | B. Units and battle data | 4 | Fixes the wrong numbers on unit pages and sets the rider/mount/engine shape later areas build on. |
| 3 | C. Rosters, recruitment and factions | 5 | Fixes the empty faction rosters; foundation of the army planner. |
| 4 | D. Characters, items and progression | 6 | The character planner's inputs and the first Lua script data. |
| 5 | E. Effect semantics | 7 | Makes effects computable. May move ahead of D if the stat engine starts first. |
| 6 | F. Buildings and technology | 8 | Upgrade graph and tree presentation data; least urgent. |

Rules for every area:

- **One unit of work.** Each area is one spec, one plan, one pull request and one `MODEL_VERSION` bump. The same pull request updates `twwiki/model/schemas.py`, the web app's `MODEL_VERSION`, the generated types and the pages that read changed fields.
- **Baselines.** Each pull request updates the link report, `tests/model/missing_links_baseline.json`, `tests/model/missing_images_baseline.json` and the real-build tests deliberately. Any coverage drop is explained in the pull request description.
- **In-game checks first.** Each area spec opens with the in-game checks its open questions need. Anything that cannot be confirmed is modelled as a labelled assumption.

### Out of scope for this roadmap

- The stat engine, the character planner and the army planner themselves.
- Decoding `startpos.esf` (starting armies and characters).
- Non-English localisation.
- Battle scripts (`script/battle/`) and quest battles.
- Changes to the Firebase publish contract beyond the model version.
- Pooled resources and rituals. These are noted as a future area G.

## Shared conventions

### Campaign tags

- **Campaign entity.** Area A adds a `campaign` entity with key, name, map, script folder and playable faction count. Source: the `campaigns` table (`wh3_main_combi`, `wh3_main_chaos`, `wh3_main_prologue`) and `start_pos_factions`.
- **Tag shape.** Anything with campaign restrictions gets `campaigns: list[Link]`, where **an empty list means every campaign**. Areas A–F apply the tag to:
  - factions
  - units: custom-battle `campaign_exclusive` and campaign rosters
  - skill nodes
  - technology nodes
  - chain availability
  - building effects with campaign conditions
  - recruitment sources
  - agent subtypes

### References

- **Modelled entities.** A reference to a modelled entity is a `Link`. Fields that are bare keys today become links: `unit.mount`, `building_level.cultures`, `Activation.spawned_unit` and others named in each area.
- **Unmodelled records.** A reference to a record with no page is embedded as a small typed object with its resolved name. Examples: an explosion, a vortex, a scope, a battle context.
- **Raw keys** appear only in `key` fields.

### Text

The model build does the following:

- splits `Title||Body` text into title and body;
- turns placeholder text into `null` and counts it: the literal "placeholder" (any case), `%PLACEHOLDER%`, and empty strings;
- rounds float32 values to the shortest representation that round-trips at 6 significant digits (`0.90000004` becomes `0.9`);
- resolves `{{tt:}}` and `{{Cco…:}}` tokens where a loc target exists, and otherwise drops the token and counts it.

Game markup (`[[col:]]`, `[[img:]]`, `[[sl:]]`, `[[url:]]`, `[[tooltip:]]`, …) passes through to the web renderer, which handles every tag from area A on.

### Values and display

- **Values.** The model keeps the game's own values, including `-1` and `0` sentinels, so the stat engine sees exactly what the game does.
- **Display rules.** A single web formatter applies the game's rules:
  - A negative range shows ∞; a zero range hides the row.
  - A negative uses count hides the row.
  - A duration of zero or less shows ∞.
  - A zero cooldown, zero miscast chance or zero wind cost hides the row.

### Reference data

Non-entity documents go in `model/<build_id>/reference/<name>.json`, each with a Pydantic schema and a manifest entry. The planned documents, by the area that adds them:

- **A:** `campaigns`, `colours`, `ui_labels`
- **B:** `unit_stat_layout`, `unit_groups`, `constants`, `scaling`
- **D:** `progression`, `script_data`
- **E:** `effect_scopes`, `bonus_values`

### Curated data

- **Location.** `curated/` at the repository root holds hand-maintained YAML files. Each records the build id it was checked against.
- **Planned files.** `curated/bonus_values.yaml` and `curated/mechanics.yaml` (area E).
- **Validation.** Tests fail if a curated key no longer exists in the DB. The manifest counts DB ids that the curated files don't cover.

### Lua scripts

- **Extraction.** A new optional extraction step raw-copies a configured list of campaign Lua files from `data_script.pack` into `raw/<build_id>/script/`. `data_script.pack` joins the build id when scripts are configured.
- **Area D decides** whether parsing uses a static Lua-table reader or a sandboxed interpreter, and which files are read.

### Gaps and tests

- **Manifest counts.** Every new resolution counts what it could not resolve in the manifest: missing, placeholder, unresolved token, unknown condition.
- **Real-build tests.** Each area pins known examples:
  - Reiksguard horse run speed 7.8 and mass 1,000 (B)
  - Reikland's campaign roster (C)
  - Karl Franz's Deathclaw unit variant (D)
  - `general_to_force_own` scope target (E)
  - the Empire barracks upgrade graph (F)

## Area contents

Counts are from build `1eb25ce70f3a` and are given so each area spec can check its own coverage.

### A. Foundations and text (model version 3)

- **Campaign entity and tags.**
  - **Factions:** per-campaign playable and major flags, from `start_pos_factions` (812 rows).
  - **Technology nodes:** `technology_nodes.campaign_key` (30 nodes).
  - **Agent subtypes:** `campaign_to_agent_subtypes` (181 rows).
  - **Custom-battle permissions:** `units_custom_battle_permissions.campaign_exclusive` (228 rows).
  - **Regions, skill nodes and chain availability** already carry a campaign; the tag becomes Links.
- **Text cleanup.**
  - Attribute title and body split (2,606 unit lines).
  - Placeholder filtering (638 chain names; the `*` culture).
  - Float rounding (150+ values).
  - `{{tt:}}` (498 occurrences) and Cco token resolution.
  - The 19 unresolved `{{tr:}}` targets.
- **Raw keys to labels.**
  - Weapon display names, derived from the owning unit where no loc text exists.
  - Labels for `agent_types`, item type and category (`ancillaries_categories` loc), and culture/subculture/faction names on building levels (`building_level.cultures` becomes links).
  - Names for technology trees that have none.
- **Effect presentation fields on every application:**
  - Scope suffix text (`campaign_effect_scopes_localised_text_*`, 322 non-empty).
  - `priority`, where 0 means hidden (1,339 effects).
  - `is_positive_value_good` and the negative icon.
- **Reference data.**
  - `campaigns`.
  - `colours`: `ui_colours` (163) and `ui_colour_profile_colour_overrides`, plus a documented lightening rule for colours too dark on the wiki background.
  - `ui_labels`: the used subset of `uied_component_texts_localised_string_*`.
- **Web.**
  - The game-text renderer handles every tag and all 44 colours used in loc text.
  - The shared sentinel formatter.
  - Polarity colour and icon on effects, with priority-0 effects hidden.
  - Secondary lines that tell same-named records apart:
    - units: category and special marker;
    - characters: subtype;
    - building levels: chain;
    - items: rarity and category;
    - factions and technology trees: culture and campaign.

### B. Units and battle data (model version 4)

- **Unit entities.**
  - `rider`, `mount`, `engine` and `articulated` blocks. Each has speed (walk, run, charge, fly), mass, HP, size and count.
  - Sources: `battle_entities` via `land_units.man_entity`, `mounts.entity` (382 mounts), `battlefield_engines.battle_entity` (148 engines; 281 units), `land_unit_articulated_vehicles` (56; 186 land units), `land_units_to_extra_engines` (7).
  - `base_stats` no longer presents rider values as unit values.
- **Weapons.**
  - The missile weapon comes from the land unit or its engine (`battlefield_engines.missile_weapon`; 48 units).
  - Alternate weapons come from `unit_missile_weapon_junctions` (331 rows, 157 units), with the bonus rows that switch them in.
  - `missile_weapons_to_projectiles` (13).
- **Projectiles and melee.**
  - Embedded explosion records: `projectiles_explosions` (412; 142 units).
  - Projectile contact, overhead and vortex effects (171 units).
  - Melee `contact_phase` (490 units).
  - The dropped projectile and melee fields named in the model audit (§U3, §U4).
  - `battle_entity_stats` (98).
- **Unit identity.**
  - Bullet points: `ui_unit_bullet_point_enums` (223) and `ui_unit_bullet_point_unit_overrides` (7,485), with state, sort order, name and tooltip.
  - Lore text: `land_units` historical description, 1,064 loc entries.
  - `create_time`, `is_renown` (257), `can_siege`, `is_high_threat`, `is_monstrous`.
  - Special category (renown, crafted, Elector Count, …) and UI unit grouping: `ui_unit_groupings`, `ui_unit_group_parents`.
  - DLC: `main_unit_ownership_content_pack_junctions` (2,677).
  - Unit sets as links.
- **Stat presentation.**
  - `unit_stat_layout` from `ui_unit_stat_to_classes` (172), `ui_unit_stats` (50) and `ui_unit_stat_to_unit_castes` (23).
  - Resistances and ward save named plainly (`damage_mod_all` is ward save).
- **Abilities.**
  - Embedded records: `battle_vortexs` (288; 342 abilities), `projectile_bombardments` (126; 152), activated projectiles (110), miscast explosions (216).
  - Spawned units as links (170).
  - Overcast version: `overpower_option`, 202.
  - Lore: `special_ability_groups_to_unit_abilities_junctions` (1,360), with the lore's `sort_order` and `colour_hex`.
  - Tooltip lines: `unit_abilities_to_additional_ui_effects_juncs` (2,993).
  - Superseded abilities (90) and phase names (567).
  - The dropped phase and activation fields (model audit §A3).
  - Army abilities: `army_special_abilities` (254).
- **Constants and scaling.**
  - `constants`: selected rows from `_kv_rules` (274), `_kv_morale` (130), `_kv_fatigue` (29), `_kv_winds_of_magic_params` (16) and `_kv_unit_ability_scaling_rules` (8).
  - `scaling`: `unit_stat_to_size_scaling_values` (24), `unit_size_global_scalings` (12), `unit_experience_bonuses` (5), `unit_fatigue_effects` (21) and `ground_type_to_stat_effects` (29).
  - The link report starts covering `_`-prefixed tables.
- **In-game checks first:** how rider, mount, engine and articulated HP combine into displayed HP; and whether "large" follows the mount or the rider.

### C. Rosters, recruitment and factions (model version 5)

- **Campaign roster per faction.**
  - `factions.military_group` → `units_to_groupings_military_permissions` (4,348), minus `units_to_exclusive_faction_permissions` (1,439), tagged by campaign.
  - Custom-battle availability becomes a separate field.
- **Recruitment sources per unit.** Each entry has a type and conditions:
  - buildings, with starting XP (`building_units_allowed`);
  - mercenary pools: `mercenary_pools` (63), `mercenary_pool_to_groups_junctions` (884), `mercenary_unit_groups` (649), `faction_to_mercenary_set_junctions` (194), `province_to_mercenary_set_junctions` (1,032);
  - Regiments of Renown, with the lord-level gate (`campaign_mercenary_unit_character_level_restrictions`, 268) and the Lua list of Regiments of Renown per subculture;
  - allied recruitment: `allied_recruitment_unit_permissions` (753), `allied_recruitment_core_units` (378), `building_allied_units` (1,093);
  - special sources, with `max_per_army` (`recruitment_sources`, 24);
  - garrisons per building level: `building_level_armed_citizenry_junctions` (3,301) and `armed_citizenry_units_to_unit_groups_junctions` (4,825).
- **Costs and caps.**
  - Cost overrides: `main_unit_faction_overrides` (112), `main_unit_resource_costs_junctions` (53), `unit_recruitment_source_overrides` (28).
  - Multiplayer caps: `unit_set_to_mp_unit_caps` (923).
  - Unit upgrades: `unit_purchasable_effect_sets` (2,017), `unit_upgrade_to_unit_groups` (151) and their requirements.
  - A reverse index of which effects raise a unit's cap.
  - The recruited-unit HP scripted bonuses (33).
- **Faction starts, per campaign.**
  - Playable and major flags, and capital.
  - Starting regions: the reverse of `region.starting_owner`.
  - Leader: `frontend_faction_leaders`, 131.
  - Start description: `start_pos_factions.long_description`, plus attack and defend loc (717 each).
  - DLC: `faction_ownership_content_pack_junctions` (380).
- **In-game and data checks first:** the source of the 20-unit army limit; whether other cap tables exist; the 124 units with no known source; and whether `building_units_allowed.enabled` (false on all 6,396 rows) is a decode issue.

### D. Characters, items and progression (model version 6)

- **Skills.**
  - Item and mount grants: `character_skill_level_to_ancillaries_junctions` (738) and `character_skill_node_ancillary_locks` (6).
  - Each character's unit variants: via skill, via item, and via custom-battle mounts (`units_custom_battle_mounts`, 681). Units link back to their character.
  - Automatic upgrades: `character_skills_to_level_reached_criterias` (888).
  - Tree row categories: `character_skill_categories` (42).
  - Rank variants with their faction, subculture and campaign restrictions (16 rows; 14 skills currently have no rank).
- **Progression.**
  - `progression` reference: XP threshold and skill points per rank, per agent type and campaign (`character_experience_skill_tiers`, 352).
  - The Lua XP formula (`wh_campaign_experience_triggers.lua`) as script data.
- **Characters.**
  - Legendary-lord flag.
  - Innate effect bundles: `faction_starting_general_effects`, 106.
  - Starting factions and available campaigns.
  - Unique agents: `unique_agents`, 52.
  - DLC: `agent_subtype_ownership_content_pack_junctions`, 283.
  - For the 48 characters with no agent type, fall back to the skill node set's `agent_key`.
- **Items.**
  - Eligibility, resolved from `ancillaries.faction_set` and `faction_set_items` (1,107) into culture, subculture and faction lists.
  - Slot limits: `ancillaries_categories_faction_junctions`, 75.
  - Slot order: `ancillaries_categories.sort_order`.
  - Rarity.
  - Item sets as an entity: `ancillary_sets` (85), `ancillary_set_ancillary_junctions` (204), `ancillary_set_effect_junctions` (184).
  - The armory as an entity: `armory_items` (362), `armory_items_to_effects` (1,498), `armory_item_sets` (115), `armory_item_set_items` (1,282), `agent_subtypes_to_armory_item_sets` (85).
  - Items granted by technologies: `technology_nodes_to_ancillaries_junctions`, 25.
  - How each item is obtained, from Lua: follower trigger and chance (370 followers), magic item drops, rare items (14) and fusing.
- **Granted abilities.** Derived from effect `enable` bonuses (2,106 rows; 1,517 abilities): `granted_by` on abilities, and `grants_abilities` on skills, items and traits.
- **Other Lua script data.** 21 legendary heroes (unlock rank, AI unlock turn, cultures, items), hero upgrade and greater-daemon paths, and trait exclusions.
- **Traits.**
  - Technology-granted traits: `technology_character_traits_junctions`, 12.
  - Bretonnian vows: `bretonnia_vows_to_traits` (39) and `agent_subtype_to_vows` (39).
  - `remove_on_skill_reset`.
- **Checks first:**
  - In game: whether a skill level's effects replace or stack on the previous level, and whether node `indent` or `tier` is the skill tree row.
  - Decide the Lua parsing approach.

### E. Effect semantics (model version 7)

- **Resolved scopes.** An `effect_scopes` reference from `campaign_effect_scopes` (435 rows: source, target, location, ownership, territory) plus suffix text and `campaign_effect_scope_agent_junctions` (50). Every application links to its scope.
- **Conditions.** Resolved into a `conditions` object on each application:
  - Battle contexts: `effect_bonus_value_battle_context_junctions` (440) and `campaign_bonus_value_battle_context_specifiers` (92), plus the culture, faction, battle type, ground type, force status and territory context tables.
  - Building context expressions: `building_effect_context_expressions` (373; 4,596 building applications), with display text.
  - A campaign condition (`IsChaosCampaign`, 757 rows) feeds the campaign tags.
- **Bonus-value dictionary.**
  - `curated/bonus_values.yaml` covers the 369 bonus-value ids: stat, operation (flat, percentage, multiplier, enable), unit and notes. It is merged into the `bonus_values` reference.
  - The dictionary is needed because 51 of the 53 id enum tables are absent from the build.
- **Effect sources.**
  - Each source entry carries its own value and scope.
  - Missing application tables are read: `campaign_effect_list_effect_junctions` (414), `technology_initiative_effects` (217), armory, item-set and action-result effects.
  - Scripted bonus values (`scripted_bonus_value_ids`, 303) link to the scripts that read them.
- **Unit-set index.** Each unit set lists its member units, so an effect can list the units it affects.
- **Bonus targets.** The 7,378 raw-key targets are resolved where a table exists: army abilities, ability groups, building sets, alternate missile weapons, unit upgrades, siege items, agents, agent actions.
- **Curated mechanics notes.** `curated/mechanics.yaml` records combat order (ward save first, then resistances, then armour on non-armour-piercing damage), each step citing `constants` keys and the build.

### F. Buildings and technology (model version 8)

- **Buildings.**
  - An upgrade and downgrade graph replaces the flat level list: `building_upgrades_junction` (3,330; 135 branching levels) and `building_downgrade_junctions` (1,493).
  - Level requirements: `building_level_required_buildings` (8).
  - Slot unlocks per settlement level: `campaign_building_chain_slot_unlocks` (349).
  - Settlement types: `settlement_type_to_building_chains_junctions` (3,508).
  - Building sets as an entity, with names, members and colour: `building_sets` (280) and `building_set_to_building_junctions` (2,606).
  - Encyclopedia text (1,943) and flavour text (548).
- **Technology.**
  - Script-lock reasons: `technology_script_lock_reasons`, 88.
  - Grants: items, traits and initiatives.
  - Unit upgrade requirements: `unit_upgrade_to_tech_requirements`, 140.
  - Tree tabs: `technology_ui_tabs`, 26 rows (sort order, tier offset); `technology_ui_tabs_to_technology_nodes_junctions`, 851.
  - UI groups: `technology_ui_groups` (128) and their corner-node junctions (120).
  - Link positions and offsets for elbow-shaped links (`technology_node_links`).
  - Required-parent counts for "N/M parents" badges.
  - The node faction restriction (`technology_nodes.faction_key`, 315 nodes). Area A adds only the campaign restriction.

### Future area G (not scheduled)

Pooled resources (`pooled_resources`, 246), rituals (1,326), initiatives (619), and campaign group pooled-resource effects.

## Testing strategy (every area)

- **Unit tests.** Every new resolver gets unit tests using the existing fixture pattern (`tests/model/fixtures.py`).
- **Real-build tests.** Each area pins its examples from "Gaps and tests" and asserts its manifest counts against the baseline.
- **Web tests.**
  - Web unit tests cover the new formatters and renderers.
  - The web fixture model (`web/test/fixtures/model`) is regenerated with `npm run fixtures`.
  - End-to-end tests are extended for pages whose structure changes.
- **Curated data** is validated against the DB in tests.
- **Deploy check.** After each area merges, the model is rebuilt and published and the Deploy workflow runs. The live site is spot-checked on the area's examples.

## Open questions carried into area specs

1. How rider, mount, engine and articulated HP combine into displayed unit HP (B).
2. Whether "large" is decided by the mount entity's size, the rider's, or the larger of the two (B).
3. Where the 20-unit army limit comes from; whether other cap tables exist (C).
4. What the 124 units with no known source are, and whether the `building_units_allowed.enabled` column is decoded correctly (C).
5. Whether skill level effects replace or stack on the previous level (D).
6. Whether node `indent` or `tier` is the skill tree row (D; the game's `metadata.json` and the skill panel disagree).
7. Whether the Lua parsing approach should be a static table reader or a sandboxed interpreter (D).
8. Who maintains `curated/bonus_values.yaml` each patch, and how uncovered ids are shown on the wiki (E).
9. Whether the ~2,200 effects with no source are applied by Lua or unused, and how the wiki should mark them (E).
