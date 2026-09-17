# Audit: Total War: WARHAMMER III `ui/` layout files

Scope: read-only research into the non-image files under `ui/` in RPFM's dependency cache (rpfm_server 5.0.6, game `warhammer_3`), for the wiki, the character planner and the army planner.
Extracted copy: `scratchpad/game-ui/ui/` (1,009 files, 97 MB). Helper scripts and per-panel text dumps: `scratchpad/dump.py`, `scratchpad/dumps/*.txt`.
No repository files, packs, RPFM settings or `raw/`/`model/` folders were touched. `git status` is clean.

---

## Summary

**Verdict: well worth the read, but don't import the layouts in bulk.** The `.twui.xml` layouts are thin views. Nearly every value they show comes from an engine "context object" (`Cco…`), and most of the order, grouping, colour and limit rules behind those objects already sit in **DB tables we extract but don't model yet**. The layouts are most useful as a map from each panel to the fields and tables it uses, plus exact sizes, states and sentinel rules. The concrete wins:

1. **Unit stat order and bars are in the DB.** `ui_unit_stat_to_classes.list_order` plus `ui_unit_stats` (icon, `max_value`, `min_value`, clamping) and `ui_unit_stat_to_unit_castes.max_value_override` drive the game's stat list: HP, Armour, Leadership, Speed, Melee Attack, Melee Defence, Weapon Strength, Charge Bonus, Ammunition, Range, Missile damage. Each row has a 40×8 bar with a gold base fill and a green or red modifier fill. Our Unit page uses a different, hand-picked order.
2. **Unit "bullet points" are the game's own short unit summary.** `ui_unit_bullet_point_enums` plus `ui_unit_bullet_point_unit_overrides` (7,485 rows) give lines like "Anti-Large" with a positive, negative, very_positive or very_negative state and a sort order. We don't use them.
3. **Colour tags map to real hex values** in `ui_colours` (163 rows), with colour-blind overrides in `ui_colour_profile_colour_overrides`. Our `theme.css` guesses 7 colours, and several are well off: `magic` is cyan `#41E1E1` in game but blue in ours. Loc text uses 44 distinct `col:` names.
4. **`gameText.ts` has a real bug.** Unknown tags such as `[[url:…]]` (1,926 uses), `[[tooltip:…]]` (992), `[[sl_tooltip:…]]` (853), `[[sl_link:…]]` (170), `[[fragment:…]]` and `[[opacity:…]]` are printed as raw `url:script_link_…` text. Their closing tags then pop the wrong open span, which can break colouring. `{{tt:…}}` and `{{Cco…:…}}` tokens also print raw keys.
5. **Effects: scope text and polarity are data too.** The game appends the loc text for `campaign_effect_scopes_localised_text_<scope>` (e.g. `\n([[img:icon_general]][[/img]]Lord's army)`), not the key. It picks the icon and colour from `effects.is_positive_value_good` and the value sign, and hides effects with `priority == 0` (1,339 effect records). Our `scopeLabel()` just replaces `_` with a space.
6. **Sentinels have explicit rules in the layouts.** `NumUses >= 0` shows "Uses: N", otherwise the row is hidden. `TargetRange < 0` shows ∞ (map-wide) and `0` hides the row. Ability `Duration <= 0` shows "(∞)". Mercenary `HasInfiniteUnitCount` shows an empty count.
7. **Unit card art is opaque and dark by design.** The 60×130 icons have no transparency (566 RGB, 455 RGBA with no transparent pixels in a sample). Their mean luminance is about 97/255. The game always layers them over `unit_card_background.png` with a 9-slice `unit_card_recruitment_frame.png` and brightens them on hover or selection (`brighten_t0` at 1.0 or 1.5). That explains why they vanish on our `#16120d` background.
8. **Tree geometry.** Skill cards are 185×67 (72×72 icon, 112×44 wrapped label, 3 level pips of 16×20) with 56 px arrows between them. Rows are `indent` 0–5 and columns are `tier` 0–12. There are **no cross-row prerequisite lines**: only horizontal chain arrows plus a rank lock overlay. Tech nodes are 230×67 (137×44 label, 50×24 turns banner, cost banners). Links are elbow segments with an "N/M parents" badge. Tech UI groups (`technology_ui_groups`) are drawn as named, tinted rectangles behind nodes.
9. **All fixed UI labels are localisable.** Every `textlabel` maps to loc key `uied_component_texts_localised_string_<textlabel>` (10,214 keys), e.g. "Duration:", "Cooldown:", "Character Stats", "Research Rate:". The wiki can reuse the game's own headings.
10. **The game has its own encyclopedia.** `common ui/spell_browser.twui.xml` ("Unit & Spell Browser"): race dropdown, then units grouped by `ui_unit_group_parents` (collapsible headers), then the 290 px unit info panel with its historical description. The spells tab lists lores sorted by `special_ability_groups.sort_order` and tinted with `colour_hex`. The **custom battle** screen is effectively the game's army planner: funds remaining, roster slot counts 5/7/10/20/40, per-group caps, and mount and upgrade options with costs.
11. **`ui/metadata.json` is a documented API reference** for 518 context object types and 6,859 functions, e.g. `CcoEffect.Priority`: "if 0 isn't shown in UI". It is valuable developer reference; don't publish it.

---

## Inventory

40,959 files under `ui/` (39,583 are images). The dependency listing has no per-file sizes; sizes below are measured on the extracted non-image files only. "Loose" means `container_name` was empty (not in a pack). No `.css`, `.csv` or `.ttf` files exist under `ui/`. Fonts are 114 bitmap `.cuf` files in `font/` (`local_en.pack`), not listed further.

### By top-level folder and extension

| Folder | Ext | Count | Size (extracted) | Packs |
|---|---|---:|---:|---|
| (root) | .json | 3 | 2,174 KB | ui.pack |
| (root) | .xml | 2 | 7 KB | ui3.pack |
| (root) | .lua | 1 | 11 KB | ui.pack |
| (root) | (none) | 2 | 82 KB | ui.pack |
| (root) | .environment / .code-workspace / .eff | 1 / 1 / 1 | 6 KB / 1 KB / not extracted | ui.pack |
| 3dui | .dds / .png | 629 / 1 | – | ui.pack |
| 3dui | .rigid_model_v2 / .wsmodel | 238 / 45 | not extracted | ui.pack |
| 3dui | .xml / .material / .environment / .lighting | 20 / 15 / 5 / 1 | 53 / 25 / 25 / 2 KB | ui3.pack (xml), ui.pack |
| battle ui | .twui.xml | 55 | 3,931 KB | ui3.pack |
| battle ui | .xml | 2 | 3 KB | ui3.pack |
| battle ui | .png / .tga | 2,542 / 30 | – | ui.pack |
| buildings | .png | 1,411 | – | ui.pack |
| campaign ui | .twui.xml | 420 | 64,399 KB | ui3.pack |
| campaign ui | .xml | 10 | 2 KB | ui3.pack |
| campaign ui | .png / .psd | 5,521 / 2 | – | ui.pack |
| cco | .cco | 41 | 144 KB | ui.pack |
| cheat_sheet / credits / help_images / movies | .png | 19 / 14 / 43 / 88 | – | ui.pack |
| common ui | .twui.xml | 112 | 6,674 KB | ui3.pack |
| common ui | .xml | 1 | <1 KB | ui3.pack |
| common ui | .png / .dds | 418 / 408 | – | ui.pack |
| cursors | .png / .cur / .bob | 174 / 49 / 1 | – / – / <1 KB | loose |
| dev_ui | .twui.xml / .xml | 54 / 2 | 3,178 KB / <1 KB | ui3.pack |
| effects | .dds | 274 | – | ui.pack |
| effects | .xml / .material | 5 / 5 | 14 / 8 KB | ui3.pack / ui.pack |
| eula | .txt | 14 | 1,243 KB | ui.pack |
| eventpics | .png | 828 | – | ui2.pack |
| flags | .png / .dds | 2,549 / 539 | – | ui.pack |
| frontend ui | .twui.xml / .xml | 41 / 1 | 8,144 KB / <1 KB | ui3.pack |
| frontend ui | .png / .dds | 891 / 1 | – | ui.pack / local_en.pack |
| icu | .dat | 1 | not extracted | ui.pack |
| loading_ui | .twui.xml / .json | 11 / 13 | 914 / 7 KB | ui3.pack / ui.pack |
| loading_ui | .png | 294 | – | ui.pack |
| portraits | .png | 4,587 | – | ui.pack |
| portraits | .bin / .txt | 4 / 1 | – / <1 KB | ui.pack, ui_3.pack |
| skins | .png | 12,068 | – | ui2.pack 12,058; local_en.pack 6; ui2_bl.pack 4 |
| skins | .txt / .jpg / .dds | 3 / 3 / 1 | 37 KB / – / – | ui2.pack |
| spine ui animations | .json / .atlas | 11 / 10 | 172 / 2 KB | ui.pack |
| spine ui animations | .png / .skel / .spine | 51 / 11 / 10 | – | ui.pack |
| spineexamples | .json / .atlas / .skel | 6 / 8 / 6 | 536 / 11 KB / – | ui.pack |
| sprite_anims | .png | 1,775 | – | ui.pack |
| templates | .twui.xml | 131 | 4,163 KB | ui3.pack |
| units | .png | 4,424 | – | ui.pack |

