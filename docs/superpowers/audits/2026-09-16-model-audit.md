# Game data model audit: gaps for the wiki and planners

**Build audited:** `model/1eb25ce70f3a` (model_version 2), `twwiki.duckdb` (1,520 tables), branch `main` @ 21ef92c.
**Method:** I read the builders in `twwiki/model/*.py` and the Pydantic contract in `schemas.py`. I checked every claim below against `_tables`, `_columns`, the tables themselves, the built `entities/*.jsonl`, `manifest.json` and `link_report.json`. No tracked files were changed.
**Products:** W = wiki, SE = stat engine, CP = character planner, AP = army planner.

---

## Summary: the 10 most important findings, by impact

1. **Faction rosters are almost all empty (High; AP, W).** `faction.units` comes only from `units_custom_battle_permissions`, so **692 of 717 factions list no units**. Examples: Cult of Sigmar, the Huntmarshal's Expedition and the Shadow Legion. The campaign roster is `factions.military_group` → `units_to_groupings_military_permissions` (4,348 rows, 1,763 units, 104 groups), and the builders never read it. `units_to_exclusive_faction_permissions` (1,439 rows, 16 of them `allowed = false`) is also unread.
2. **Mounted units show the wrong speed, mass and size (High; W, SE).** `base_stats` takes speeds and mass from `land_units.man_entity`, which is the rider. `unit.mount` is a raw string, and `mounts.entity` → `battle_entities` is never followed. **1,041 of the 1,070 mounted units** show rider values. Reiksguard, for example, shows run 3.3 and mass 100, but its horse has run 7.8 and mass 1,000. Entity `size` (small/large/very_large) is not in the model at all, and 853 mounted units have a mount size that differs from the rider's. That size decides who counts as "large" for `bonus_v_large`. Engine and articulated-vehicle HP are ignored as well.
3. **Lord and hero mount variants are cut off from their characters (High; CP, W).** `character_skill_level_to_ancillaries_junctions` (738 rows) is unread; 716 of those rows are mount ancillaries, each with a `provided_bodyguard_unit`. **814 of the 1,304 lord/hero units have no link to a character**, and 709 of them are reachable only through that skill → ancillary → bodyguard-unit chain. `units_custom_battle_mounts` (681 rows) would also link them.
4. **Weapons and damage are incomplete (High; SE, W).** 48 artillery units have `missile_weapon: null` because their weapon sits on `battlefield_engines.missile_weapon`. 142 units whose projectile explodes lose all explosion damage, since only the `explosion_type` key is kept. 490 units lose the melee `contact_phase` (for example poison or burning on hit). 171 units lose projectile contact, overhead or vortex effects. 157 units have unread alternate weapons in `unit_missile_weapon_junctions`.
5. **Recruitment outside buildings is missing (High; AP, W).** 539 non-character units are recruited by no building. Among them are 256 of the 257 `is_renown` Regiments of Renown and the mercenary-pool units (`mercenary_unit_groups` 649, `mercenary_pool_to_groups_junctions` 884, `mercenary_pools` 63). Also unread: `recruitment_sources` (24, with `max_per_army`), `unit_recruitment_source_overrides` (28), the RoR lord-level gate `campaign_mercenary_unit_character_level_restrictions` (268), `main_unit_faction_overrides` (112) and `main_unit_resource_costs_junctions` (53). **310 units have no availability link of any kind** in the model.
6. **Effects can be listed but not computed (High; SE, CP, AP).** `EffectApplication.scope` is a bare string: 346 scopes are in use, and `campaign_effect_scopes` (435 rows of source/target/location/ownership/territory) is unread. What a bonus id means is engine-defined: 369 distinct ids, and 51 of the 53 referenced `campaign_bonus_value_ids_*` enum tables are absent from the build. Flat versus percent is encoded only in the id suffix and the loc template (`%+n%`). **7,378 of the 23,110 bonus targets** are raw keys. Among them, battle contexts (518 rows, e.g. "vs Tomb Kings") and building `context_requirement` (4,596 applications, 282 expressions, 757 rows `IsChaosCampaign`) are conditions the model does not interpret.
7. **Character progression inputs are missing (High; CP).** Unread: rank → XP and skill points (`character_experience_skill_tiers`, 352), automatic skill upgrades by level (`character_skills_to_level_reached_criterias`, 888), legendary lords' innate bundles (`faction_starting_general_effects`, 106), item slot limits (`ancillaries_categories_faction_junctions`, 75), item faction eligibility (`ancillaries.faction_set`: 2,077 items restricted across 63 sets), armory items (362 items, 1,498 effects), and ancillary sets (85 sets, 184 set effects).
8. **Abilities are reachable from their sources only through multi-hop joins, and key spell data is missing (Medium–High; CP, W, SE).** 1,517 abilities are switched on by effects (skills 866, items 624, bundles 186, traits 52). `character.abilities` includes only the associated unit's innate abilities, so **424 skill-enabled abilities have no character link**. Also unread: lore membership (`special_ability_groups_to_unit_abilities_junctions`, 1,360), army abilities (`army_special_abilities`, 254), overcast variants (`unit_abilities.overpower_option`, 202), and the damage records behind vortex (342), bombardment (152) and projectile (110) abilities, which are kept only as keys.
9. **Combat constants are not exported, and the link report cannot see them (Medium–High; SE, W).** `_kv_rules` (274 rows) holds the numbers the guide calls "hardcoded": `armour_roll_lower_cap` 0.5, `ward_save_max_value` 90, `melee_hit_chance_base/min/max` 35/8/90, `collision_damage_armour_penetration_ratio` 0.7, `charge_decay_duration` 13, and the missile AP coefficients. Scaling and progression tables `unit_stat_to_size_scaling_values` (24), `unit_experience_bonuses` (5) and `_kv_unit_ability_scaling_rules` (8) are also unexported. `link_report` skips every `_`-prefixed table.
10. **Campaign and faction context is flattened (Medium; AP, CP, W).** Factions have no playable flag, campaign membership or legendary lord. `start_pos_factions` has 812 rows: 104 playable in `wh3_main_combi`, 25 in `wh3_main_chaos`, 1 in `wh3_main_prologue`. `frontend_faction_leaders` (131) and `campaign_to_agent_subtypes` (181) are unread. Technology tree nodes drop `faction_key` (315 nodes) and `campaign_key` (30 nodes). `units_custom_battle_permissions.campaign_exclusive` (228 rows) is ignored, so campaign-only units show up as custom-battle units.

---

## Findings by area

### 1. Units

