# Audit: documentation shipped in Total War: WARHAMMER III game files

Build examined: `text/build_info` reads `Warhammer3 / Patch_8_1`, build `4194776`, dated `12/07/2026`.
Source: rpfm_server 5.0.6 dependency cache (685,765 files), session with `select_game("warhammer_3")`.
Extracted (read-only) to `scratchpad/game-docs/`; HTML turned into plain text under `scratchpad/doctxt/` for reading.

## Summary

- **The docs folder exists and is `documentation/` in `data.pack`**: 141 files, 23.0 MB. It holds three things: generated **Lua scripting API reference** (`documentation/script/`, 112 HTML pages for battle, campaign and frontend), the **UI "context object" (Cco) reference** (`documentation/ui/documentation.html`, 1.9 MB, plus `callback_documentation.html`), and three short **pack modding notes** (`documentation/pack/*.txt`). There is no modding guide, no changelog and no mechanics manual.
- **It contains no formulas for combat or stats.** Across the main pages there are no hits for `leadership`, `effect_bonus_value` or `general_to_force`. `armour` appears only in UI getter names such as `ArmourPiercingPercentage`. Nothing covers damage, armour mitigation, ward save, charge, or how bonuses stack. The research-guide expectation that mechanics are "not in DB tables" also holds for the docs: **they are not in the docs either.**
- **The docs are an API index.** What is useful: (a) `BONUS_VALUES_SCRIPT_INTERFACE` lists 39 bonus-value families, which line up with the DB's `effect_bonus_value_*_junctions` tables; (b) the `CcoUnitStat` and `CcoUnitDetails` UI API confirms the engine keeps **base versus modified** stats, an `IsPercentage` flag per stat, and clamped display values. That is a useful spec for the stat engine's output shape, but it gives no maths.
- **The Lua scripts are the valuable find.** They sit in `data_script.pack` under `script/`, not in `documentation/`. Several campaign scripts are plain **data tables that matter to the character planner**: legendary-hero unlocks (21 entries, e.g. Kroak at rank 15), followers gained by event and chance (370 entries), rare-item weights (14), the post-battle item-drop formula, the **character XP formula** (`wh_campaign_experience_triggers.lua`), hero upgrade paths, Regiments of Renown per subculture (23), recruited-unit starting HP (33 scripted bonus values), and trait exclusions.
- **`scripted_bonus_value_ids` (303 rows in the DB) only means something through Lua.** 142 of the 147 literal ids used in scripts are in the DB. The scripts show how the values are read: summed across the character, faction and force scopes, and used as percentage points (`1 + v/100`) or as a `random_percent(v)` chance.
- **Verdict:** as a mechanics source the HTML docs are **low value** (the one exception is a medium-value glossary of bonus-value families and stat-object semantics). **`script/campaign/*.lua` is medium to high value** for the character planner and for explaining scripted effects in the wiki. Extract the Lua as raw text and parse a handful of tables into JSON. Don't publish the HTML docs.

## Inventory