### By extension (totals)

| Ext | Count | Packs | What it is |
|---|---:|---|---|
| .png | 37,698 | ui 24,628; ui2 12,886; loose 174; local_en 6; ui2_bl 4 | art (not extracted) |
| .dds / .tga / .jpg | 1,852 / 30 / 3 | ui, ui2, local_en | textures (not extracted) |
| **.twui.xml** | **824** | **ui3.pack** | **UI layouts and templates, format `version="142"`** |
| .xml | 43 | ui3.pack | `fontcategories.xml`, `animation_presets.xml`, `*.warscape_req.xml`, 3D/material property sets, radar settings |
| .cco | 41 | ui.pack | named reusable context expressions (UI "macros") |
| .json | 33 | ui.pack | `metadata.json` (Cco API docs), `autocomplete.json` (editor lists), `mock_default.json`, loading-screen scripts, Spine skeletons |
| .txt | 18 | ui.pack, ui2.pack | EULAs (14), skin image lists, a portrait naming note |
| .lua | 1 | ui.pack | `coreutils.lua` (generic math helpers) |
| .material / .environment / .lighting | 20 / 6 / 1 | ui.pack | 3D UI rendering |
| .rigid_model_v2 / .wsmodel / .skel / .spine / .atlas | 238 / 45 / 17 / 10 / 18 | ui.pack | 3D and Spine animation assets |
| .cur / .bob / .psd / .bin / .dat / .eff / .code-workspace / (none) | 49 / 1 / 2 / 4 / 1 / 1 / 1 / 2 | various | cursors, source art, portrait settings, ICU data, dev workspace, 2 legacy binary layouts (`Version130`/`132`) |

---

## Format: how the layout XML works

**Root.** `<layout version="142">` contains `<hierarchy>` (the tree, as nested elements named after component ids, each with `this="GUID"`) and `<components>` (one element per component, keyed by the same GUID). All 824 files are version 142 and parse as plain XML.

**Component attributes** (39,471 components): `id`, `uniqueguid`, `offset`, `dimensions`, `docking`/`dock_point`/`dock_offset`, `component_anchor_point`, `priority`, `currentstate`/`defaultstate`, and `template_id` plus `part_of_template` when the component is an instance of a file in `templates/` (e.g. `tmpl=stat_entry`, `square_large_text_tab_toggle`, `building_frame`).

**Component children:**
- `<componentimages>/<component_image imagepath="ui/skins/default/…png">`: the image slots the component can use. Paths are often skin-relative, resolved through `AddDefaultSkinPath(…)`.
- `<states>`: one element per named state (`active`, `hover`, `inactive`, `selected`, `locked`, `positive`/`negative`, rarity names, numbers…) with `width`/`height` and:
  - `<imagemetrics>/<image componentimage=GUID width height dockpoint margin tile colour="#RRGGBBAA" ui_colour_preset_type_key="…" shader_name="set_greyscale_t0|brighten_t0|overlay_t0" shadertechnique_vars="…">`. A non-zero `margin` means 9-slice.
  - `<component_text text textlabel fontcat_name font_m_size font_m_colour font_colour_override_preset_key texthalign textvalign texthbehaviour="Resize|Never split|Slip by character" text_shader_name="text_outline_t0">`.
- `<callbackwithcontextlist>/<callback_with_context callback_id context_object_id context_function_id>` with optional `<child_m_user_properties><property name value/>`. This is the data binding. 41,184 bindings; the most common are `ContextVisibilitySetter` (5,502), `ContextTextLabel` (3,844), `ContextPropagator` (3,001), `ContextImageSetter` (2,194), `ContextList` (1,136), `ContextStateSetter` / `ContextStateSetterConditional` (1,790), `ContextFillBar` (171) and `ContextColourSetter` (263). The properties carry refresh events (`event0="CampaignTechnologyStateChangeAny"`), `update_constant`, `fallback_state` and per-state conditions.
- `<LayoutEngine type="List|HorizontalList|RadialList" spacing margins secondary_margins itemsperrow sizetocontent max_length allow_overlap horizontal_alignment>`: flex-like auto layout (4,808 components).
- `<animations>`/`<triggers>`: animation frames and transitions, not relevant to us.

**Context expressions** are a small functional language evaluated on a `Cco…` object:
- Property chains: `UnitRecordContext.CategoryIcon`, `PlayersFaction.UnitCapForUnit(UnitRecordContext)`.
- Control flow: `GetIfElse(cond, a, b)`, `GetIf`, `Do(…)`, `DoIf`.
- Lists: `.Filter(…)`, `.Sort(SortOrder, true)`, `.Transform(…)`, `.Distinct(Key)`, `.Any`, `.FirstContext(…)`, and lambdas `(x) => { … }`.
- Text: `Format("%+d", RoundFloat(Value - ComparisonValue))`, `Loc("uses_x")`, `.RemoveTextTags`, `.ToUpperLocalised`, `.ParseTextReplacements`.
- Colour: `GetColour("red")`.
- Comments are wrapped in `#…#`. A callback id prefixed with `#` (e.g. `#ContextVisibilitySetter`) is disabled.
- `cco/*.cco` define reusable named expressions per type, e.g. `CcoCampaignCharacter { ExCharacterDetailsInitiativeSetList { InitiativeSetList.Filter(…) } }`, referenced as `Ex…` in layouts.

**Links out of the layouts:**
- **DB records**: through Cco record wrappers (`CcoMainUnitRecord`, `CcoBuildingLevelRecord`, `CcoTechnologyUiGroupRecord`…), `ContextInitDatabaseRecord` with `db_key` (e.g. `db_key="mount"` on `CcoAncillariesCategoryRecord`), and `DefaultDatabaseRecord("CcoCultureRecord").RecordList`.
- **Loc**: static text via `textlabel` → `uied_component_texts_localised_string_<textlabel>` (verified: `dy_title_NewState_Text_41` → "Stats"; `StateText_b31b371a` → "Duration:"). Dynamic text via `Loc("key")`. Tokens `{{tr:key}}` (ui_text_replacements) and `{{CcoType:Function}}` appear inside text.
- **Icons**: literal `imagepath` values, record getters (`IconPath`, `CategoryIcon`, `SmallIcon`), or built paths (`"ui/skins/default/tech_tree_tab_" + Key + ".png"`).
- **Sub-layouts**: `ComponentCreator layout="ui/campaign ui/character_details_panel_skills"`, and tooltips through `ContextLayoutTooltip layout_path="ui/common ui/tooltip_entity_info"`. The `ui_tooltips` table (753 rows) maps tooltip keys to layout names.
- **Engine callbacks**: a panel's core logic often sits in a C++ callback with no expression (`SkillChain`, `TreeCallback`, `CampaignUnitsHUDCallback`, `UnitRecruitmentCallback`). There the layout only gives visuals and states.

**Supporting files:**
- `fontcategories.xml`: named font categories (see Visual system).
- `metadata.json`: API reference for 518 Cco types (221 Record, 148 Campaign, 95 Common, 37 Battle), each function with argument types and a doc string.
- `autocomplete.json`: editor lists (307 callback ids, 406 context function ids, 405 context object ids, 219 events).
- `loading_ui/dynamic_loading_screen_data/*.json`: timed `SetText(Loc(…))`/`SetImage` scripts.
- `*.warscape_req.xml`: asset dependency lists.

---

## Panel-by-panel findings

### 1. Unit card and unit info panel