**U1. Campaign rosters use custom-battle permissions (High; AP, W)**
- *Model:* `units.py` builds `custom_battle_factions` from `units_custom_battle_permissions`. `build.py` REVERSE turns that into `faction.units`.
- *Gap:* Only 25 factions have custom-battle rows, so 692 of 717 factions show `units: []`. The campaign roster is `factions.military_group` (set on all 717 factions) → `groupings_military` (104) → `units_to_groupings_military_permissions` (4,348 rows, 1,763 distinct units). Examples: `wh_main_emp_empire` has 87 campaign units against 138 custom-battle units, and `wh3_main_emp_cult_of_sigmar` has 91 campaign units against 0. Per-faction exceptions live in `units_to_exclusive_faction_permissions` (1,439 rows). 159 units appear only in military permissions, and 265 units appear in neither table.
- *Needs:* AP, W.
- *Fix:* Add a campaign roster per faction (military group minus exclusions) as its own field, and keep custom-battle availability separate, filtered by `campaign_exclusive`.

**U2. Mount, engine and vehicle entities are not resolved (High; W, SE)**
- *Model:* `_base_stats` reads walk/run/charge/fly speed, mass and `hit_points` from `battle_entities[land_units.man_entity]`. `mount` is `land_units.mount` as a raw string.
- *Gap:*
  - Of 1,070 mounted main_units, 1,041 have a different run speed on the mount entity (`mounts.entity`, 382 mounts). Sample: `wh_main_emp_cav_reiksguard`, rider 3.3/100 against horse 7.8/1,000.
  - `battle_entities.size` is not modelled. 853 mounted units change size class through their mount (unit size counts are small 1,788, medium 282, large 257, very_large 279 by rider; 1,014 / 621 / 491 / 480 by mount).
  - 281 units have an `engine` (`battlefield_engines`, 148, whose `battle_entity` has its own HP; the mortar engine has 425). 186 land units have an `articulated_record` (`land_unit_articulated_vehicles`, 56). Neither is followed.
  - `land_units_to_extra_engines` (7) is unread.
- *Needs:* W (displayed speed, mass and HP), SE (bonus vs large, total HP, knockback).
- *Fix:* Embed rider, mount and engine entity blocks separately (speed, mass, HP, size, count) and let the stat engine combine them. At minimum, take movement stats and size from the mount entity when one exists.

**U3. Missile weapons from engines, alternate weapons and explosions (High; SE, W)**
- *Model:* `missile_weapon` = `land_units.primary_missile_weapon` → `default_projectile`. The projectile embeds `explosion_type` as a key only.
- *Gap:*
  - 48 units (for example `wh_main_emp_art_mortar`) have an empty primary weapon and fire through `battlefield_engines.missile_weapon`.
  - `unit_missile_weapon_junctions` (331 rows, 157 units) holds alternate weapons that effects swap in; `effect_bonus_value_missile_weapon_junctions` (254) targets those rows.
  - `missile_weapons_to_projectiles` (13) is unread.
  - `projectiles_explosions` (412 rows: `detonation_damage`, `detonation_damage_ap`, `detonation_radius`, `contact_phase_effect`) is not embedded; 142 units fire explosive projectiles.
  - Projectile fields dropped: `contact_stat_effect`, `overhead_stat_effect`, `spawned_vortex` (171 units), `spread`, `muzzle_velocity`, `calibration_distance`, `can_target_airborne`, `is_spell`, `building_damage_multiplier`, `scaling_damage`, `projectile_penetration`.
- *Needs:* SE, W.
- *Fix:* Resolve the unit's weapon from the land unit or its engine, embed the explosion record (and any phase or vortex it triggers), and list alternate weapons with the bonus rows that enable them.

**U4. Melee weapon omissions (Medium; SE, W)**
- *Model:* `MELEE_FIELDS` keeps damage, AP, bonuses, splash, interval and magic.
- *Gap:* `contact_phase` is dropped (490 units; it is an `OptionalStringU8` with no schema ref, so the link report cannot see it). Also dropped: `scaling_damage` (7 units), `weapon_length`, `collision_attack_max_targets`, `is_spell`, `melee_weapon_type`. `battle_entity_stats` (98 rows, alternate melee/missile loadouts) is unread.
- *Needs:* SE, W.
- *Fix:* Link the contact phase as an embedded phase, the same way abilities embed theirs.

**U5. Armour, shields, resistances and ward save (Medium; W, SE)**
- *Model:* `armour` = `unit_armour_types.armour_value`. The shield is embedded. Resistances are exposed under the raw column names `damage_mod_physical/magic/flame/missile/all`.
- *Gap:* The names hide what they are: `damage_mod_all` is ward save (8 land units have it natively; 1,830 have some resistance). No cap is attached; the caps are `_kv_rules.ward_save_max_value` 90, `damage_resistance_min` 0 and `damage_weakness_min` -100. Resistances added by passive abilities (`stat_resistance_*` in `special_ability_phase_stat_effects`) and by effects (`unit_damage_resistance_*_mod`, 680 unit-set rows) must be merged by the SE, which needs the constants.
- *Needs:* W, SE.
- *Fix:* Rename or annotate the resistance fields and publish a constants document from `_kv_rules` (see §9).

**U6. Unit identity and campaign fields dropped (Medium; AP, W)**
- *Gap:*
  - Not in the model: `main_units.create_time` (recruit turns, 0–3), `is_renown` (257), `can_siege`, `is_high_threat`, `is_monstrous`, `additional_building_requirement` (8), `in_encyclopedia`, `ui_unit_group_land`.
  - From `land_units`: `historical_description_text` (1,064 loc texts, the wiki "lore" paragraph), `can_skirmish`, `training_level`, `hiding_scalar`, `visibility_*`, `campaign_action_points`.
  - DLC ownership: `main_unit_ownership_content_pack_junctions` (2,677).
  - Unit bullet points: `ui_unit_bullet_point_unit_overrides` (7,485 rows for 2,558 units, e.g. Greatswords → anti_infantry, armour_piercing, armoured) with `ui_unit_bullet_point_enums` (223, `state` positive/negative, `sort_order`) and loc `ui_unit_bullet_point_enums_onscreen_name_*`.
- *Needs:* W (bullets, lore, DLC), AP (recruit time, RoR flag).
- *Fix:* Add these as plain fields plus an ordered bullet list.

**U7. Caps, costs and upkeep (Medium–High; AP)**
- *Model:* `recruitment_cost`, `upkeep_cost`, `multiplayer_cost`, `campaign_cap` (358 units > 0), `multiplayer_cap` (296 > 0).
- *Gap:*
  - Faction cost overrides: `main_unit_faction_overrides` (112, keyed by `faction_set`).
  - Pooled-resource costs: `main_unit_resource_costs_junctions` (53).
  - Recruitment-source costs: `unit_recruitment_source_overrides` (28, `resource_costs`).
  - Multiplayer caps by unit set and subculture: `unit_set_to_mp_unit_caps` (923).
  - Effect-driven caps: `unit_cap` bonuses, 114 on unit sets and 107 on unit records. These are derivable, but nothing indexes "what raises this unit's cap".
  - Unit upgrades: `unit_purchasable_effects` (137) with `unit_purchasable_effect_sets` (2,017 unit rows, Greenskin scrap upgrades and similar); `unit_upgrade_to_unit_groups` (151) with tech (140) and building (39) requirements.
  - Domination costs: `battle_currency_units_cost_values` (2,234).