| Folder | Files | Size | Types | Pack | What it is |
|---|---|---|---|---|---|
| `documentation/` (root) | 1 | <1 KB | txt | data.pack | `readme.txt`: says the folder is modder docs kept unpacked by CA |
| `documentation/pack/` | 3 | 4 KB | txt | data.pack | Pack compression flags; DB validation log setting; `twad_key_deletes` table for deleting records |
| `documentation/script/` (root) | 7 | ~1.6 MB | html, js, css | data.pack | `index.html` (main index), `scripting_doc.html` (769 KB: events and game interfaces), `scripted_events.html`, `ui_scripting.html`, `search.js` / `searchdata.js` |
| `documentation/script/campaign/` | 43 | 6.23 MB | 42 html | data.pack | Campaign manager (1.0 MB), episodic scripting (980 KB), campaign UI manager, model hierarchy, narrative system, invasion / mission / random-army managers, custom starts |
| `documentation/script/battle/` | 50 | 3.87 MB | 49 html | data.pack | Battle manager, generated battle, script_unit, unit / unitcontroller / army wrappers, cutscenes |
| `documentation/script/frontend/` | 18 | 1.60 MB | 17 html | data.pack | Frontend pages; mostly copies of the shared core, lua and uicomponent pages |
| `documentation/script/images/` | 14 | 1.08 MB | 11 png, 2 pdn, 1 jpg | data.pack | Diagrams (model hierarchy, narrative chains, load order) |
| `documentation/ui/` | 5 | 8.73 MB | 2 html, odt, exe, css | data.pack | `documentation.html` (1.87 MB, "UI Symbols Documentation", 515 Cco classes, 218 of them `...Record` DB wrappers), `callback_documentation.html` (UI callbacks), `context_viewer_doc.odt`, `parse_code_into_structs.exe` (6.75 MB, **not extracted for use, not run**) |
| **Documentation total** | **141** | **23.0 MB** | | data.pack | |
| `script/_lib/` | 45 | 3.83 MB | lua | data_script.pack | Script library the HTML docs are generated from (`lib_campaign_manager.lua` 804 KB, etc.) |
| `script/campaign/` | 986 | 14.9 MB | 373 lua, plus cutscene and camera assets | data_script.pack | Campaign feature scripts; `main_warhammer/` (IE), `wh3_main_chaos/` (RoC), `wh3_main_prologue/` |
| `script/battle/` (not extracted) | ~4,690 | n/a | lua, txt, kfp | data_script.pack | Quest, survival and scenario battle scripts (3,531 quest-battle files) |
| `script/` root | 12 | ~70 KB | lua, xml, txt | data_script.pack | `events.lua` (event table exported from DaVE), `docgen.lua`, `autorun.lua`, loaders |
| `script/patch_note_helper/` | 2 | 1 KB | json, bat | data_script.pack | Manifest listing the 37 tables CA diffs for balance patch notes |
| `script_data/external_json_files/campaign/` | 46 | 50 KB | json | data.pack | Nurgle plague UI layout, Malakai mission reward definitions, one Empire battle-reward rule |
| Other text found | | | | | `text/encyclopedia.xml` (empty `<encyclopediaUrls/>`), `text/build_info` (version), `manifest.txt` (loose-file manifest), `local_en.pack` `text/db/encyclopedia_*__coc_.loc` |

## Contents

### 1. Scripting API reference (`documentation/script/`)
Generated by `script/docgen.lua` from `--- @function` / `--- @desc` comments in `script/_lib/*.lua`, plus a dump of engine interfaces.
- **`index.html`**: an introduction. Scripts run in Lua 5.1 in three environments (frontend, campaign, battle).
- **`scripting_doc.html`**: lists roughly 600 campaign **events** (e.g. `CharacterSkillPointAllocated`, `CharacterRankUp`, `AncillariesFused`, `CharacterPreBattleChallenge`) and about 280 **script interfaces** (`CHARACTER_SCRIPT_INTERFACE`, `MILITARY_FORCE_SCRIPT_INTERFACE`, `EFFECT_SCRIPT_INTERFACE`...) with signatures.
  - `EFFECT_SCRIPT_INTERFACE` is described as "An effect that provides bonus values via a scope". Its members are `key`, `scope` and `value`; there are no semantics beyond that.
  - `BONUS_VALUES_SCRIPT_INTERFACE` has 39 getters, e.g. `agent_value(record_key, bonus_value_id)`, `unit_attribute_value`, `special_ability_phase_value`, `pooled_resource_value`, `scripted_value`, `basic_value(bonus_value_id)`. These match the `effect_bonus_value_*_junctions` table families.
  - Custom effect bundles use `add_effect(effect_key, scope_key, value)`. Unit caps show up only as getters (`unit_cap` is "-1 if unlimited").