**Unit info panel** (`common ui/unit_information.twui.xml`, 290 px wide, used in campaign, battle, custom battle and the browser), top to bottom:
1. **Name**: `tx_unit-type`, `header_14`, `ContextTextLabel => Name`.
2. Skull separator.
3. **Subheader**: category name (`UnitRecordContext.CategoryName`, `body_12` in `ui_font_faded_grey_beige`, tooltip `CategoryTooltip`) with a 22×22 category icon in a 34×34 round frame. The frame state comes from `UnitRecordContext.SpecialCategoryKey`: `renown`, `crafted`, `elector_counts`, `blessed_spawning`, `chieftain`, `mistwalker`, `tech_lab`, `default`. **This is how the game tells same-named units apart** (RoR, crafted, Elector Count versions). A purchased-effects icon list follows.
4. **Bullet points or description** (toggle). `ContextList => BulletPointList`, a 257×20 row with states `positive`/`negative`/`very_positive`/`very_negative`, arrow icons `arrow_increase_1/2` and `arrow_decrease_1/2`, green or red text, and `LocalisedTextWithIcon`. Otherwise `UnitRecordContext.Description` in `body_12_italic`.
5. **Health bar**: 220×24 frame, 212×16 fill coloured `alliance_player` `#A2EC17`, a barrier sub-bar in `magic_barrier` `#82E1E1`, and a numeric HP value with icon (`GetIfElse(IsKnownHp, HitPoints, "??")`). Comparison badge `Format("%+d", …)` is green or red.
6. **Top bar**: XP rank icon, kills, upkeep (`ContextNumberFormatter => UpkeepCost` + `icon_income`), tier icon (states 1–5, `unit_tier_N.png`), and men count `Format("%d (%d)", NumEntities, NumEntitiesInitial)`. That last one has states `large`/`small` from `IsLargeEntity` with `icon_entity_large`/`icon_entity_small`, and the `tooltip_entity_info` layout. **This is how "large" is shown.**
7. **"Stats" header**, then `ContextList => StatList` of `templates/stat_entry` rows. Each row is 260×24:
   - x=-2: icon 22×22 (`CcoUnitStat.Icon`).
   - x=22: name 156 px (`Name.RemoveTextTags`, `ui_font_faded_grey_beige`, green or red if modified).
   - x=156: modifier icons 16×16 (`ModifierIconList`, e.g. `modifier_icon_shield`, AP, magical).
   - x=172: value, right-aligned, `ContextNumberFormatter => DisplayedValue` (clamped).
   - x=219: bar 40×8. Base fill `#FFCC4B`; modifier fill `green` or `red` = `GetIfElse(Value > ValueBase, …)`; frame 48×14.
   - Comparison badge `label_compare` 46×28 in `alliance_player` or `alliance_enemy` colours, plus a comparison tick placed at `ComparisonValue / MaxValue`.
   **Bars and numbers are shown together, and base and modified values are shown by overlaying the two fills.**
8. **"Abilities" header**, then categories. `AbilityDetailsList.FirstContext.CategoryStateList` gives the category states `abilities`, `additional_stats`, `attributes`, `passives`, `resistances`, `spells`. Each category is a 250×54 block with an orange `body_12_bold` title (`ui_font_orange` in the character panel) and 250×30 rows (28×28 icon in `ability_icon_frame_small` + name). **Resistances, ward save and "additional stats" are rendered as ability-like rows in their own categories, not in the stat bar list.** A compact icon grid (`itemsperrow=9`, 28×28, 1 px spacing) is used when collapsed.
9. Agent sub-panel (`agent_information`) for heroes, and a training-slot lore list (`PossibleAbilityGroupList`) with ability group name + icons.

**DB cross-check (twwiki.duckdb):**
- `ui_unit_stat_to_classes` (172 rows, 16 unit classes). Every class checked (`inf_mel`, `inf_mis`, `cav_mel`, `art_fld`, `com`) uses the same `list_order`: 0 `stat_health`, 2 `stat_armour`, 3 `stat_morale`, 4 `scalar_speed`, 5 `stat_melee_attack`, 6 `stat_melee_defence`, 7 `stat_weapon_damage`, 8 `stat_charge_bonus`, 9 `stat_ammo`, 10 `scalar_missile_range`, 11 `stat_missile_damage_over_time`. Columns `filter` (`none`/`melee`/`ranged`/`naval`) and `base_value` exist too.
- `ui_unit_stats` (50 rows): `icon` (e.g. `ui/skins/default/icon_stat_armour.png`), `max_value` (armour 180, leadership 120 with `min_value` -55, speed 140, melee attack 100), `clamp_displayed_minimum`/`clamp_displayed_maximum`, `campaign_only`.
- `ui_unit_stat_to_unit_castes` (23 rows): bar maxima by caste, e.g. `stat_weapon_damage` 800 for lord, hero and monster; `stat_charge_bonus` 150 for lord and hero.
- Stat names: `unit_stat_localisations_onscreen_name_<stat>` already embed the icon (`[[img:ui/skins/default/icon_stat_armour.png]][[/img]] Armour`). Tooltips: `unit_stat_localisations_tooltip_text_<stat>`.
- Bullet points: `ui_unit_bullet_point_enums` (223 rows: 206 positive, 13 negative, 3 very_positive, 1 very_negative; `sort_order`, `icon_path`), `ui_unit_bullet_point_unit_overrides` (7,485 unit→bullet rows), loc `ui_unit_bullet_point_enums_onscreen_name_<key>` / `…_tooltip_text_<key>` (e.g. "Anti-Large").

**Mismatch with our Unit page** (`web/src/components/pages/UnitPage.astro`): Base stats are listed as Men, HP/entity, MA, MD, CB, Armour, Leadership, walk/run/charge speed… with no bars, no icons and no per-caste maxima. Resistances and ward save are mixed into "Base stats", and bullet points are absent.

**Unit card** (`common ui/land_unit_card.twui.xml`, 60×130; recruitment item 81×184 with a 66×136 card; custom battle 60×130 or small 45×100/108):
- Image stack in `card_image_holder`, bottom to top:
  1. `unit_card_background.png` (60×130).
  2. The unit icon.
  3. `mask_unit_tertiary` (overlay shader).
  4. `unit_card_back_overlay.png`, tiled, `#FFFFFF32`, margin 0,10,0,10.
  5. `mask_unit_primary` and `mask_unit_secondary` (faction colour masks).
  6. `unit_card_recruitment_frame.png`, 9-slice with margin `0,20,0,20`.
- `hover` applies `brighten_t0` 1.0; `selected` applies `brighten_t0` 1.5 plus `unit_card_selected.png`; `inactive` and `locked` apply `set_greyscale_t0`, with a `#C0C0C0` tint when locked.
- Overlays: category semicircle `unit_card_semicircle[_renown|_crafted|_chieftain|…].png` 36×36 holding the 22×22 category icon, XP chevrons 24×24, 52×14 health bar, ammo bar in `orange`, spell-slot dial, upkeep/cost banners.
- Custom battle cards add a cost label on a `#00000096` strip.

### 2. Character details, skills, items, traits

**Panel frame** (`campaign ui/character_details_panel.twui.xml`, 1600×900):
- Name plate `header_16` and subtype `dy_subtype` `header_14`: **name plus subtype disambiguates duplicate names**.
- Tabs (300×103 `square_large_text_tab_toggle`): Details, Skills, Vows, Fragments, Quests, Initiatives, and more, each loading a sub-layout.
- Right column `stats_effects_holder` 300×690, containing:
  - "Character Stats": health bar plus the same `stat_entry` list, with name and value states `green`/`red` against `PreBonusStatContext.Value` (skill preview).
  - "Abilities": categories as above.
  - "Details, Traits & Effects": type, loyalty (icon states 0–2), office, army upkeep, activity, location with flag.
  - "Traits": 276×48 rows; the trait bar is a HorizontalList of 22×16 pips with fill states `-3…3` and `trait_frame_current` on the current level.
  - "Battle Effects" and "Campaign Effects" lists.
- Footer: skill points `Skill Points:` + a `header_18_bold` number, reset buttons, and a rank tooltip showing the Character, Battle and Campaign skill split (`ui_font_yellow`, `red`, `alliance_ally`).