- *Needs:* AP.
- *Fix:* Add a `costs` block with overrides and resource costs, plus a reverse index from unit (via unit sets) to cap-modifying effects.

**U8. Recruitment sources: RoR, mercenaries, allied recruitment, garrisons (High; AP, W)**
- *Model:* Only `building_units_allowed` → `recruited_by_buildings`.
- *Gap:* 539 non-character units have no building source: 256 RoR, 409 in mercenary pools (overlapping), 28 with source overrides, 124 unexplained by these tables. Unread:
  - `mercenary_pools` (63, with `recruitment_source`), `mercenary_pool_to_groups_junctions` (884, with faction, subculture and tech requirements), `mercenary_unit_groups` (649)
  - `faction_to_mercenary_set_junctions` (194), `province_to_mercenary_set_junctions` (1,032)
  - `recruitment_sources` (24, `max_per_army`, e.g. `grudge_settler` 3, `ogre_mercenaries` 3, `allied_recruitment` 4)
  - `allied_recruitment_unit_permissions` (753), `allied_recruitment_core_units` (378), `building_allied_units` (1,093)
  - `campaign_mercenary_unit_character_level_restrictions` (268)
- *Needs:* AP, W.
- *Fix:* Add a `recruitment` list per unit, one entry per source type (building, mercenary pool, RoR, allied, special source) with its conditions and cap.

**U9. Unit attributes and unit sets (Low–Medium; W, SE)**
- *Model:* Attributes come from `unit_attributes_to_groups_junctions`. The description uses loc `unit_attributes_bullet_text_*`.
- *Gap:* That loc text is `"Title||Body"`, and the delimiter is passed through: 2,606 unit lines contain `||` (e.g. `"Hide (forest)||This unit can hide in forests…"`). Unit sets have no entity and no loc (0 `unit_sets_*` loc keys). A bonus target's `unit_set` is an opaque key; resolving it means scanning every unit's `unit_sets`.
- *Fix:* Split title and body. Consider a small `unit_set` index (key → members, exp range, special_category) so effect pages can list the units they affect.

### 2. Abilities and spells

**A1. Sub-records kept as keys only (High; SE, W)**
- *Model:* `Activation` has `spawned_unit`, `activated_projectile`, `bombardment` and `vortex` as strings.
- *Gap:*
  - `battle_vortexs` (288: `damage`, `damage_ap`, radius, duration, speed, `contact_effect`) is used by 342 abilities.
  - `projectile_bombardments` (126: `num_projectiles`, `projectile_type`, `radius_spread`, `arrival_window`) by 152.
  - Activated projectiles by 110, spawned units by 170 (all 170 keys resolve to `main_units`, so they are linkable).
  - `miscast_explosion` → `projectiles_explosions` on 216.
  - Army abilities: `army_special_abilities` (254) and `effect_bonus_value_military_force_ability_junctions` (382) are unmodelled; those bonus targets are raw keys.
- *Needs:* SE (spell damage), W (spell pages).
- *Fix:* Embed vortex, bombardment and projectile damage blocks (with their contact phases). Link spawned units, and add army abilities to the ability entity.

**A2. Overcast, lores, UI lines and superseding (Medium–High; W, CP)**
- *Gap:*
  - `unit_abilities.overpower_option` (overcast variant, 202 abilities) is not modelled.
  - Lore membership (`special_ability_groups_to_unit_abilities_junctions`, 1,360 rows, 109 groups) is unread. Only `character.lore_of_magic` exists; abilities do not know their lore. `effect_bonus_value_special_ability_group_junctions` (381, e.g. lore-wide cost reductions) stays raw.
  - `special_ability_groups_to_units_junctions` (782) is unread.
  - `unit_abilities_to_additional_ui_effects_juncs` (2,993 rows on 1,289 abilities) with `unit_abilities_additional_ui_effects` (453, `effect_state`, `sort_order`, loc 452) is unread. These are the tooltip bullet lines.
  - `unit_ability_superseded_abilities_set_elements` (90) is unread.
  - Phase names: loc `special_ability_phases_onscreen_name_*` has 567 non-empty texts; unread.
- *Fix:* Add `overcast: Link`, `lore: Link`, ordered `ui_effects[]`, `supersedes[]` and phase `name`.

**A3. Phase fields dropped (Medium; SE)**
- *Model:* 16 `PHASE_FIELDS`, plus stat and attribute effects. `how` is add (1,635) or mult (1,347).
- *Gap:* Dropped: `imbue_contact` (70 phases), `inspiration_aura_range_mod`, `barrier_heal_amount`, `mana_max_depletion_mod`, `remove_magical`, `freeze_recharge`, `freeze_fatigue`, `affects_allies/enemies`, `spreading` (`special_ability_spreadings`, 26). 59 phases carry at least one of these. Also dropped from `unit_special_abilities`: `target_intercept_range`, `only_affect_target`, `update_targets_every_frame`, `spawn_type`, `spawn_is_transformation`, `shared_recharge_time`, `is_hidden_in_ui_for_enemy`. Effects modify some of these (`target_intercept_range_mod` 35 rows, `shared_cooldown_mod` 18).
- *Fix:* Add the fields that effects modify or that change targeting.

**A4. Ability sources require a three-hop join (Medium–High; CP, W)**
- *Model:* `ability.units` and `ability.characters` come from `land_units_to_unit_abilites_junctions` via the associated unit. `modified_by_effects` lists effects. A skill knows its effects, and an effect knows its bonus targets.
- *Gap:* 1,517 abilities are enabled by an `enable` bonus (2,106 rows; `enable_overchage` 395, `disable` 114). By source type: skill 866, item 624, effect_bundle 186, trait 52, building 4, technology 3. 424 skill-enabled abilities have no character link, and 395 abilities are fully orphaned (no unit, character or effect). `modified_by_effects` mixes enabling with modifying (recharge_mod 1,049, cost_mod 506, and so on), and the source (skill, item, tech) is two hops away.
- *Fix:* Add a derived `granted_by` on abilities, `{source: Link, via_effect, bonus_value_id}`, and `grants_abilities` on skills, items and traits.

### 3. Characters