- **`campaign/campaign_manager.html`, `episodic_scripting.html`**: function reference (`cm:add_skill`, `cm:remove_skill_point`, `force_reset_skills`, `add_agent_experience`, `get_characters_bonus_value`...). Descriptions are one-liners. The only army-size fact is a helper that checks whether a force has "20 units in it".
- **`campaign/model_hierarchy.html`**: diagram and reference of the campaign model tree (world → faction → character → military force → unit).
- **`campaign/narrative_*.html`, `mission_manager`, `invasion_manager`, `random_army_manager`, `custom_starts`**: scripting frameworks for missions and narrative. Not relevant to stats or planners.
- **`battle/*.html`**: battle scripting wrappers. `unit:fatigue_state()` returns one of `threshold_fresh` … `threshold_exhausted`, and there are morale-state tests such as `morale_is_higher_than_wavering`. These are state names, not formulas.
- **Currency:** all 465 `@function` entries in the shipped `lib_campaign_manager.lua` appear in `campaign_manager.html`. The "defined in … line N" references are slightly off, though: `add_skill` is documented at line 7793 but sits at line 7803 today. So the docs were generated from a near-identical, slightly older library revision. No patch or version string appears in any HTML page. No DLC keys appear (`dlc25`, `dlc26` and `dlc27` get 0 hits), which is expected for a generic API.

### 2. UI context reference (`documentation/ui/documentation.html`)
"UI Symbols Documentation" lists 515 `Cco*` context classes (Battle, Campaign, Common, Record) with function name, return type and a one-line description, plus global expression functions.
- `CcoUnitStat`: `ValueBase` ("value of stat with no mods/buffs/debuffs"), `Value`, `DisplayedValue` ("clamping it if necessary"), `MinValue`/`MaxValue`, `IsPercentage`, `ModifierIconList`, `PreBonusStatContext`.
- `CcoUnitDetails`: `StatList`, `BaseStatValueFromKey`, `StatContextFromKey`, `Mass`.
- `CcoBattleAbility`: intensity is what "modifiable stats of this ability will be multiplied by" (`DefaultIntensity`, `MaxIntensity`); also `ManaUsed`, `MiscastChance`, `RemainingUses` (-1 means unlimited).
- `CcoEffect`: `Value` ("raw value of the effect"), `EffectScopeContext`, `Priority` ("if 0 isn't shown in UI"), `IsPositive`. `CcoEffectBundle`: `TurnsRemaining` (0 means infinite).
- `CcoCampaignCharacterSkillLevelDetails`: `RankRequired`, `EffectList`, `AbilityList`, `UnitAttributeList`. `CcoCampaignCharacter` has `SkillPointsAvailable` and `Upkeep` (for a general this covers the whole army).
- Faction: `UnitCapForUnit`, `UnitCapForAgent` ("unit cap modifier"); `CcoMainUnitRecord.UnitSetUnitCapList`; `AutoresolvePredictionInaccuracyPercent`.
- `CcoCampaignEffectScopeRecord` exposes only `Key`, `LocalisedText` and `RecordList`, so it gives **no scope semantics**. Those semantics already live in the DB (see below).
- `callback_documentation.html` lists UI callback components by area (Battle / Campaign / Frontend). Not relevant.

### 3. Pack notes (`documentation/pack/`)
Short modder notes: ZSTD/LZ4 compression flags in `rules.bob`; turning on `db_validation.log.txt` with `vfs_log_level 1`; the `twad_key_deletes` table for deleting DB records in a mod. Relevant to the pipeline only as a caution: a modded or merged dataset can delete vanilla rows through `twad_key_deletes`.