**Skill tree** (`character_details_panel_skills.twui.xml`, 1270×700, horizontal scrolling):
- `list_box` HorizontalList with `itemsperrow=10`, a 20 px top spacer, then **six rows** `chain0`…`chain5`. Row height is 90 (70 for the last); `chain0` has a left margin of 242.
- DB: `character_skill_nodes.indent` 0–5 (visible nodes) = row; `tier` 0–12 (a few to 30) = column. `metadata.json` describes `Tier` as "y grid position" and `Indent` as "x grid position", the opposite of how the panel is filled; see Open questions.
- Inside a row: `SkillChain`, HorizontalList with **56 px spacing**. Each node is `template_skill_entry` 185×65, preceded by an `arrow` 56×33 (`parchment_divider_arrow.png`, alpha `#FFFFFF80` when inactive).
- `template_module` 21×60 is a vertical `parchment_divider` with an optional outgoing arrow. It separates groups of nodes in a row.
- **No vertical or diagonal prerequisite lines exist.** Cross-row requirements show only as lock states, the tooltip, and `SkillLevelPip`.
- **Card 185×67** states: `available`, `hover`, `complete`, `complete_hover`, `maxed`, `maxed_hover`, `researching`, `locked`, `locked_rank`, `locked_auto_unlock`, `locked_upgrade_rank`.
  - Background: `skills_tab_active` (available) or `skills_tab_selected` (allocated), plus ornament `skills_tab_ornament` 220×67.
  - Skill icon 72×72 docked left (dock offset -59,-3).
  - Label `dy_skill`: **112×44, centred, word-wrapped, `body_12` + `text_outline_t0`**, grey `ui_font_inactive_grey_light` when locked. The layout's sample text is the long Spanish name "Ecantamiento de la Tomenta de Craneos de Sakhmet", so the box is sized for two to three lines.
  - `level_parent`: vertical list of 3 pips 16×20 (spacing -4): `skills_tab_level_off`/`_lit` (brightened ×5)/`_over`, and `icon_padlock` in the `locked_rank` state.
  - Locked states grey out everything (`set_greyscale_t0`). `locked` adds `padlock.png`; `locked_rank` adds `skill_locked_rank.png` (135×72 overlay); `locked_auto_unlock` adds `skill_auto_unlock_rank.png` 30×30; `locked_upgrade_rank` adds `skill_upgrade_locked_chains.png` with a glow pulse.
  - `type_icon` 24×24 (active or inactive) marks the skill type.
- Tooltip `campaign ui/edict_tooltip` (392 px): rarity-styled title (`tooltip_title_common|uncommon|rare|legendary|crafted`), italic description, effect rows 379×26 with 24×24 icon, granted ancillaries, unit card mini list (10 per row).
- **Rank bands**: the game has no band graphic. Rank gating is a per-card state, and `CcoCampaignCharacterSkillLevelDetails.RankRequired` gives the rank per level; DB `character_skills.unlocked_at_rank`. A planner can draw bands, but it can't copy them from the game.
- Also in the panel: skill search box (350×35) and an auto-management checkbox.

**Items and mounts** (`character_details_panel_details.twui.xml`):
- The equipment list is `CcoAncillariesCategoryRecord.RecordList.Filter(IsHidden == false && Category != "general" && Category != "mount").Sort(SortOrder, true)`.
  - DB `ancillaries_categories`: armour 0, weapon 1, mount 2, talisman 3, enchanted_item 4, arcane_item 5, general 6, form 7 (hidden). Icons `equipment_items_<type>`.
- Mount is a separate block ("Mount", `db_key="mount"`) with a dropdown (`Loc("no_mount")` when empty). The option row shows the bodyguard upkeep difference `ProvidedBodyguardUnitContext.Upkeep - …UnitRecordContext.Upkeep`.
- Slot frame 77×79 with states `common`, `uncommon`, `rare`, `legendary`, `crafted`, `default`, `round` (`AncillaryRecordContext.FrameState`); icon 77×79 with a `round` icon state.
- Item picker rows 500×86: name `header_14` + `(RarityName)` + upkeep, italic `ColourText` description, "assigned to" portrait 23×37, unique padlock.

### 3. Technology tree

`campaign ui/technology_panel.twui.xml`:
- **Tabs**: `TechnologyList.Transform(UiTabContext).Distinct.Sort(SortOrder, true)`. DB `technology_ui_tabs.sort_order` and `tier_offset` (26 rows); tab image `tech_tree_tab_<key>.png`; per-tab turns banner and search-hit count.
- **Tree**: `TreeCallback => TechnologyTree(tab)` with `scale_tree`. Nodes are placed by DB `technology_nodes.tier` (0–29), `indent` (-2…9), `pixel_offset_x` (-1350…500) and `pixel_offset_y` (-100…120).
- **Node** `template_slot_entry` 230×61, `technology_entry` 230×67. States: `available`, `hover`, `complete`, `complete_hover`, `researching`, `locked`, `locked_rank`, `locked_upgrade_rank`, `maxed`, `query_matched`.
  - Label `dy_tech` 137×44, centred, wrapped, outline shader.
  - Check mark 56×56 when researched.
  - `dy_time` 50×24 on `turns_banner.png`. `Duration` is shown only when `Duration != 0 && (CanResearch || IsResearching || IsQueued)`.
  - Costs, shown only when not researched or researching: `dy_cost` (treasury icon; state `cant_afford` when `Cost > TreasuryAmount`), `dy_pooled_res_cost`, `Food`.
  - Requirement icons 24×24: `icon_building_required` (from `RequiredBuildingList`), `dy_resource_icon`. Yin/yang harmony icon. Agent training portraits 28×27.
- **Links** (`branch_parent`, `CcoTreeLink`): segments `template_branch_horizontal` 117×13 (`parchment_divider_length.png`), `template_branch_vertical` 13×78 (`parchment_divider_height.png`), and `template_branch_end` arrowheads 15×13 (states `top|bottom|left|right` × `_active|_inactive`).
  - A link is active when `ParentContext.IsResearched && ChildContext.IsAtLeastResearching`.
  - Multi-parent badge `Format("%d/%d", ResearchedParents, RequiredParentsNumber)` 21×24 with a green check. In the main tree it is kept only for `wh_main_dwf_dwarfs`.
  - DB `technology_node_links`: `parent_link_position`/`child_link_position` (side codes 0–4; the most common pair is 2→4, 684 rows), `…_offset`, `initial_descent_tiers`, `visible_in_ui`. `technology_nodes.required_parents`.
- **UI groups** (`TechnologyUiGroupList`): each is a 250×136 background resized to span its corner nodes (`LeftMostTechnology`/`RightMostTechnology`/`TopMostTechnology`), tinted, with an optional watermark image (`BackgroundImage`) and a name banner `header_14` on `reward_flyer.png`. It greys out when all techs in the group are researched.
  - DB `technology_ui_groups` (key, `optional_background_image`, `colour_hex`; 128 rows) and `technology_ui_groups_to_technology_nodes_junctions` (`top_left_node`, `bottom_right_node`, optional TR/BL; 120 rows).
- **Header**: "Research Rate:" `Format("%d", TechnologyResearchPoints)`, treasury, pooled resources used by techs, research point surplus.
- **Tooltip** (`tech_tooltip_context`, 340 px) sections in order:
  1. Title (`header_14`).
  2. Red "required resources" warning.
  3. "Disabled by: X".
  4. Required buildings (red).
  5. Required parent technologies (`technology_x_required` "N required").
  6. Additional required techs.
  7. Script lock reason.
  8. Italic description (`RecordContext.ShortDescription`).
  9. Ancillaries (`GrantedText`).
  10. Effects (`LocalisedText` + icon).
  11. Traits.
  12. Upgraded initiatives (`{{tr:upgrades_initiative}} %S`).
  13. Unit cards "units affected" (`UnitsFromEffectNotExcluded`, 8 per row).
  14. Additional details box.
- Cost breakdown tooltip: `tooltip_technology_cost_breakdown`.

### 4. Building browser and settlement panel

`campaign ui/building_browser.twui.xml`:
- **Columns** are building sets for the selected settlement or horde (`SelectedSettlement.BuildingSetList`). Each column (`template_category`) has a `category_label` coloured by `CcoBuildingSetRecord.Colour`, a `chain_background` (states `city_chain`/`locked`/`unlocked`) and a `chain_list`.
- **Chains within a set**: HorizontalList with **45 px spacing**, `sort_func=OptionalSortOrder`.
- **Levels within a chain**: a vertical List of `building_frame` **74×74** slots (64×64 in the settlement slot view).
- The "current level" break bar is placed at `106 * MaximumChainColumn + 29` horizontally and `106 * Level` vertically, which implies a **106 px pitch per level and per chain column**.
- Cyclic (Nurgle lifecycle) chains use a `RadialList` (radius `20 * MaximumChainBuildings`) with a circular fill band.
- Tier badge `tier_label` 52×40 (`OptionalTierIcon`, default `building_tier_city_empire.png`) is shown on the first level and whenever the primary slot requirement changes. That makes it **effectively a settlement-tier band marker**. Level numeral 16–20 px `settlement_silver_numeral_N.png`.
- **`building_frame` template (74×74)**:
  - Square or circular button with states `built`, `built_inactive`, `built_panel`, `cannot_build_ever`, `empty`, `greyed`, `hover`, `locked`, `normal`, `not_owned`, `selected`, `unknown`.
  - Category frame `building_type_frame.png` with a secondary overlay.
  - Damaged bar 4×30; constructing animation (12 frames).
  - `turns_center` / `turns_corner` banners.
  - Requirement icons: `tech` (`IsLockedByAnyTech`, `icon_technology_required`) and `resource` (red tint, `ResourceRecordContext.IconFilepath`).
  - Duplicate-in-province icon; unlocks-tech icon; development points.
  - Cost list (`CreateCost(…)` treasury, pooled resource), states `normal`/`red`.
  - **Unit mini-cards 23×50** (`UnitList(settlement, faction)`, overlapping −10 px, max 60 px wide; state `active_red` if an additional building is missing) and agent cards.