**C1. Mount and ancillary grants from skills (High; CP, W)**
- *Gap:* `character_skill_level_to_ancillaries_junctions` (738 rows: mount 716, general 14, arcane_item 8) is unread. Karl Franz's Deathclaw skill shows only the effect `wh_main_effect_enable_mount_deathclaw`, with no ancillary and no mounted unit. `item.bodyguard_unit` exists (726 items), but there is no skill ↔ item link and no reverse from unit to character. 814 of 1,304 lord/hero units have no character. `units_custom_battle_mounts` (681: base_unit → mounted_unit) and `character_skill_node_ancillary_locks` (6) are unread.
- *Fix:* Add `SkillLevel.ancillaries: Link[]` and `character.unit_variants: [{unit, via_skill|via_item|custom_battle}]`, and give units a reverse link to their character.

**C2. Rank, XP and skill points (High; CP)**
- *Gap:*
  - `character_experience_skill_tiers` (352 rows: `agent_key`, `skill_rank`, `experience_threshold`, `skill_points`, campaign and army/navy variants; e.g. general rank 0 → 1,000 XP, 1 point) is unread.
  - `character_skills_to_level_reached_criterias` (888: skill auto-upgrades at a character level, e.g. tomb prince steed at level 3) is unread.
  - Skill-level rank variants: `_skills` reads only `character_skill_level_details` rows whose faction, subculture and campaign are all empty. 16 rows are dropped, and for 14 skills those were the only rank data, so their `unlocked_at_rank` is null.
  - `character_skill_categories` (42: indent bands, order, colour, per-subtype overrides) is unread, so the tree's row labels are missing.
- *Fix:* Add a `progression` document per agent type and campaign. Keep all level-detail variants with their restrictions, and add auto-upgrade rules to skills.

**C3. Legendary lords, starting lords and campaign availability (Medium–High; CP, AP, W)**
- *Gap:*
  - `faction_starting_general_effects` (106 subtypes → innate effect bundles, e.g. `wh2_dlc09_tmb_arkhan` → `wh2_dlc09_lord_trait_tmb_arkhan`) is unread.
  - `frontend_faction_leaders` (131 rows, 106 lords, 105 factions: start faction, portrait, difficulty) is unread.
  - `campaign_to_agent_subtypes` (181, e.g. LLs available in `wh3_main_chaos`) is unread.
  - `unique_agents` (52) is unread.
  - DLC ownership (`agent_subtype_ownership_content_pack_junctions`, 283) is unread.
  - 48 characters have `agent_types: []` because `agent_types` is derived only from `faction_agent_permitted_subtypes`.
- *Fix:* Add `is_legendary`, `starting_factions`, `innate_bundles`, `campaigns` and `dlc`. Fall back to the skill node set's `agent_key` for agent type.

**C4. Item eligibility, slots, sets and armory (High; CP)**
- *Model:* Item has `agent_types` (1,376 rows), `agent_subtypes` (1,115), `required_skills` (726), effects, and `applies_to`.
- *Gap:*
  - `ancillaries.faction_set` is not modelled, and every one of the 2,671 items has it: 594 `all`, the other 2,077 across 62 restricted sets such as `anc_set_exclusive_dwarfs`. `faction_sets`/`faction_set_items` (1,107) are unread.
  - Slot counts per category and faction (`ancillaries_categories_faction_junctions.allowed_per_character`, 75) are unread.
  - Item sets (`ancillary_sets` 85, `ancillary_set_ancillary_junctions` 204, `ancillary_set_effect_junctions` 184) are unread.
  - Armory (Daemon Prince and similar): `armory_items` 362, `armory_items_to_effects` 1,498, `armory_item_sets` 115, `armory_item_set_items` 1,282, `agent_subtypes_to_armory_item_sets` 85, plus slot types and blacklists. All unread.
  - Tech-granted items: `technology_nodes_to_ancillaries_junctions` (25).
  - `applies_to` is `"."` for 2,619 items and empty for 52, so it carries no information.
  - `character.items` (REVERSE) only follows subtype inclusions; 547 items are allowed by agent type only, and 1,191 have neither.
- *Fix:* Resolve faction sets once (a set resolver exists for chain sets in `regions.py`) and expose eligibility as culture/subculture/faction lists. Add item-set and armory entities.

**C5. Skill trees (Low–Medium; CP)**
- *Model:* Good coverage: nodes (with faction, subculture and campaign restrictions: 567 restricted nodes, 27 campaign-only), links (`REQUIRED`/`SUBSET_REQUIRED`), locks. 16 subtypes have more than one tree.
- *Gap:* Per-level effect values are replacements, not increments. For example `wh2_dlc09_skill_tmb_army_buff_basic_archers` ammo is 8 → 12 → 20, and 1,204 skills have more than one level. The model keeps levels separate, which is right, but nothing states the rule (open question). Also dropped: `character_skills.influence_cost`, `is_female_only/male_only_background_skill`, link UI positions (fine for data; needed only to draw).
- *Fix:* Document the per-level semantics in the schema.

**C6. Traits (Low; CP, W)**
- Levels, thresholds, effects and antitraits are captured. 45 traits have no name. Tech-granted traits (`technology_character_traits_junctions`, 12), vows (`bretonnia_vows_to_traits` 39, `agent_subtype_to_vows` 39) and `remove_on_skill_reset` are unread. Trait triggers are Lua (guide §5; confirmed by the absence of trigger tables).

### 4. Effects

**E1. Scope model not resolved (High; SE, CP, AP)**
- *Model:* `EffectApplication {effect: Link, scope: str, value: float}`.
- *Gap:* `campaign_effect_scopes` (435 rows, columns `source`, `target`, `location`, `ownership`, `territory`) is unread. 346 distinct scopes are in use across skills, buildings, bundles, items, techs and traits. Top skill scopes: `character_to_character_own` 10,299, `general_to_force_own` 3,236, `agent_to_parent_army_own` 581. The planners need to know an effect applies to "the Lord's army" rather than "the character". Also unread: the scope suffix loc `campaign_effect_scopes_localised_text_*` (322 non-empty, e.g. `(Lord's army)`), which the in-game tooltip appends, and `campaign_effect_scope_agent_junctions` (50).
- *Fix:* Embed a resolved scope object (`source`, `target`, `location`, `ownership`, `territory`, `suffix_text`) or a scope index entity.