### 4. Lua campaign scripts (`script/campaign/`, `data_script.pack`)
Not documentation, but this is where scripted mechanics live. Tables worth keeping:
- **`wh_campaign_experience_triggers.lua`**: the character XP formula as data plus code. Constants include `xp_per_gold_value_killed_exponent = 0.88`, `battle_xp_base = 300`, `battle_xp_max = 10000`, and hero and secondary-general multipliers of 0.75 and 0.5. Hero-action XP ranges from 200 to 1600. The battle formula is `min(base*killed% + (enemy_value*killed%)^0.88, max)`, then modifiers. Bonus values give `mod = 1 + experience_mod/100`, plus per-group mods such as `experience_mod_chs_khorne`.
- **`wh3_main_legendary_characters.lua`**: `character_unlocking.character_data`, 21 legendary heroes. Each entry has `unlock_rank` (e.g. 15), `ai_unlock_turn`, `subtype`, `allowed_cultures`, per-faction `starting_mission_keys` and bundled `ancillaries`.
- **`wh3_campaign_followers.lua`**: 370 follower entries of `{follower, event, condition(fn), chance}`, e.g. 25% chance on `CharacterLootedSettlement`. The conditions are Lua functions, so this needs light parsing (keep the event and chance; summarise the condition text).
- **`wh3_campaign_magic_items.lua`**: post-battle item drop. Base `chance = 10`, plus the summed `post_battle_ancillary_drop_chance_mod` (character + faction + force), plus 10 for a faction leader, plus a difficulty modifier (−3 … +6). Items are pooled by category (armour, enchanted_item, general, talisman, weapon) and rarity.
- **`wh3_campaign_rare_items.lua`**: `chance_per_battle_to_gain_rare_item = 3`, then 14 items with weights and culture requirements or restrictions.
- **`wh3_campaign_item_fusing.lua`**: fusing pairs (scrap + scrap → upgraded; upgraded + upgraded → a random unique); `base_chance_to_fuse_unique_item = 10`.
- **`wh3_campaign_character_upgrading.lua`**: initiative → new agent type and subtype (e.g. an Exalted Hero devoted to Khorne), `default_xp_proportion = 0.5`.
- **`wh3_campaign_greater_daemons.lua`**: herald subtype → exalted greater daemon, with dilemma and incident.
- **`wh_campaign_ror_recruitment.lua`**: `regiments_of_renown` per subculture (23 subcultures).
- **`wh3_campaign_recruited_unit_health.lua`**: unit → `recruit_hp_*` scripted bonus value (33; all 33 ids exist in the DB).
- **`wh2_campaign_traits.lua`**: trait exclusions by culture and subculture.
- **`wh3_campaign_bonus_values.lua`**: 96 listeners that implement scripted bonus values, e.g. `random_unit_killed_per_turn_chance` used as `random_percent(value)`.
- **`wh3_campaign_character_initiative_unlocks.lua`**: which event and condition grants each character initiative (e.g. Ogre "big names").
- **Campaign naming:** the scripts compare `cm:get_campaign_name() == "main_warhammer"` and `campaign_name_key() == "wh3_main_combi"`. The DB `campaigns` table already maps `wh3_main_combi` → `script/campaign/main_warhammer`, `wh3_main_chaos`, and `wh3_main_prologue`.

### 5. `script_data/external_json_files/campaign/` (data.pack)
Small JSON records exported from CA's tools: Nurgle plague tree layout (component links and x/y), seven Malakai mission definitions (`ActivatingRitual`, `Ancillary` reward, `EffectBundle`, highlighted units), and one battle-reward rule (`DamageDealtAsGoldValuePerResource: 20.0` for Nuln research). Niche.

## Usefulness assessment