- **Footer**: culture panorama (`CultureContext.UiBackgroundImage`); settlement list 204×190 with slot grid (`BuildingSlotList.Filter(Index < MaxBuildingSlotCount)`, `template_layout=ui/campaign ui/settlement_building_slot`); ally/foreign-slot views; growth, income and slaves boxes.
- **Building tooltip** (`building_information`, 400 px): title `header_14` + skull separator, then:
  - building image 108×76 in a category-coloured frame + level numeral;
  - **secondary title = chain name** (`dy_secondary_title`, `ui_font_faded_grey_beige`), which disambiguates same-named levels;
  - food cost line;
  - italic description;
  - effects list;
  - instruction box.
  `building_info_recruitment_effects` shows "Unlocks recruitment of:" rows 350×50 with name, 26×26 category icon, XP rank and garrison size.

### 5. Effects and tooltips

- **Effect row templates**:
  - `templates/effect_entry`: 300×30, icon 24×24 top-left, text at x=26, `body_12`, greyscale state `inactive`.
  - Tooltip rows: 26–30 px tall.
  - Text is always `CcoEffect.LocalisedText`, the fully formatted string (value substituted into `effects_description_<key>` plus the scope suffix).
  - The icon goes through the `AbilityEffectIcon` callback, which picks the positive or negative icon and background (`construction_positive.png`, `effect_icons_bg_white_image.png`).
  - `tooltip_context_effect_list` additionally sets `ContextColourSetter => SupplementColour` and splits effects into normal and `IsInCategory("info")` groups under a divider.
- **Polarity data**: DB `effects.is_positive_value_good` (12,299 of 15,064 true), `effects.icon` / `icon_negative`, `priority`. Per `metadata.json`, `CcoEffect.Priority` is "used for ordering and if 0 isn't shown in UI" (1,339 effects have priority 0) and `IsPositive()` is available.
- **Colour inside effect text**: some descriptions carry their own tags, e.g. `Maintenance cost: [[col:red]]%n[[/col]]`. Most don't, so the positive or negative cue comes from the icon, and in breakdown rows from `value` states `positive`/`negative` with the `red` preset.
- **Scopes**: the scope suffix comes from loc `campaign_effect_scopes_localised_text_<scope>`, e.g. `army_to_army_own` → `\\n([[img:icon_general]][[/img]]Lord's army)`, `agent_to_parent_army_own` → `\\n([[img:icon_hero]][[/img]]Hero's army)`. Some scopes have **empty** text (`army_to_army_enemy`, `army_to_army_own_unseen`), meaning no suffix. There are 435 scope records; `CcoCampaignEffectScopeRecord.LocalisedText` exists.
- **Effect bundle tooltip** (`tooltip_effect_bundle`, 440 px): title with rarity states → "Turns remaining: N" (only if ≥1) → italic description → optional pooled-resource threshold requirement → effect list.
- **Ability tooltip** (`common ui/special_ability_tooltip`), rows in order:
  1. Header with name, wind cost (`ManaUsed > 0`) and shortcut.
  2. Source type, lore, "Active Ability" type, uses.
  3. Phase and projectile block: damage, AP %, flaming or magical icons, explosive damage, number of projectiles.
  4. Detail rows (190 px label + value): **Range** (hidden if 0, ∞ icon if <0), **Effect range** (same rules), **Spread range** (>0), **Duration** (`IsPassive || ActiveTime > 0`; ∞ icon when `ActiveTime <= 0`), **Cooldown** (`RechargeTime > 0`), **Shared cooldown**, **Miscast chance** (>0, `ui_font_blue_light`), Can target, Affects.
  5. Valid-use block: Affected units, Affects units if, Enabled if, Can use if, Recharges if.
  6. Additional UI effects (green).
  7. Form (transform) portrait.
  8. Italic description.
  9. Click hints.
  Phase stats use `Format("(%d%S)", Duration, Loc("seconds_abbreviated"))` or an infinity bracket.
- **Trait tooltip** (340 px): title → italic flavour → explanation → effects → "units affected" card list → attribute box (`BulletText.ParseTextReplacements.Replace("||", " ")`) → ability tooltip.
- **Item tooltip** (`tooltip_ancillary_record`, 446 px): rarity title (`OnscreenName + …`) → italic `ColourText` → effects → ability tooltip. Armory items (daemon gifts) use a banner per item type and a set name.

### 6. Army and recruitment

- **Army size**: no army panel hard-codes the unit limit. `MilitaryForceContext.UnitCount` is used, and the only literal `"/20"` is in `augment_panel` (Throt). The limit is engine or campaign data, not layout.
- **Custom battle** (`frontend ui/custom_battle`) is the game's own army builder:
  - Roster background `unit_list` states **`5`, `7`, `10`, `20`, `40`** (and `_small`); reinforcements add `8`, `12`, `16`. `unit_card_slot.png` marks empty slots.
  - "Funds remaining" label `FundsRemaining(true|false)`, greyed when negative.
  - Unit pool grouped by `CcoUiUnitGroupParentRecord` (DB `ui_unit_group_parents`: commander 1, hero 2, infantry 3, missile infantry 4, cavalry 5, missile cavalry 6, monsters 7, constructs / flying war machines 8, missile monsters 9, artillery 10, campaign exclusives 99; `mp_cap` column present).
  - Collapsible headers with a group icon; cards 45×108; cost label greyed when `Cost > FundsRemaining`; search filter.
  - Per-unit mount radio buttons with cost (`CanAffordMount`) and upgrade checkboxes with cost (`CanAfford`).
  - `MaxUnitsCanRecruit(TeamIndex)`, `MaxUnitsCanReinforce`.
- **Campaign recruitment** (`units_panel`, `recruitment_item` 81×184):
  - Header states: `Recruitment Options`, `Available Mercenaries`, `Renown`, `Raise_dead`, `Blessed`, `Elector`, `Imperial`, `Satrapy`, `Horde`, `Client`, `allied_recruitment`, `nurgle_mercenaries`.
  - Capacity pips 18×25 (`local_capacity_entry` states `local`/`camp`/`foreign_slots`/`military_force`; `global_capacity_entry`; available and other variants).
  - Per card:
    - `Turns` 78×18 (states `blocked`, `general`, `settlement`);
    - `max_units` banner (states `normal`, `red`);
    - `unit_cap` / `unit_cap_global` **"2/4"** (red when at cap);
    - `UpkeepCost` and `RecruitmentCost` 70×18 banners, each with a 24×12 up or down arrow `upkeep_modified_icon` (`unit_effect_positive`/`negative`) when modified;
    - food cost, favour cost, cooldown, `merch_type` (`battle_site`, `client`, `faction`, `horde`, `province`, `satrapy`), mercenary `replenishment_chance` "41%".
  - Cap source: `PlayersFaction.UnitCapForUnit(UnitRecordContext)`.
- **Mercenaries**: `tooltip_mercenary_info` breaks availability down by source (Buildings `ui_font_yellow`, Battle site `red`, Character `alliance_ally`) → "Total units available". Pools: `AvailableUnitCount`; `HasInfiniteUnitCount` → blank count; state `depleted` when 0.
- **Regiments of Renown**: `unit_cat_frame` state `renown` (semicircle `unit_card_semicircle_renown.png`), header state `Renown`, and a big `button_hire_renown` 268×51 with glow.

### 7. Encyclopedia or compendium