**E2. Bonus value semantics and conditions (High; SE)**
- *Model:* Effects carry `bonus_targets` from all 53 `effect_bonus_value_*` tables (23,110 targets on 13,105 effects; 1,959 effects have none).
- *Gap:*
  - 369 distinct bonus ids (519 table/id pairs) with no dictionary. 51 of the referenced `campaign_bonus_value_ids_*` enum tables are absent from the build (only 2 exist), and there is no loc. Flat versus multiplicative is encoded as `_mod`/`_mult`/`_add` suffixes and the `%+n%` template.
  - Battle-context conditions: `effect_bonus_value_battle_context_junctions` (440) points at `campaign_bonus_value_battle_context_specifiers` (92: night only, force types), plus the culture (227), faction (5), battle type, ground type, force status and territory junctions. All unread, so conditional bonuses such as "melee attack vs Tomb Kings" or "during ambush" appear unconditional. Same for the unit-attribute (66), unit-ability (6) and army-ability (6) context tables.
  - Raw targets by table: rituals 932, pooled resource factors 667, agents 645, attrition 612, army abilities 382, ability groups 381, scripted 328, agent actions 326, name records 283, alternate missile weapons 254, building sets 247, unit upgrades 243, siege items 221, and others.
  - `effect_bonus_value_basic_junction` (647) legitimately has no target.
- *Fix:* Hand-maintain a bonus-id dictionary (stat, operation, unit) and join it into bonus targets. Resolve battle contexts into a `conditions` object.

**E3. Missing application sources (Medium; W, CP)**
- *Gap:* 2,668 effects have `sources: []`. 468 of them are applied by unread tables: `campaign_effect_list_effect_junctions` 414 (via `technology_initiative_effects` 217 and initiatives), armory 28 + 11, ancillary sets 15, action results 3. The other ~2,200 are probably Lua-applied or unused.
- `sources` is deduplicated and loses the value and scope per source, so an effect page cannot say "+5 from skill X, +10 from item Y" without loading every source.
- *Fix:* Read the extra application tables, and add `value` and `scope` to the reverse `sources` entries.

**E4. Presentation (Low; W)**
- Effect `Link.name` is the description template (e.g. `"Ammunition: %+n% for Skeleton Archers…"`), so every application needs client-side substitution with `value`, `is_positive_value_good` and the scope suffix.
- 514 effects and 1,039 bundles have no title.
- Applications are ordered by effect key, but the game orders by `effects.priority`, which lives on the effect entity rather than the application.
- 150 values show float32 artefacts (e.g. `0.90000004` ×74; also phase `fatigue_change_ratio` ×104).
- `EffectApplication.source` repeats the parent entity on every application.
- *Fix:* Round float32 fields at build time and add `priority` to the application.

### 5. Buildings and economy

**B1. Recruitment details and garrisons (Medium; AP, W)**
- *Model:* `units_recruited` is a sorted set of unit keys from `building_units_allowed`.
- *Gap:*
  - The set drops `XP` (17 rows give starting rank) and hides 47 duplicate building/unit pairs. The `faction` and `conditions` columns are unused in this build (0 rows set), and `enabled` is false on all 6,396 rows, so it looks unused.
  - Garrisons are unread: `building_level_armed_citizenry_junctions` (3,301 rows on 1,558 levels) → `armed_citizenry_units_to_unit_groups_junctions` (4,825, with priority), e.g. `wh_main_emp_settlement_major_2` → spearmen, swordsmen, crossbowmen, halberdiers.
  - Also unread: `building_allied_units` (1,093) and `unit_upgrade_to_building_level_requirements` (39).
- *Fix:* Store `[{unit, xp}]` and a `garrison` list per level.

**B2. Upgrade graph, requirements, slots and sets (Medium; W, AP)**
- *Gap:*
  - `building_upgrades_junction` (3,330; 135 levels branch into several upgrades) is unread. `building_chain.levels` is a flat list ordered by `level`, which misrepresents branching chains.
  - `building_downgrade_junctions` (1,493) and `building_level_required_buildings` (8) are unread.
  - Slot unlocks per settlement level (`campaign_building_chain_slot_unlocks`, 349) and `settlement_type_to_building_chains_junctions` (3,508) are unread.
  - `building_sets` (280, with loc names) and `building_set_to_building_junctions` (2,606) are unread, yet 247 bonus targets point at building sets.
  - `building_levels.slave_cap_contribution`, `health_override` and `primary_slot_building_building_level_requirement` are dropped.
  - Chain encyclopedia descriptions (`building_chains_encyclopedia_description_*`, 1,943 keys), building flavour text (548) and variant descriptions are not modelled.
- *Fix:* Add `upgrades_to[]` and `downgrades_to[]` on levels, a building-set index, and settlement slot rules.

**B3. Context-conditional building effects (Medium; SE, W)**
- *Model:* `context_requirement` is a raw key (4,596 of the 21,613 junction rows carry one).
- *Gap:* 282 expressions, e.g. `IsChaosCampaign` (757 rows), `WallEffect` (490), `IsNOTUniqueRegionOrFort` (154), `FavouredCorruption*`. `building_effect_context_expressions` (373, with `expression` and display flags) and its loc `building_effect_context_expressions_display_text_*` are unread. A campaign-specific building effect therefore looks unconditional.
- *Fix:* Resolve the expression and its display text, and flag the campaign-scoped ones.

**B4. Availability and economy (Low–Medium; W)**
- Chain availability is good: 1,821 of 1,943 chains, with culture/subculture/faction/campaign.
- `building_level.cultures` (from variants) is empty for 2,731 of 5,259 levels, so the level-level `cultures` field is unreliable on its own.
- Resources are modelled only through special slot templates (204 icons). `resources_to_campaign_junctions` (36) and the pooled-resource family (`pooled_resources` 246, `campaign_group_pooled_resource_effects` 714) are unread.
- `building_levels.resource_requirement`, `commodity` and `first_in_world_bundle` are empty in all rows (no gap).

### 6. Technology

**T1. Node-level restrictions dropped (Medium–High; CP/AP campaign planning, W)**
- *Model:* `TreeNode` and `Placement` have tier, indent, cost, resource cost, parents and UI group, but no faction or campaign.
- *Gap:* `technology_nodes.faction_key` is set on 315 of 1,843 nodes (e.g. 84 for `wh3_dlc27_hef_aislinn`, 33 each for the Chaos warlords) and `campaign_key` on 30 (18 `wh3_main_combi`, 12 `wh3_main_chaos`). All 33 node sets have an empty `campaign_key`, so restrictions exist only on nodes and are lost. A tree shows nodes the player's faction or campaign never sees.
- *Fix:* Add `faction` and `campaign` to `TreeNode` and `Placement`.

**T2. Unlock conditions, grants and tabs (Medium; W, CP)**
- *Captured:* required technologies (114), required buildings (91), `required_parents`, links.
- *Unread:*
  - `technology_script_lock_reasons` (88 script-locked techs, e.g. `tech_dlc17_bst_bretonnia_locked`)
  - `technology_nodes_to_ancillaries_junctions` (25), `technology_character_traits_junctions` (12)
  - `technology_initiative_effects` (217, effects via `campaign_effect_lists`)
  - `unit_upgrade_to_tech_requirements` (140)
  - `mercenary_pool_to_groups_junctions.tech_requirement` (tech-gated mercenaries)
  - `technology_ui_tabs_to_technology_nodes_junctions` (851) and `technology_ui_tabs` (26), the multi-tab trees
  - `technology_category_modules` (7, tier-band bundles)