| Item | Rating | Project need filled | Evidence |
|---|---|---|---|
| Combat/stat formulas in any doc | **Low (absent)** | Stat engine | 0 hits for leadership, ward save formulas, armour mitigation, stacking rules in docs or `_lib` |
| `BONUS_VALUES_SCRIPT_INTERFACE` family list | Medium | Stat engine: confirms which record types bonus values are keyed by; a checklist for `effect_bonus_value_*` junction coverage | 39 getters; DB has 58 `effect_bonus_value_*` tables |
| `CcoUnitStat` / `CcoUnitDetails` API | Medium | Stat engine output contract (base, modified, displayed-clamped, min/max, is_percentage, modifier list) | `ValueBase`, `DisplayedValue`, `IsPercentage` descriptions |
| Ability intensity semantics (`CcoBattleAbility`) | Medium | Ability pages: intensity multiplies modifiable stats | `DefaultIntensity` / `MaxIntensity` descriptions |
| Effect scope semantics | Low from docs / **already in DB** | Scope glossary | Docs: key and loc only. DB `campaign_effect_scopes` has `source/target/location/ownership/territory`, e.g. `general_to_force_own` = character → force, `forcewide_when_commanding`, `yours` |
| `campaign_variables` (DB, cross-checked) | High (already extracted) | Replenishment, bribes, loot, recruitment caps | e.g. `replenishment_base_land 8`, `replenishment_bonus_land_garrisoned_in_owned_province 12`, `recruitment_point_hard_cap 30`, `maximum_building_level 5` |
| `wh_campaign_experience_triggers.lua` | **High** | Character planner: XP to rank estimates; XP bonus effects | constants and formula above; 17 `experience_*` ids in `scripted_bonus_value_ids` |
| `wh3_main_legendary_characters.lua` | **High** | Character pages: how legendary heroes unlock, rank, starting items | 21 entries; `wh2_dlc12_lzd_lord_kroak` exists in `agent_subtypes` |
| `wh3_campaign_followers.lua` | High | Item pages: how each follower is obtained (event and % chance) | 370 entries |
| Magic, rare-item and fusing scripts | Medium–High | Item pages: drop chance, rare weights, fusing | base 10%, 3% rare, 10% unique fuse; helm of Draesca exists in `ancillaries` |
| Character upgrading / greater daemons | Medium | Character planner: hero transformation paths | initiative → subtype maps |
| RoR per subculture, recruited unit HP | Medium | Army planner: RoR availability; starting HP bonuses | 23 subcultures; 33 of 33 `recruit_hp_*` ids in DB |
| `wh3_campaign_bonus_values.lua` + `scripted_bonus_value_ids` | Medium–High | Wiki: explain the 328 effects wired to scripted bonus values (289 distinct effects); value semantics (chance %, additive across scopes) | 96 listeners; 142 of 147 literal script ids in DB; the other 161 DB ids are built dynamically or live in other scripts |
| Campaign key naming | Low (DB already has it) | Raw key cleanup | `campaigns.script_path` |
| Events list / `events.lua` | Low | Maybe planner trigger labels ("on rank up") | about 600 events |
| Narrative, mission, tour, cutscene docs and scripts | Low | none | frameworks only |
| `documentation/ui/callback_documentation.html`, frontend pages | Low | none | UI plumbing |
| `documentation/pack/*.txt` | Low | pipeline caution on `twad_key_deletes` | modding notes |
| `patch_note_helper` manifest | Low–Medium | A curated list of 37 balance-relevant tables to diff between builds | `Required_tables` list |
| `script_data` JSON | Low | Plague tree layout, Malakai missions | 46 small files |
| `parse_code_into_structs.exe` | Ignore | n/a | Executable; do not run |

## Recommendations