`common ui/spell_browser.twui.xml`, titled "Unit & Spell Browser" (1600×900; reachable from menu bar, battle HUD, custom battle and campaign select):
- **Units tab**:
  - Race strip 1600×100 (`CultureRecord.StripLargeImagePath`) with name.
  - "Select Race" dropdown: `CultureRecord.RecordList.Filter(GroupedUnitList.IsEmpty == false).Sort(Name, true)`, 3 per row, 250×50.
  - Left 880 px: `GroupedUnitList(true)` in **2 columns**. Each group is a 425×39 collapsible header (group name + icon) over a roster of **45×100 cards, 9 per row, 2 px gaps**, using the same card image stack as the game.
  - Right 610 px: embedded **unit_information** panel (290 px) next to a scrolling historical description (`UnitContext.HistoricalDescription`, `ui_font_faded_grey_beige`).
- **Spells tab**:
  - Left 460 px: lore list `CcoSpecialAbilityGroupRecord.RecordList.Filter(IsCompositeGroup == false && AbilityList.Size > 0 && IsContextValid(ParentLoreContext) == false).Sort(SortOrder, true)`. Entries are 200×50 with a 56×56 icon, **tinted by the lore's `Colour`** (DB `special_ability_groups.colour_hex`, `sort_order`).
  - Middle: 580×327 video preview (`VideoName`) plus the full ability tooltip. A toggle shows the "upgraded" (overcast) spell.
  - Spell buttons 250×62 with 59×59 icon, 2 per row.
- A generic `help_panel` also exists (help pages via `[[sl:…]]` links).

---

## Visual system

### Named colours: game vs our theme

Source: DB `ui_colours` (column `unnamed colour group_1`). Text presets are applied via `font_colour_override_preset_key` and image tints via `ui_colour_preset_type_key`. Default text colour for almost all text (20,585 of 20,700 text blocks) is `#FFF8D7` (= `fe_white`).

| Tag / preset | Uses in loc `[[col:]]` | Game hex | Our `theme.css` | Note |
|---|---:|---|---|---|
| red | 1,649 | `#FF2D2D` | `--col-red #d9644a` | ours is muted orange-red; acceptable on dark background, hue differs |
| yellow | 1,549 | `#FFB900` | `--col-yellow #e8c547` | game is amber-orange |
| green | 854 | `#A0FF37` | `--col-green #8fc26a` | game is lime |
| magic | 140 | `#41E1E1` | `--col-magic #7fb3e8` | **wrong hue**: game is cyan |
| white | 80 | `#FFFFFF` | `#f4efe4` | close |
| subtitle_* (22 names) | ~170 | e.g. belakor `#CEC0C0` | missing | rendered with no colour class |
| fe_white (+ overridecol) | 37 | `#FFF8D7` | `#f4efe4` | our base `--text #e8dcc2` is darker than the game's |
| dark_r | 21 | `#AA0000` | missing | dark red; lighten for a dark theme |
| link | 10 | `#B95C00` | missing | hyperlink colour (also `link_mouseover #C86B0F`, `link_visited #A87A54`) |
| blue | 5 | `#2D2DFF` | missing | too dark on our background |
| ancillary_crafted / unique / rare / uncommon | 4 / 3 / 2 / 1 | `#808000` / `#4B096F` / `#1C6BA7` / `#246E00` | only unique = `#d68ce0` | game values marked "placeholder" in the DB and too dark for us; keep lightened variants but match hue |
| fabulous_pink | 3 | `#F33BFF` | missing | |
| orange, fatigue_tired, fatigue_winded | 3 each | `#FFAD5B` | missing | |
| dark_y / magic_barrier | 1 / 1 | `#8C8C00` / `#82E1E1` | missing | |
| `%s` | 9 | – | – | runtime-filled colour; treat as uncoloured |

Other UI presets worth having as tokens:
- `ui_font_faded_grey_beige #A99F89` is the game's "muted" colour, used 1,436 times (our `--muted #a8925f` is more yellow).
- `ui_font_inactive_grey #666666`, `ui_font_inactive_grey_light #C0C0C0`, `ui_font_yellow #FFD700`, `ui_font_orange #FC8A23` (ability category titles), `ui_font_blue_light #41E1E1`.
- `alliance_player #A2EC17` (health, positive comparison), `alliance_enemy #FF2D2D`, `alliance_ally #68CEFF`.
- Rarity: `common #66FF00`, `rare #00C6FF`, `epic #A600FF`.
- `threat_low / medium / high #6AA924 / #FFAD5B / #C41400`.

Colour-blind overrides exist for `red`, `green`, `alliance_*` and `dip_attitude_*` in the profiles `deuteranopia`, `protanopia` and `tritanopia` (e.g. deuteranopia green `#CEABCB`, red `#B34E30`). `ui_main_theme_options` holds 8 selectable theme accents (default `#F33BFF`).

**Text tags in loc** (occurrences): `img` 13,982; `col` 8,778; `sl` 7,761; `url` 1,926; `tooltip` 992; `sl_tooltip` 853; `i` 803; `b` 241; `sl_link` 170; `fragment` 32; `overridecol` 23; `opacity` 20. Tokens: `{{tr:}}` 18,757 (already substituted in `twwiki/model/text.py`), `{{tt:}}` 498, `{{CcoCampaignEventIncident:…}}` 354 and other Cco tokens. **`gameText.ts` only understands `b`, `i`, `sl`, `col`, `overridecol` and `img`.**

### Fonts

From `ui/fontcategories.xml`. Default font `la_gioconda`, default colour `#FFF8D7FF`, leading 3. Actual glyphs are proprietary bitmap `.cuf` files in `font/`; don't ship them.

| Category | Face | Size | Use count in layouts |
|---|---|---:|---:|
| body_12 | la_gioconda | 12 | 15,479 |
| body_10 | la_gioconda | 10 | 1,660 |
| header_14 | brand_header | 14 | 1,201 |
| header_16 | brand_header | 16 | 680 |
| body_12_italic | georgia_italic | 12 | 342 (all descriptions and flavour text) |
| header_18_bold / 24_bold / 16_bold / 20 / 38 / 70 | la_gioconda_uppercase | 18/24/16/20/38/70 | 323 / 230 / 172 / … |
| header_12 / header_18 | brand_header | 12 / 18 | 188 / 64 |
| body_12_bold | la_gioconda | 12 | 74 |
| body_alternative_12, header_alternative_16/18/24 | Calligraph421 | 12–18 | 63 |
| grudges_* | Norse / Norse-Bold, colour `#4A0000` | 14–38 | Book of Grudges only |

Pattern: serif body at 12, **italic serif for descriptions**, small-caps/uppercase serif for panel titles, and a display face for entity names. Ours: `--sans` system-ui for body and Georgia for headings. The game uses a serif for body text too, and italic for descriptions. A dyslexic font set (`dyslexic_font_*`) exists as an accessibility option.

### Standard sizes

| Element | Size (px) | Source |
|---|---|---|
| Unit card (campaign/battle) | 60×130; browser/custom small 45×100 or 45×108; building mini-card 23×50; tooltip mini-card ?×69 | land_unit_card, spell_browser, building_frame, edict_tooltip |
| Unit category icon | 22×22 in 34–36 round frame | unit_information, land_unit_card |
| Stat row | 260×24; icon 22; name 156; value at x=172; bar 40×8 (frame 48×14); modifier icon 16 | templates/stat_entry |
| Ability icon | 28×28 (frame `ability_icon_frame_small`); ability row 250×30; category block min 54 tall | unit_information |
| Effect icon / row | 24×24; rows 26–30 tall, 300–440 wide | effect_entry, tooltips |
| Unit info panel | 290 wide (character panel 300) | unit_information |
| Tooltip widths | 340 (tech, trait), 346 (rank/merc), 392 (skill/edict), 400 (building), 440 (effect bundle), 446 (item) | various |
| Skill card | 185×67; icon 72×72; label 112×44; pips 16×20 ×3; arrow gap 56; row pitch 90 | character_details_panel_skills |
| Tech node | 230×61–67; label 137×44; turns 50×24; check 56×56; link segments 117×13 horizontal, 13×78 vertical, arrowheads 15×13 | technology_panel |
| Building slot | 74×74 (browser), 64×64 (settlement); level/chain pitch 106; chain spacing 45; level numeral 16–20 | building_browser, building_frame |
| Item slot | 77×79; picker row 500×86 | character_details_panel_details |
| Capacity pip | 18×25 | units_panel |
| Tab button | 300×103 (large), 118×108 (tech tab) | character_details_panel, technology_panel |

### Icon backgrounds and frames