- Research-time formula inputs are in the model (campaign variables, `research_points` effects), per the spec's non-goal.
- *Fix:* Add `script_locked`, `grants` (items, traits, initiatives) and `tab` on nodes.

### 7. Factions and campaigns

**F1. Faction entity is thin (Medium–High; AP, CP, W)**
- *Model:* Name, adjective, culture/subculture, category, rebel/quest flags, flag, colour, units (custom battle only), characters.
- *Gap:*
  - No `playable`, `campaigns` or `is_major`. `start_pos_factions` has 812 rows: combi 534 (104 playable, 112 major), chaos 265 (25/26), prologue 13 (1/8). The model has 717 factions because some appear in more than one campaign.
  - No starting regions (`region.starting_owner` exists, but REVERSE has no faction → regions entry) and no capital.
  - No legendary lord (`frontend_faction_leaders`) and no start blurb: `start_pos_factions.long_description` and loc `factions_attack_desc_*`/`factions_defend_desc_*` (717 each) are unread.
  - `military_group`, `waaagh_faction`, `faction_to_faction_groups_junctions` (550), DLC ownership (`faction_ownership_content_pack_junctions`, 380), `start_pos_diplomacy` (362) and `start_pos_entity_association_faction_regions` (225) are unread.
  - 623 of 717 factions have no adjective.
- *Fix:* Add `starts: [{campaign, playable, is_major, capital, regions[], leader}]` built from the start_pos tables.

**F2. Campaign-specific permissions scattered or dropped (Medium; AP, W)**
- *Present:* region `campaign`, chain availability `campaign`, skill node `campaign`, difficulty `campaign`, campaign-variable overrides.
- *Dropped:* tech node campaign (T1), `campaign_to_agent_subtypes` (181), `units_custom_battle_permissions.campaign_exclusive` (228 rows), building `IsChaosCampaign` contexts (757), `campaign_group_member_criteria_campaigns` (41).
- There is no `campaign` entity. `campaigns` has 3 rows (`wh3_main_chaos`, `wh3_main_combi`, `wh3_main_prologue`) with `map_name`.
- Starting armies and characters are not in the DB: there is no `start_pos_characters`, `start_pos_armies` or `start_pos_units` table (only calendars, diplomacy, entity associations, factions, regions). They live in `startpos.esf`, as `regions.py` already notes for slot templates.
- *Fix:* Add a campaign entity, and treat "which campaign" as a filter dimension on every entity that has restrictions.

### 8. Loc and text

**L1. Coverage (from `manifest.missing_names` and field null counts)**
- Missing names: effect 514, effect_bundle 1,039, skill 91, building_level 81, trait 45, unit 6, technology 3, technology_tree 2, item 2, ability 1.
- Null descriptions: skill 830 of 5,944, character 443 of 613, effect_bundle 1,710, item 181 (explanation 2,269 is optional text), technology long_description 1,486, faction adjective 623.
- 19 unresolved `{{tr:}}` targets. Examples still in the output: `{{tr:effects_description_wh3_cp1_pooled_resource_relics_other}}` (49 occurrences) and `{{tr:building_culture_variants_name_wh3_main_sla_marauders_3wh3_main_sla_slaanesh}}` (11), plus `building_chains_chain_tooltip_wh3_dlc27_*` and `character_skills_localised_*_wh3_cp1_*`. These look like tr targets whose own key includes the table prefix but whose loc entry is missing or empty.
- No `{{tt:}}` or `{{Cco…}}` tokens reach the model. Markup passes through as designed: `[[img:` 24,343, `[[col:` 4,314.

**L2. Text that exists but is not modelled (Medium; W)**

| Text | Loc entries |
|---|---|
| Unit historical/lore descriptions | 1,064 |
| Ability tooltip bullet lines (`unit_abilities_additional_ui_effects_localised_text_*`) | 452 |
| Phase names | 567 non-empty |
| Unit bullet-point names | via `ui_unit_bullet_point_enums` |
| Scope suffixes | 322 |
| Building set names/descriptions | 280 / 280 |
| Chain encyclopedia descriptions | 1,943 |
| Building flavour texts | 548 |
| Faction attack/defend descriptions | 717 / 717 |
| Start-pos settlement names (`start_pos_settlements_onscreen_name_*`) | ~811 |
| Building context display text | per expression |
| Item category names (`ancillaries_categories`) | 24 |

- The loc `tooltip` flag column is ignored (low).
- *Fix:* Add these as fields on the owning entity. The attribute title/body split (U9) is the only parse needed.

### 9. Engine-derived stats and mechanics (guide §5)

**M1. Constants are in the DB but not exported (Medium–High; SE, W)**

`_kv_rules` (274), `_kv_morale` (130), `_kv_fatigue` (29), `_kv_unit_ability_scaling_rules` (8), `_kv_winds_of_magic_params` (16) and `_kv_experience_bonuses` (7) are unused. `link_report` excludes them, because `Context._record_tables` and the report ignore `_`-prefixed names. Relevant values in this build:

- **Armour roll:** `armour_roll_lower_cap` 0.5 (matches the guide's 0.5×–1× roll). No explicit 100 armour cap key was found.
- **Ward save:** `ward_save_max_value` 90, `ward_save_min_value` -100. Resistance floor `damage_resistance_min` 0, weakness floor `damage_weakness_min` -100. No generic "resistance max 90" key was found; the guide's "all resistances capped at 90%" rests on the guide only.
- **Charge and collision:** `collision_damage_armour_penetration_ratio` 0.7 (matches the guide's 70% AP), `collision_damage_maximum` 70, `collision_damage_modifier` 0.6, `charge_decay_duration` **13** (the guide says a 15 s window; see mismatches), `bracing_charge_reflector_bonus` 2.0, `devastating_flanker_charge_multiplier` 2.0.
- **Melee hit chance:** `melee_hit_chance_base` 35, `min` 8, `max` 90; flank/rear defence penalties 0.6/0.3; `melee_defence_formed_attack_bonus` 5.
- **Missile AP:** `missile_armour_piercing_coefficient` 0.5, `missile_armour_penetrating_coefficient` 0.25 (not in the guide).
- **Ability scaling:** direct-damage scaling by unit size (small 0.25 … ultra 1.0), `healing_percentage_cap` 0.75.

**M2. Derived numbers that are not stored (the SE and wiki must compute them)**
- **Total HP:** rider HP plus bonus HP per man, plus mount, engine and articulated entity HP. The model has only the rider's `hit_points` (U2).
- **Unit size scaling:** `unit_stat_to_size_scaling_values` (24 rows: single-entity damage scalars by unit size), `unit_size_global_scalings` (12, buildings and siege). `num_men` is the ultra value.
- **Rank bonuses:** `unit_experience_bonuses` (5: melee attack/defence growth 0.6/0.12, morale, accuracy, reload).
- **Fatigue:** `unit_fatigue_effects` (21). Terrain: `ground_type_to_stat_effects` (29).
- **Damage split:** base vs AP, bonus vs large/infantry (needs entity `size`, U2), magical/flaming, resistances by type, ward save first, then armour on the base portion only (guide §5 prose; constants above).
- **Displayed "Missile strength" and "Melee damage"** in the unit card are sums the engine derives (damage + AP (+ bonus)); **damage per 10 s** uses `melee_attack_interval` (the model has it) or reload with `base_reload_time`/`shots_per_volley`/`burst_size`/`projectile_number` (the model has these, but not the engine-fired weapons, U3).
- **Explosion and vortex damage over time** needs the records from U3/A1.
- **Prose still required:** leadership and routing, mass/knockback math, hit reactions, charge-impact formula, winds-of-magic pool behaviour, replenishment, corruption. The DB holds only inputs (`_kv_morale`, `_kv_fatigue`, `_kv_winds_of_magic_params`).
- *Fix:* Export a `constants` document (selected `_kv_*` rows with notes), a `scaling` document (size and rank tables), and a curated mechanics prose page that cites the constant keys, patch and build id. Include `_kv_*` tables in the link report.

### 10. `link_report.json` `source_not_read`, grouped by theme

484 references come from about 350 unread tables. By source-table theme (approximate, keyword-classified):

| Theme | Refs | Tables | Meaningful examples |
|---|---|---|---|
| Recruitment, rosters, costs (AP) | ~65 | ~50 | `units_to_groupings_military_permissions`, `units_to_exclusive_faction_permissions`, `mercenary_unit_groups`, `mercenary_pool_to_groups_junctions`, `unit_recruitment_source_overrides`, `main_unit_faction_overrides`, `main_unit_resource_costs_junctions`, `allied_recruitment_*`, `building_allied_units`, `units_custom_battle_mounts`, `unit_set_to_mp_unit_caps`, `armed_citizenry_*`, `unit_purchasable_effect_sets`, `unit_upgrade_to_*`, `campaign_mercenary_unit_character_level_restrictions`, `battle_currency_units_cost_values`, `main_unit_ownership_content_pack_junctions` |
| Characters, items, skills (CP) | ~53 | ~42 | `character_skill_level_to_ancillaries_junctions`, `character_skills_to_level_reached_criterias`, `character_skill_node_ancillary_locks`, `character_skill_categories`, `ancillary_set_*`, `armory_*`, `ancillaries_categories_faction_junctions`, `faction_starting_general_effects`, `frontend_faction_leaders`, `campaign_to_agent_subtypes`, `unique_agents`, `technology_nodes_to_ancillaries_junctions`, `technology_character_traits_junctions`, `bretonnia_vows_to_traits` |
| Battle stats and abilities (SE) | ~35 | ~30 | `mounts.entity`, `battlefield_engines.missile_weapon`/`battle_entity`, `land_unit_articulated_vehicles`, `unit_missile_weapon_junctions`, `missile_weapons_to_projectiles`, `projectile_bombardments.projectile_type`, `projectiles_explosions.contact_phase_effect`, `battle_vortexs.contact_effect`, `army_special_abilities`, `special_ability_groups_to_unit_abilities_junctions`, `special_ability_groups_to_units_junctions`, `unit_abilities_to_additional_ui_effects_juncs`, `unit_ability_superseded_abilities_set_elements`, `unit_experience_bonuses`, `unit_stat_to_size_scaling_values`, `unit_fatigue_effects`, `ground_type_to_stat_effects`, `ui_unit_bullet_point_unit_overrides`, `battle_entity_stats` |
| Effect glue | ~15 | ~13 | `campaign_effect_list_effect_junctions`, `armory_items_to_effects`, `ancillary_set_effect_junctions`, `effects_additional_tooltip_details` (tooltip loc is read; the table is not), `campaign_effect_scope_agent_junctions`, battle-context culture/faction junctions |
| Campaign, buildings, tech, regions (W, AP) | ~167 | ~114 | `building_upgrades_junction`, `building_downgrade_junctions`, `building_set_to_building_junctions`, `campaign_building_chain_slot_unlocks`, `settlement_type_to_building_chains_junctions`, `building_level_required_buildings`, `technology_script_lock_reasons`, `technology_ui_tabs_to_technology_nodes_junctions`, `technology_initiative_effects`, `faction_set_items`, `start_pos_diplomacy`, `start_pos_entity_association_faction_regions`, `campaign_map_regions`, `rituals` (1,326), `initiatives` (619), `pooled_resource_*`, `culture_settlement_occupation_options` |
| Noise for these products (audio, campaign AI, VFX, art sets, set-piece battles, loading screens, UI cheat sheets) | ~149 | ~105 | Safe to ignore: `audio_*`, `cai_*`, `campaign_character_art_sets`, `battle_set_piece_*`, `loading_screen_quotes_*`, `climbing_ladders_meshes_definitions` |

**Blind spots of the link report itself:**
1. "Read" means "some query touched the table", so ignored columns never show up. Examples: `technology_nodes.faction_key`/`campaign_key`, `building_units_allowed.XP`, and `units_custom_battle_permissions.campaign_exclusive`, `general_unit` and `siege_unit_*`.
2. Columns without a schema ref are invisible, e.g. `melee_weapons.contact_phase` and `projectiles.contact_stat_effect`.
3. `_kv_*` tables are excluded.
4. `target_not_read` has 287 more references worth mining, notably `land_units.mount → mounts`, `land_units.engine → battlefield_engines`, `projectiles.explosion_type → projectiles_explosions`, `unit_special_abilities.vortex/bombardment`, `*.effect_scope → campaign_effect_scopes` and `ancillaries.faction_set → faction_sets`.

### 11. Cross-cutting misalignments (shape problems)

| # | Field (model) | Problem | Affected |
|---|---|---|---|
| X1 | `unit.base_stats.walk/run/charge_speed, mass, hit_points_per_entity` | Rider values presented as unit values | 1,041 mounted units, 281 engine units |
| X2 | `unit.mount`, `Activation.spawned_unit/activated_projectile/bombardment/vortex`, `Projectile.explosion_type` | Stringly-typed keys, not links or embedded records | 1,070 mounted units; 342 + 152 + 110 + 170 abilities; 142 units |
| X3 | `EffectApplication.scope`, `context_requirement`, `BonusTarget.bonus_value_id`, `BonusTarget.target_key` (battle contexts) | Semantics as opaque strings; the SE cannot tell flat from %, army from character, or conditional from unconditional | 346 scopes; 4,596 building applications; 369 ids; 518 context rows |
| X4 | `unit.custom_battle_factions` → `faction.units` | Custom-battle permission (including 228 `campaign_exclusive` rows) used as the campaign roster | 692 empty factions |
| X5 | `building_level.units_recruited` | Set of keys: loses XP and multiplicity | 17 XP rows, 47 duplicates |
| X6 | `building_chain.levels` | Linear list for a branching upgrade graph | 135 branching levels |
| X7 | `Skill.levels[].unlocked_at_rank` | Only the generic variant kept; faction/campaign variants dropped | 16 rows, 14 skills with null rank |
| X8 | `TreeNode` / `Placement` | Node faction and campaign dropped | 315 + 30 nodes |
| X9 | `UnitAttribute.description` | `"Title\|\|Body"` delimiter not parsed | 2,606 unit lines |
| X10 | `Item.applies_to` | Carries `"."` / `""` only | 2,671 items |
| X11 | `Effect.sources` | Deduplicated links without value/scope, so per-source values are lost | 15,064 effects |
| X12 | `Character.agent_types` | Derived from faction permissions; empty when there are none | 48 characters |
| X13 | Base stat names `damage_mod_*` | `damage_mod_all` is ward save; no caps attached | 1,830 land units with resistances |
| X14 | Float32 values | Printed with artefacts (`0.90000004`) | 150+ values |
| X15 | `Character.abilities` | Only the associated unit's innate abilities; skill/item-granted abilities need a 3-hop join | 424 skill-enabled abilities unlinked |

---

## Where the guide doesn't match this build

1. **`land_units_to_unit_abilities_junctions` does not exist.** The table is misspelled in the game data as `land_units_to_unit_abilites_junctions` (8,700 rows). Only three `land_units_to_*` tables exist: that one, `land_units_to_battle_personalities_junctions` (1,362) and `land_units_to_extra_engines` (7).
2. **`subcultures` does not exist.** It is `cultures_subcultures` (32).
3. **The guide's `X_to_effects_junctions` naming** doesn't match the real names: `character_skill_level_to_effects_junctions`, `building_effects_junction`, `technology_effects_junction`, `ancillary_to_effects`, `trait_level_effects`, `effect_bundles_to_effects_junctions`, `armory_items_to_effects`, `ancillary_set_effect_junctions`, `campaign_effect_list_effect_junctions`.
4. **The bonus-value family** has 53 tables in this build. The guide's example "religion" table does not exist.
5. **The skills chain omits `character_skill_node_set_items`** (29,517 rows), which is required to map node sets to nodes. `character_skill_node_links` does exist (20,590).
6. **"Warriors of Chaos recruitment lives only in `building_levels_tables`" is not supported.** `building_levels` has no unit column. 69 of 97 non-character `_chs_` units are in `building_units_allowed`, and the rest come through mercenary pools (e.g. `wh3_dlc20_chs_province_pool`, 121 group rows).
7. **Campaign keys:** the guide gives Realm of Chaos as `campaigns_wh3_main_chaos`; the data key is `wh3_main_chaos`. Immortal Empires is `wh3_main_combi` as stated, but `campaigns.map_name` is `wh3_main_combi_map_5` (the guide's `wh3_main_combi_map_1` is only the `terrain_location`). There is a third campaign, `wh3_main_prologue`.
8. **Startpos/region tables:** this build has only `start_pos_factions`, `start_pos_regions`, `start_pos_diplomacy`, `start_pos_calendars` and `start_pos_entity_association_faction_regions`. There are no starting character, army or unit tables.
9. **Charge window:** the guide says 15 s (Fandom, patch 1.12.1). `_kv_rules.charge_decay_duration` is 13.0 in this build. (`_kv_morale.charge_bonus` = 15.0 exists but appears to be a morale value.)
10. **"All resistances capped at 90%":** only `ward_save_max_value` 90 exists as an explicit cap. No generic resistance maximum was found in `_kv_rules`.
11. **"Hardcoded engine behaviour":** several coefficients the guide treats as external knowledge are DB rows (armour roll 0.5, collision AP 0.7, hit-chance base/min/max, missile AP coefficients). The formulas that combine them remain engine behaviour.
12. **OwenTanzer counts (patch 8.1.1) differ from this build:**
    - Technologies 1,620 vs 1,869.
    - Node sets 521 vs 547 skill node sets.
    - Regions 641 vs 569 combi start-pos regions (945 in `regions`).
    - Provinces 214 vs 316.
    - The 104 playable IE starts match (`start_pos_factions`, combi, playable = 104).
13. **Loc keys `<table>_<column>_<record_key>` have exceptions this build relies on.** Unit names come from `land_units_onscreen_name_<land_unit>`, not from main_units. Building level names concatenate `building_culture_variants_name_<level><culture><subculture><faction>`. Settlement names use `start_pos_settlements_onscreen_name_settlement:…`. Attribute bullets pack title and body with `||`.

---

## Open questions

1. **HP:** how does the game combine rider, mount, engine and articulated entity HP with `bonus_hit_points` and `num_mounts`/`num_engines` into the displayed unit HP? This needs an in-game check on a few units (Reiksguard, Mortar, Steam Tank, a chariot) before the stat engine fixes the formula.
2. **Large vs infantry:** is it decided by the mount entity's `size`, the rider's, or the larger of the two?
3. **Skill level effects:** do rows for level N replace level N-1 (the values suggest totals: 8 → 12 → 20), or stack? Confirm in-game once.
4. **Unexplained units:** 124 non-character, non-building, non-RoR, non-mercenary units. Are they ritual spawns, summons, event rewards or dead data? Their sources may be Lua-only.
5. **Sourceless effects:** are the ~2,200 effects with no source Lua-applied (`data_script.pack`, a spec non-goal) or unused? If Lua-applied, should the wiki mark them "applied by script"?
6. **`building_units_allowed.enabled`** is false on all 6,396 rows. Is that a decode quirk (schema column mismatch) or a genuinely unused column? The same check applies to `conditions` and `faction`, which are always empty.
7. **`charge_decay_duration` 13 vs the guide's 15 s window:** same mechanic, or decay versus full window?
8. **Where are unit caps for campaign "elite" units enforced** beyond `main_units.campaign_cap` and `unit_cap` effects (e.g. Chaos Dwarf or Ogre caps by building level)? Confirm that no other cap table exists before the army planner design.
9. **Should the model carry the 51 absent `campaign_bonus_value_ids_*` semantics** as a curated dictionary in-repo, and who maintains it per patch?
10. **Should faction and unit availability be modelled per campaign** (IE vs RoC) now, given that start_pos data covers factions and regions but not armies?