**Extract (pipeline)**
1. Add an optional `scripts` extraction step that raw-copies `script/campaign/*.lua` (top level only, about 187 files), `script/campaign/main_warhammer/*.lua`, `script/_lib/lib_campaign_manager.lua` and `script/events.lua` into `raw/<build>/script/`. Skip the cutscene, camera and replay assets and `script/battle/` (about 4.7k quest-battle files). Include `data_script.pack` in the build id.
2. Parse these tables into JSON with a small Lua-table reader. Run a real Lua 5.1 interpreter (e.g. `lupa`) in a sandbox with a stub `cm`/`core`, or regex the literal tables:
   - `experience_triggers.json`: constants and group → bonus-value maps.
   - `legendary_characters.json`: subtype, unlock_rank, ai_unlock_turn, cultures, ancillaries, mission keys.
   - `followers.json`: follower, event, chance, raw condition source text.
   - `item_drops.json`: base chances, rare items with weights, fusing pairs.
   - `hero_upgrades.json`: character_upgrading and greater_daemons maps.
   - `regiments_of_renown.json`, `recruited_unit_health.json`, `trait_exclusions.json`.
   - `scripted_bonus_value_usage.json`: id → the scripts and functions that read it, plus the scope getter used (character, faction, force, region, province).
   Load each into DuckDB as `script_*` tables and link them to existing keys (validate against `agent_subtypes`, `ancillaries`, `main_units`, `scripted_bonus_value_ids`).

**Curate (prose, hand-written from the docs and scripts)**
3. A "How effects work" wiki page that combines the DB `campaign_effect_scopes` columns (source/target/location/ownership) with the bonus-value family list from `BONUS_VALUES_SCRIPT_INTERFACE`. Add a note that scripted bonus values have no engine effect unless a script reads them.
4. A stat engine output contract modelled on `CcoUnitStat`: base, modified, displayed (clamped), min/max, is_percentage, contributing modifiers.
5. A character XP / rank page generated from `experience_triggers.json`.

**Model and wiki gaps this fills**
- Items (`twwiki/model/items.py`): how each item is obtained (follower triggers, drop chance, rare pool, fusing), and legendary-hero bundled items.
- Characters (`characters.py`): legendary-hero unlock rules, hero transformation paths, XP scripted modifiers.
- Effects (`effects.py`): flag effects whose bonus value is `scripted` (`effect_bonus_value_scripted_junctions`) and link each to the script that implements it.
- Units (`units.py`): RoR availability by subculture; recruited-unit starting HP modifiers.

**Ignore**
- All HTML docs as wiki content (API reference only; about 23 MB); `callback_documentation.html`; frontend and battle pages; images; `parse_code_into_structs.exe` and `.odt`; narrative, mission and tour frameworks; cutscene assets; `script/battle/**`; `text/encyclopedia.xml` (empty).
- Keep `documentation/script/scripting_doc.html` and `documentation/ui/documentation.html` locally as developer references while building the Lua parser. Don't publish them.

## Open questions

1. **Where do combat formulas live?** They are in neither the docs nor `_lib`. The stat engine will need community-sourced formulas (armour roll range, ward/physical resistance caps, charge-bonus decay), validated against `campaign_variables`, `battle_*` / `kv_*` tables (e.g. `_kv_rules`, `_kv_morale`, `_kv_fatigue` if present) and in-game tooltips. Next step: audit the `kv_*` tables in DuckDB.
2. How effects with the same bonus value **stack across scopes** in engine code (additive percentage versus multiplicative) is not stated anywhere. The scripts sum character + faction + force values for scripted ids, which suggests additive, but that is script behaviour, not engine behaviour.
3. 161 of the 303 `scripted_bonus_value_ids` are not referenced as literal strings in `script/campaign` or `_lib`. They may be built dynamically (e.g. `"corruption_" .. x`), read in `script/battle/`, or dead. A full `data_script.pack` scan is needed before labelling any as unused.
4. Should the pipeline run Lua (sandboxed `lupa`) or use a static table parser? Follower conditions are functions, and some tables are built at runtime.
5. The doc line references lag the shipped library by about 10 lines. Confirm whether `documentation/` is regenerated each patch or only occasionally. Future builds should not rely on it for version-accurate details.
6. How far should Realm of Chaos (`wh3_main_chaos`, 596 script files, mostly cutscenes) and prologue content be covered? Planner focus is presumably Immortal Empires (`wh3_main_combi` → `script/campaign/main_warhammer`).