- **Unit cards** always sit on `unit_card_background.png` under a 9-slice frame (`unit_card_recruitment_frame.png`, `unit_card_frame_plain.png`) with faction colour masks. Hover brightens (`brighten_t0`), locked or inactive goes greyscale.
- **Ability icons** are wrapped in `ability_icon_frame_small.png` and tinted `#F0F0F0`.
- **Effect icons** sit on `effect_icons_bg_white_image.png` or `construction_positive/negative.png`.
- **Items** sit on `equipment_items_frame[_rarity].png`.
- **Skill icons** sit on a parchment tab `skills_tab_active/selected.png`.
- **Buildings** sit in `building_type_frame.png` tinted by building-set colour.
- **Tooltips** use `tooltip_frame.png` (9-slice) with a rarity title bar `tooltip_title_<rarity>.png`.
- Rows use `selectable_non_button_hover_gradient.png` at `#FFFFFF32` for hover.

**Why our cards vanish**: the icons are dark, fully opaque paintings intended for a lighter, framed card. Our `.game-img-card` (60×130) has no background, border or lift.

### Mismatches with `theme.css` / `gameText.ts`

1. `KNOWN_COLOURS` covers 7 of 44 names in use. `magic` is the wrong hue. `subtitle_*`, `dark_r`, `link`, `orange`, `fabulous_pink` and the rarity colours are missing.
2. `--text #e8dcc2` vs game `#FFF8D7`; `--muted #a8925f` vs `#A99F89`.
3. Unknown tags (`url`, `tooltip`, `sl_tooltip`, `sl_link`, `fragment`, `opacity`, `tt`) print as literal `name:arg`, and their closers pop the wrong span.
4. `{{tt:…}}` and `{{Cco…:…}}` print their inner key.
5. Descriptions aren't italic (the game uses `body_12_italic` + faded beige for every description and flavour text).
6. Unit card images have no frame or background.

---

## Data hints

Record fields and functions the game displays, with the DB column to use where it maps directly:

| UI element | Expression | DB / loc source (verified where marked ✔) |
|---|---|---|
| Stat list order, icon, bar max | `CcoUnitStat.SortOrder/Icon/MaxValue/MinValue/DisplayedValue` | `ui_unit_stat_to_classes.list_order` ✔, `ui_unit_stats.icon/max_value/min_value/clamp_*` ✔, `ui_unit_stat_to_unit_castes.max_value_override` ✔ |
| Stat name / tooltip | `Name.RemoveTextTags`, `Tooltip` | `unit_stat_localisations_onscreen_name_<stat>` (contains `[[img]]`) ✔, `…_tooltip_text_<stat>` ✔ |
| Bullet points | `BulletPointList`, `State`, `SortOrder`, `LocalisedTextWithIcon` | `ui_unit_bullet_point_enums` ✔, `ui_unit_bullet_point_unit_overrides` ✔ |
| Unit category label / icon | `UnitRecordContext.CategoryName/CategoryIcon/CategoryTooltip/SpecialCategoryKey` | `ui_unit_groupings` (icon, parent_group) ✔, loc `ui_unit_groupings_onscreen_<key>` ✔ |
| Unit group headers (browser, custom battle) | `CcoUiUnitGroupParentRecord.OnscreenName/Icon` | `ui_unit_group_parents` (`order`, `icon`, `mp_cap`) ✔ |
| Men count, large | `Format("%d (%d)", NumEntities, NumEntitiesInitial)`, `IsLargeEntity` | land unit num_men, entity size |
| Tier icon | `UnitRecordContext.Tier` → `unit_tier_N.png` (1–5) | main_units tier |
| Unit cap | `PlayersFaction.UnitCapForUnit(UnitRecordContext)` | `main_units.campaign_cap` (our page already hides `-1`) |
| Equipment slot order | `RecordList.Filter(IsHidden == false && Category != "general" && Category != "mount").Sort(SortOrder)` | `ancillaries_categories.sort_order/hidden` ✔ |
| Item frame | `AncillaryRecordContext.FrameState`, `RarityName` | ancillary rarity (open: exact column) |
| Skill grid | `Tier`, `Indent`, `TotalLevels`, `RankRequired` | `character_skill_nodes.tier/indent/visible_in_ui/required_num_parents` ✔, `character_skills.unlocked_at_rank` ✔, `character_skill_node_links.link_type` (`REQUIRED` 10,470 / `SUBSET_REQUIRED` 10,120) ✔ |
| Tech grid / links / groups / tabs | `Tier`, `Indent`, `RequiredParentsNumber`, `TechnologyUiGroupList`, `UiTabContext.SortOrder` | `technology_nodes.tier/indent/pixel_offset_x/y/required_parents` ✔, `technology_node_links.*_link_position(_offset)` ✔, `technology_ui_groups(+junctions)` ✔, `technology_ui_tabs.sort_order/tier_offset` ✔ |
| Effect text / icon / polarity / hidden | `LocalisedText`, `IconPath`, `IsPositive`, `Priority` (0 = hidden) | `effects.icon/icon_negative/is_positive_value_good/priority` ✔; loc `effects_description_<key>` with `%n`/`%+n` ✔ |
| Effect scope suffix | `EffectScopeContext.LocalisedText` | loc `campaign_effect_scopes_localised_text_<scope>` (starts with literal `\\n`, may be empty) ✔ |
| Lore list order and colour | `Sort(SortOrder)`, `Colour` | `special_ability_groups.sort_order/colour_hex` ✔ |
| Colour tags | `GetColour("red")`, presets | `ui_colours` ✔, `ui_colour_profile_colour_overrides` ✔ |
| Static labels | `textlabel` | loc `uied_component_texts_localised_string_<textlabel>` (10,214) ✔ |
| Tooltip layouts | `layout_path` | `ui_tooltips.layout_name`, `ui_tooltip_components` ✔ |

**Sentinel and label rules:**

| Value | Game display |
|---|---|
| Ability `NumUses < 0` | uses row hidden (`NumUses >= 0` shows `Loc("uses_x")`) |
| Ability `TargetRange` / `EffectRange` `< 0` / `== 0` / `> 0` | ∞ icon (`icon_infinity.png`, "map-wide") / row hidden / `N` + `Loc("metre_abbreviation")` |
| `SpreadRange`, `RechargeTime`, `MiscastChance` `<= 0` | row hidden |
| Ability `ActiveTime <= 0` (when shown) | ∞ icon; phase `Duration <= 0` → "(∞)"; `Duration < 0 && HpChangeFrequency > 0` → "every N seconds" |
| `ManaUsed == 0` | wind cost badge hidden |
| Tech `Duration == 0` or tech not researchable | turns banner hidden; `Cost == 0` hides the gold banner |
| Mercenary `HasInfiniteUnitCount` | blank count |
| Ammo unlimited | `icon_infinity` (`unlimited_ammo`) |
| HP unknown (fog of war) | "??" |
| Effect `Priority == 0` | effect not shown |
| Unit comparison deltas | `Format("%+d", …)`, green if higher, red if lower |
| Modifier value vs base | value and name coloured green or red, bar split into base (gold) and modifier (green/red) |
| Keys → labels | always via `Name`/`OnscreenName`/`LocalisedText` loc lookups. The one visible raw-key fallback is armory items: `GetIfElse(IsStringEmpty(Name), Key, Name)` |

---

## Usefulness and recommendations

| # | Finding | Wiki UI | Character planner | Army planner | Suggested change |
|---|---|---|---|---|---|
| 1 | Stat order, icons, bar maxima in `ui_unit_stat_to_classes` / `ui_unit_stats` / `…_to_unit_castes` | High | Medium | High | Model these three tables. Render unit stats in `list_order` with icon, value and a 40 px bar (base gold, modifier green/red later from the stat engine). Move resistances, ward save and misc stats into separate "Resistances" and "Additional stats" groups like the game. |
| 2 | Bullet points (`ui_unit_bullet_point_*`) | High | Low | High | Add `bullet_points` (key, state, sort_order, name, tooltip) to the unit model. Show them under the unit name with arrow icons and green/red text; use them as roster tags in the army planner. |
| 3 | `ui_colours` hex table (+ colour-blind profiles) | High | Medium | Medium | Generate `--col-*` CSS variables from `ui_colours` for every name used in loc. Lighten the very dark ones (`dark_r`, `blue`, `ancillary_*`) with a documented adjustment. Fix `magic` → cyan. Optionally add a colour-blind toggle using the overrides. |
| 4 | Unknown text tags and `{{…}}` tokens break `gameText.ts` | High | High | Medium | Treat `url`, `sl_link`, `sl_tooltip`, `tooltip`, `tt`, `fragment` and `opacity` as transparent spans (render children only; `opacity:0` → hidden). Only pop the stack for tags that pushed a span. Drop unresolved `{{tt:…}}`/`{{Cco…}}` tokens instead of printing them. Add tests with real loc samples. |
| 5 | Effect scope text, polarity, priority | High | High | Medium | Model: resolve `scope` → loc `campaign_effect_scopes_localised_text_*` (strip the leading `\\n`, keep `[[img]]`; hide if empty). Compute `good = (value > 0) == is_positive_value_good` and use it for icon (`icon`/`icon_negative`) and a green/red cue. Filter `priority == 0` from display (keep for the stat engine). |
| 6 | Sentinel rules (∞, hidden rows) | High | Medium | Medium | Encode the table above in one formatter (`effectText.ts` / `StatTable`): `-1` or `<0` → ∞ for ranges and durations, hide uses when `<0`, hide zero-valued optional rows, never print `-1`. |
| 7 | Unit card framing | High | Low | High | CSS: give `.game-img-card` a light parchment-toned background, a 1–2 px `--border-accent` frame with rounded top, subtle inner shadow and `filter: brightness(1.15)` on hover. Don't copy `unit_card_background.png`/frames into the site. |
| 8 | Skill tree geometry (rows = indent, columns = tier, chain arrows, no cross lines, rank lock states, 112×44 wrapped labels) | High | High | Low | Lay the tree out as 6 rows × up to 13 columns, horizontal arrows only inside a row, 3 level pips per node, greyscale + lock badge for rank-locked levels, and rank bands derived from `unlocked_at_rank`/level `RankRequired` (a planner addition; the game has none). Allow two-line wrapped labels instead of clipping. |
| 9 | Tech tree geometry (tier/indent + pixel offsets, elbow links with side codes, N/M parent badge, UI group rectangles, tabs by sort_order) | High | Low | Low | Use `technology_node_links` link positions to draw orthogonal elbows instead of straight lines. Show "N/M" on multi-parent nodes. Draw `technology_ui_groups` as tinted named boxes. Order tabs by `technology_ui_tabs.sort_order`. Show turns and cost badges on nodes. |
| 10 | Building browser (sets as columns, chains 45 apart, levels stacked, tier badges, unit mini-cards, chain name as subtitle) | Medium | Low | Medium | On building chain pages show the levels vertically with settlement-tier markers, unit unlock mini-cards and cost/turn badges. Use the chain name as the disambiguating subtitle on level pages. |
| 11 | Disambiguation cues (category + special category frame; character subtype; building chain; item rarity) | High | Medium | Medium | In search results and headers, add a secondary line: units → category + RoR/crafted/elector marker; characters → subtype; buildings → chain; items → rarity/category. |
| 12 | Equipment slot order (`ancillaries_categories`) and rarity frames | Medium | High | Low | Planner item slots in `sort_order` (armour, weapon, talisman, enchanted, arcane), mount separate, `general` (followers) separate. Rarity-coloured slot borders. |
| 13 | Custom battle builder (funds, slot counts 5/7/10/20/40, group caps, mount/upgrade costs) and recruitment card badges (cap "2/4", upkeep arrows, turns) | Low | Low | High | Army planner UX: roster grid of 20 slots (configurable), funds remaining, pool grouped by `ui_unit_group_parents` order, greyed unaffordable cards, cap badge "n/cap" in red when reached. |
| 14 | Unit & Spell Browser structure | Medium | Low | Medium | Culture index pages: units grouped by `ui_unit_group_parents` with card grids; lore pages ordered by `special_ability_groups.sort_order` and tinted by `colour_hex`. |
| 15 | `uied_component_texts_localised_string_*` labels | Medium | Medium | Medium | Use the game's own labels for section headings ("Stats", "Abilities", "Duration:", "Cooldown:", "Research Rate:") to match in-game wording and ease localisation. |
| 16 | Typography (serif body, italic beige descriptions, uppercase headings) | Medium | Low | Low | Render descriptions and flavour in italic `--muted` (`#A99F89`), consider a serif body stack, and move `--text` toward `#FFF8D7`. Use free fonts only. |
| 17 | Ability tooltip row order and conditions | High | Medium | Low | Order ability page rows like the game: type/lore/uses → damage/projectile → range, effect range, spread, duration, cooldown, miscast → targets → enabled/usage conditions → description. |
| 18 | `metadata.json` Cco API docs | Medium (dev) | Medium (dev) | Medium (dev) | Keep as an unpublished developer reference for mapping UI concepts to DB. |
| 19 | Layout sizes (card, node, row dimensions) | Medium | Medium | Medium | Record in curated notes as design references (relative proportions), not pixel-for-pixel. |

### Extract / curate / ignore

- **Add to the DB/model (tables already in `raw/`, just not modelled). This is the main recommendation:** `ui_unit_stats`, `ui_unit_stat_to_classes`, `ui_unit_stat_to_unit_castes`, `ui_unit_bullet_point_enums`, `ui_unit_bullet_point_unit_overrides`, `ui_unit_groupings`, `ui_unit_group_parents`, `ui_colours`, `ui_colour_profile_colour_overrides`, `ancillaries_categories`, `technology_ui_groups` (+ junctions), `technology_ui_tabs`, `technology_node_links` positions, `campaign_effect_scopes` loc, `special_ability_groups.sort_order/colour_hex`, and the `uied_component_texts_localised_string_*` loc subset.
- **Parsed JSON (small, generated, publishable as derived data):** `colours.json` from `ui_colours` (name → hex, plus the adjusted dark-theme value) feeding generated CSS. `stat_layout.json` (stat key → order, icon, min/max, caste overrides) derived from the DB, not from layouts.
- **Curated notes only (hand-written, in `docs/`):** node and card dimensions, state names, sentinel display rules, tooltip section orders, the tag list for `gameText.ts`. Short structural facts only, no copied layout content.
- **Raw copy, unpublished, optional:** `ui/metadata.json` (2 MB) and `ui/fontcategories.xml` as developer references under `raw/<build>/files/ui/`. Only worth it if the team will query them. Don't add the 824 `.twui.xml` files to the pipeline: they are 91 MB of heavily engine-coupled markup and the useful facts are captured above.
- **Ignore:** all images beyond what the model already has (especially frames and backgrounds, which are artwork), `3dui`, `effects`, Spine and `sprite_anims`, cursors, EULAs, loading-screen scripts, `.cco` macros (except as reading aids), `autocomplete.json`, `mock_default.json`, `coreutils.lua`, legacy binary layouts.

---

## Open questions

1. **Tier vs indent axes.** `metadata.json` describes `CcoCampaignCharacterSkill.Tier` and `CcoCampaignTechnology.Tier` as the y position and `Indent` as x. The skill panel, though, has 6 horizontal rows (`chain0…5`), matching `indent` 0–5 with `tier` 0–12. Checking one lord in game (or a screenshot) would confirm the skill orientation. For technologies, `tier` spans 0–29 and `indent` -2…9 with a horizontally scrolling panel, which suggests tier = column too, but `TreeCallback` is engine code.
2. **Ability category order.** The state list is stored alphabetically in XML (`abilities, additional_stats, attributes, passives, resistances, spells`); the real display order comes from `CategoryStateList` in engine code. Is there a DB table for it (e.g. ability type / UI category with a sort order)?
3. **Which stats are "additional stats" and "resistances".** They appear as ability-detail categories, not `StatList` rows, so the source mapping (physical/missile/magic/fire resistance, ward save, mass, etc.) needs a DB search (`unit_abilities`/`unit_special_abilities` UI-only entries or an engine list).
4. **Item rarity.** `AncillaryRecordContext.FrameState` / `RarityName`: which `ancillaries` column feeds it (and how "crafted" is flagged)?
5. **Army size limit.** No layout encodes 20 units; confirm the campaign source (campaign variable or effect) before hard-coding it in the army planner. Custom battle offers 5/7/10/20/40.
6. **`skill_locked_rank.png` overlay.** Is the rank number drawn by the engine on top? The layout has no text for it.
7. **`ui_unit_stat_to_classes.filter`** (`melee`/`ranged`/`naval`) and the missing `list_order` 1: which stats are conditionally shown per unit (e.g. ammo and range only for missile units)?
8. **`effects.priority` hiding.** Confirm that `priority == 0` hides effects in every panel (the metadata docs say "generally"). Some bundles may still show them.
9. **Dark-theme colour adjustment.** Pick a rule (e.g. raise HSL lightness to ≥ 60 %) for game colours that are too dark on `#16120d`, and decide whether to offer the game's exact values in a light "parchment" theme instead.
