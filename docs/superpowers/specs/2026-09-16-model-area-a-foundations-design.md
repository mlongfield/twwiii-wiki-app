# Model Area A: Foundations and Text — Design

**Date:** 2026-09-16
**Status:** Approved
**Model version:** 3
**Roadmap:** `docs/superpowers/specs/2026-09-16-model-v3-roadmap-design.md`, area A. The roadmap's shared conventions apply.

## Context

Area A is the first of six model refinement areas. It lays the foundations the other areas build on: a campaign entity and campaign tags, text cleanup, labels in place of raw keys, and effect presentation fields. It also fixes the most visible reader-facing problems the 2026-09-16 audits found (`docs/superpowers/audits/`):

- Raw keys are shown to readers: weapon keys, agent types, item types, building culture keys and campaign keys.
- 638 building chains are named "placeholder", and the region culture picker offers a `%PLACEHOLDER%` culture.
- Attribute titles are doubled, float values show artefacts (`0.90000004`), and `-1` values are shown as-is.
- Game-text rendering prints about 3,900 unknown tags as raw keys and styles only 7 of the 44 colours in use.
- Effects print their scope key, ignore good/bad polarity, and show effects the game hides.
- Same-named records can't be told apart, and there is no campaign dimension.

Area A changes the model and the web app in one pull request (roadmap decision).

## Decisions made in brainstorming

- **Campaign presentation:** badges plus an Immortal Empires default filter.
  - Pages show a small campaign badge on content that is not in every campaign.
  - Browse lists that carry campaign information get a Campaign filter that defaults to Immortal Empires, with an "All" option.
  - There is no site-wide campaign switch yet.
- **Unnamed records:** hidden from lists, pages kept.
  - Their names become null and are counted.
  - Their pages exist, titled "Unnamed <type>" with the key.
  - They are left out of browse lists, search and the culture picker.
  - They still appear in link lists when a named record links to them.
- **Weapons:** no name, as in the game. The weapon key row is removed from unit pages; the key stays in the model.
- **Effects with priority 0:** collapsed under a "Hidden effects (n)" disclosure, with a note that the game doesn't display them.

## Findings this design relies on

All counts are from build `1eb25ce70f3a`.

- **Campaigns.**
  - The `campaigns` table has three rows (`wh3_main_combi`, `wh3_main_chaos`, `wh3_main_prologue`) with `map_name` and `script_path`.
  - Loc `campaigns_onscreen_name_*` gives "Immortal Empires", "The Realm of Chaos" and "The Lost God".
  - `start_pos_factions` has 812 rows: combi 534 (104 playable), chaos 265 (25 playable), prologue 13 (1 playable), each with an `is_major` column.
- **Loc placeholders.**
  - 1,648 loc entries have text "placeholder" (any case), 1,228 of them `building_chains_encyclopedia_name_*`.
  - Every one of those 1,228 chains has a non-empty `building_chains_chain_tooltip_*` entry, which the chain builder already uses as a fallback.
- **Tokens.**
  - `{{tt:…}}` appears in 283 loc entries with 162 distinct targets, none of which exist as loc keys under any known prefix. In practice they sit inside `[[tooltip:{{tt:…}}]]` tags.
  - `{{Cco…:…}}` tokens are live UI expressions, e.g. `{{CcoCampaignPayloadInfoEntry:…}}`.
  - 19 `{{tr:}}` targets are unresolved.
- **Weapons:** there is no loc for melee or missile weapons.
- **Agent types.**
  - There are nine: general, champion, wizard, dignitary, engineer, spy, runesmith, minister, colonel.
  - Labels are per culture: `agent_culture_details` (agent, culture, key) with loc `agent_culture_details_onscreen_name_<key>`, e.g. "Lord".
- **Items.**
  - Category names come from `ancillaries_categories_onscreen_name_*` (some use `{{tr:}}`, e.g. arcane item).
  - Rarity comes from `ancillary_uniqueness_groupings` (`group_key`, `uniqueness_min`, `uniqueness_max`, `ui_state`, `col_hex`) matched against `ancillaries.uniqueness_score`. Names come from `ancillary_uniqueness_groupings_onscreen_name_*`, e.g. "Common", "[[col:ancillary_rare]]Rare[[/col]]".
  - `applies_to` is "." for 2,619 items and empty for 52.
- **Units:** the caste, category and class labels are genuine data. For Greatswords all three are "Melee Infantry" in loc.
- **Technology trees:** two trees have no name: `cth_mil` (culture Grand Cathay) and `rogue_mil` (Rogue Armies).
- **Effect scopes.**
  - Loc `campaign_effect_scopes_localised_text_<scope>` has 322 non-empty entries. They start with a literal `\n` escape (for example `\n([[img:icon_general]][[/img]]Lord's army)`); some scopes have empty text.
  - `effects.priority` is 0 for 1,339 effects, and `effects.is_positive_value_good` is true for 12,299 of 15,064.
- **Colours.**
  - `ui_colours` has 163 rows (`key`, `description`, `unnamed colour group_1` = hex without `#`).
  - Colour-blind overrides are in `ui_colour_profile_colour_overrides`.
  - Loc text uses 44 distinct `col:` names.
- **UI labels:** loc `uied_component_texts_localised_string_*` has 10,214 entries.

## Goals

- No raw DB key, placeholder string, unresolved token, float artefact or `-1` value is shown on any wiki page.
- Every entity with a campaign restriction carries it as links, and the wiki can filter by campaign.
- Effect lines read the way the game shows them: scope suffix, good/bad colour and icon, hidden effects set aside.
- Same-named records carry a short subtitle that tells them apart.
- The model build reports every placeholder, dropped token, unnamed record and unmatched rarity in the manifest.

## Non-goals

- Rider/mount/engine stats, bullet points, stat layout, ability sub-records (area B).
- Campaign rosters and recruitment (area C).
- Resolved scope objects, conditions, bonus-value dictionary (area E).
- Technology node faction restrictions (area F).
- A site-wide campaign switch; the broader visual redesign (text and muted base colours, serif body, card framing); a colour-blind toggle in the UI (the colour data is modelled, the toggle is later).

## Model changes (`twwiki/model/`)

### Loc and text (`text.py`)

- **Missing text.** `LocResolver.raw()` treats empty text, text equal to "placeholder" (case-insensitive, trimmed) and text containing `%PLACEHOLDER%` as missing. It counts each placeholder by key prefix, meaning the key up to its last `_<record>` segment, as recorded in the resolver.
- **Token handling** in `substitute()`, after `{{tr:}}` substitution:
  - `{{tt:<target>}}` is removed (it only ever appears as a tooltip argument) and counted by target.
  - `{{Cco…:…}}` tokens (regex `\{\{Cco[^:}]*:[^}]*\}\}`) are removed and counted.
  - Unresolved `{{tr:<target>}}` tokens are removed after the existing retries. They stay in `unresolved_targets` for the manifest.
- **`split_title_body(text) -> tuple[str | None, str | None]`.**
  - Splits on the first `||`.
  - Trims both parts; an empty part becomes None.
  - Text with no `||` returns `(None, text)`.
  - Used for unit attribute bullet text: the title replaces the attribute name when the name is null; otherwise the body alone is the description.
- **Float rounding.** `round_float(value) -> float` rounds to 6 significant digits (`float(f"{value:.6g}")`). The model writer applies it to every float in entities and reference documents when serialising, so no builder has to remember it.

### Campaign entity and tags

- **New entity type `campaign`** (`campaigns.py`), keyed by `campaigns.campaign_name`. Fields:
  - `key`, `name` (loc `campaigns_onscreen_name_<key>`), `map` (`map_name`), `script_folder` (`script_path`)
  - `playable_factions: list[Link]` and `major_factions: list[Link]`, from `start_pos_factions`
  - `factions: list[Link]`, all factions in that campaign's start position
  - `regions: list[Link]`, the reverse link from `region.campaign`
- **Existing campaign fields become links.** These fields currently hold `campaign: str | None` and change to `campaign: Link | None`:
  - `region.campaign`
  - `province.campaign`
  - skill tree node `campaign`
  - building chain availability `campaign`
  - `difficulty_level.campaign`
  - campaign variable override `campaign`
  - technology tree `campaign`
- **Technology tree nodes and placements** gain `campaigns: list[Link]` from `technology_nodes.campaign_key` (empty when blank, meaning every campaign).
- **Characters** gain `campaigns: list[Link]` from `campaign_to_agent_subtypes` rows for that subtype. No rows means every campaign.
- **Factions** gain three fields from `start_pos_factions`. An empty list means "in no campaign start position"; these are not campaign-restriction tags.
  - `start_campaigns: list[Link]`
  - `playable_in: list[Link]`, for rows where `playable` is true
  - `major_in: list[Link]`, for rows where `is_major` is true
- **Units.** `units_custom_battle_permissions` rows with `campaign_exclusive = true` no longer add to `unit.custom_battle_factions` (and therefore `faction.units`). The number excluded is counted in the manifest.

### Labels instead of raw keys

- **Character `agent_types`** becomes `list[AgentType]`, where `AgentType {key, name}`. The name comes from `agent_culture_details` for the character's culture; the character's culture is the culture of its first faction, if any. Otherwise it falls back to the first culture row for that agent, sorted by culture key. A null name is counted.
- **Item.**
  - `category` becomes `ItemCategory {key, name}` (name from `ancillaries_categories_onscreen_name_<key>` via `LocResolver.text`).
  - New `rarity: Rarity | None`, where `Rarity {key, name, colour}`. It uses the grouping whose `uniqueness_min <= uniqueness_score <= uniqueness_max`: `name` is loc text (markup kept), `colour` is `col_hex` with `#`. When no grouping matches, the rarity is null and the miss is counted.
  - `applies_to` is removed from the schema.
  - `type` stays, and pages don't show it.
- **Building level.** `cultures: list[str]` is replaced by `availability: list[Link]`. Each key from the building's culture variants resolves to a culture, subculture or faction link, in that order of lookup; an unresolved key becomes a missing link and is counted.
- **Weapons.** Melee and missile weapons get no name field; their `key` stays.
- **Technology tree.** When a tree has no loc name, its name is derived as `"<faction name or culture name> Technologies"` and `name_derived: true` is set. That derived name is used for linking and lists. When neither faction nor culture exists, the name stays null.

### Effect applications (`EffectApplication`)

New fields, filled for every application (skills, buildings, bundles, items, traits, technologies):

- `scope_text: str | None`
  - Loc `campaign_effect_scopes_localised_text_<scope>`.
  - A leading literal `\n` or `\\n` (and any whitespace) is stripped.
  - Markup is kept.
  - Empty text becomes None.
  - Applications whose scope has no text are counted.
- `priority: int`, from `effects.priority`.
- `hidden: bool`, which is `priority == 0`.
- `favourable: bool | None`
  - `(value > 0) == is_positive_value_good` when `value != 0`.
  - None when `value == 0`.
- `icon_image: str | None`: the effect's `icon_negative_image` when `favourable is False` and a negative image exists; otherwise the effect's `icon_image`.

### Reference documents (`model/<build_id>/reference/`)

Each document is a Pydantic model in `schemas.py`, written by `build.py` and listed in the manifest under `reference`.

- `campaigns.json`: the campaign entities in summary: `key`, `name`, `map`, playable and major counts.
- `colours.json`: one entry per `ui_colours` row. Each entry has:
  - `key` and `description`
  - `hex`: the game value, e.g. `#41E1E1`
  - `dark_hex`: `hex` if its HSL lightness is at least 60%; otherwise the same hue and saturation with lightness raised to 60%
  - `profiles: {deuteranopia|protanopia|tritanopia: hex}`, from `ui_colour_profile_colour_overrides`
- `ui_labels.json`: a map from label name to text for the `uied_component_texts_localised_string_*` entries the web app uses. The builder takes a fixed list of label keys (`UI_LABEL_KEYS` in the builder, starting with the labels for Duration, Cooldown, Uses, Range, Stats, Abilities, Effects and Research Rate) and counts keys with no text.

### Manifest

- `model_version`: 3.
- New `text` section:
  - `placeholders_by_prefix`
  - `dropped_tt_tokens`
  - `dropped_cco_tokens`
  - `dropped_tr_tokens`
- New counts:
  - `unnamed_by_type`
  - `effect_applications_without_scope_text`
  - `unmatched_rarity_scores`
  - `unresolved_agent_type_names`
  - `campaign_exclusive_permissions_excluded`
  - `unresolved_building_availability_keys`
- New `reference` section: document name → entry count.

## Web changes (`web/`)

### Game text (`src/lib/gameText.ts`)

- **Tags.**
  - `col` and `overridecol` push a span with class `gt-col-<name>`.
  - `img` renders as today.
  - `b` and `i` render bold and italic.
  - `sl`, `sl_link`, `url`, `tooltip`, `sl_tooltip` and `fragment` render only their inner text.
  - `opacity:<n>` renders its inner text, or nothing when `n` is 0.
  - Any other tag renders only its inner text.
- **Closing tags.** A closing tag closes only the most recent open element with the same tag name. A close with no matching open tag is ignored.
- **Tokens.** Any `{{…}}` token reaching the renderer is dropped. A model-builder counter should keep it from happening.

### Colours

- **Generated CSS.** The prebuild writes `src/generated/colours.css` with one `.gt-col-<key> { color: var(--col-<key>) }` rule and one `--col-<key>` custom property (using `dark_hex`) per `colours.json` entry.
- **Theme.** `theme.css` imports the generated file and removes its seven hand-set `--col-*` colours. Other theme tokens are unchanged.
- **Unknown names.** A `col:` name that isn't in `colours.json` renders uncoloured, and the build report counts it.

### Game value display (`src/lib/gameValue.ts`)

A single module applies the roadmap's display rules. Its functions return either formatted text or `null` (row hidden):

- `formatRange(v)`: negative → "∞", 0 → null, positive → number.
- `formatDuration(v)`: 0 or less → "∞", positive → number + "s".
- `formatUses(v)`: negative → null, otherwise the number.
- `hideIfZero(v)`: 0 → null. Used for cooldown, miscast chance and wind cost.

The shared stat table accepts these functions per row, and the ability page uses them for every activation row.

### Effects (`src/components/EffectList.astro`)

- **Scope and icon.** Each line shows `scope_text` through the game-text renderer after the description, replacing `scopeLabel()`. The icon comes from the application's `icon_image`.
- **Polarity.** The value text gets class `fx-good` or `fx-bad` from `favourable`; values of 0 stay neutral. Both classes use the generated `green` and `red` colours.
- **Hidden effects.** Applications with `hidden` render in a `<details>` element titled "Hidden effects (n)", placed after the visible list. A one-line note reads "The game does not display these effects."

### Campaigns

- **Campaign page type** (`/campaigns/<key>/`). It shows the name, map, "Playable factions", "Major factions" and "Regions".
- **`CampaignBadge.astro`.** Rendered in the page header when the entity is restricted to some but not all campaigns. The badge text is each campaign name joined with " · " (e.g. "The Realm of Chaos"). The restriction comes from:
  - `campaigns` for characters and technology tree nodes;
  - `start_campaigns` for factions;
  - `campaign` for regions, provinces, difficulty levels, technology trees and chain availability rows.
- **Campaign filter.** Browse lists for factions, characters, regions, provinces, difficulty levels and technology trees get a "Campaign" filter.
  - It defaults to Immortal Empires; "All" is an option.
  - For factions, a faction matches a campaign when that campaign is in its `start_campaigns`. For the other types, the entity matches when its campaign tag contains that campaign or is empty.
  - Without JavaScript every row shows.
- **Links.** Region, province, skill node, chain availability and faction pages link to their campaigns.

### Telling same-named records apart (`src/lib/subtitle.ts`)

- **Subtitles.** `subtitleFor(type, entity): string | null` returns:
  - unit: category name;
  - character: agent type name and culture name;
  - building level: chain name;
  - item: rarity name and category name;
  - faction: culture name and the start campaign names;
  - technology tree: faction name, or else culture name.
- **Page header:** shown under the title.
- **Browse lists:** a new "Details" column, kept at phone width.
- **Search results:** the subtitle is stored in the search index document and shown under each result.
- **Link lists:** `LinkList` shows the subtitle only for entries whose name appears more than once in that list.

### Unnamed records

- **Titles.** Entity pages whose name is null are titled "Unnamed <singular type label>" with the key under it.
- **Lists.** Browse lists, the search index and the region culture picker skip records with a null name.
- **Link lists.** Link lists render them as the key, as today.

### Page updates

- **Unit:**
  - The "Weapon" key row is removed from the melee and missile weapon tables.
  - When the caste, category and class names are identical, one "Type" row replaces the three.
- **Item:** "Rarity" (coloured by `rarity.colour`) and "Category" rows. The type row and "Applies to" row are removed.
- **Building level:** "Available to" becomes a link list (from `availability`), replacing the "Cultures" key row.
- **Character:** "Agent types" shows names.
- **Faction:** "Starts in" and "Playable in" link rows.
- **Ability:** activation rows use `gameValue.ts`.

### Types, loader and fixtures

- **Version and types.** The web `MODEL_VERSION` becomes 3, and the generated types include `campaign` and the new fields.
- **Reference loader.** The data layer loads `reference/campaigns.json`, `reference/colours.json` and `reference/ui_labels.json`. The prebuild fails with a message naming the missing file when a version 3 model lacks any of them.
- **Fixture model.** `npm run fixtures` regenerates `web/test/fixtures/model`. It must include a campaign, a hidden effect, an unfavourable effect, an item with a rarity, a building chain whose encyclopedia name was a placeholder, and a campaign-restricted technology node.

## Error handling

- **Missing optional tables:** fields stay empty and the entity type is recorded in `partial`, as today.
- **Schema validation:** the model build still fails only on schema validation and image-copy failures.
- **Missing reference file:** the web prebuild fails on a missing reference file for model version 3.
- **Unknown colour names and dropped tokens** are counted, not fatal.

## Testing

### Python (`tests/model/`)

- **Text:**
  - Placeholder and empty text count as missing, and are counted by prefix.
  - Dropping `{{tt:}}`, `{{Cco…}}` and unresolved `{{tr:}}` keeps surrounding text; for example `[[tooltip:{{tt:x}}]]word[[/tooltip]]` keeps the tags and "word".
  - `split_title_body` with no delimiter, two delimiters, and markup.
  - `round_float`: `0.90000004` → `0.9`, `1.0000001` → `1.0`, integers unchanged, `1e-7` unchanged.
- **Campaigns:**
  - The campaign builder.
  - Link conversion for every former campaign string.
  - Technology node and character tags, with empty meaning every campaign.
  - Faction start, playable and major lists.
  - `campaign_exclusive` exclusion.
- **Labels:**
  - Agent type culture choice and fallback.
  - Rarity range match, including a score outside every range.
  - Item category names.
  - Building availability resolution (culture, subculture, faction, unresolved).
  - Derived technology tree names.
- **Effects:**
  - `scope_text` stripping and the empty case.
  - `favourable` for all four combinations of sign and `is_positive_value_good`, and for zero.
  - `icon_image` switching.
  - `hidden`.
- **Reference and manifest:** reference documents validate, `dark_hex` lightening is correct at the 60% boundary, and the manifest has the new sections.
- **Real build (`tests/model/test_real_build.py`):**
  - The three campaign names.
  - Altdorf's `campaign` links to `wh3_main_combi`.
  - `wh2_dlc09_special_settlement_khemri_tmb` has a non-placeholder name.
  - Karl Franz has an agent type named "Lord".
  - Ghal Maraz has a non-null rarity.
  - Some `army_to_army_own` application has a `scope_text` containing "Lord's army".
  - No entity string contains `{{tt:`, `{{Cco` or "placeholder" as the entire value.
  - No serialised float matches `\d\.\d*0{5,}\d`.
  - `cth_mil` has a derived name.
  - Unnamed building chains stay at or below a threshold set from the first real build and recorded in the test.

### Web

- **Unit tests:**
  - Game text: every tag, nesting, unmatched closers, `opacity:0`, unknown tags, dropped tokens.
  - `gameValue.ts` rules.
  - `subtitleFor` for each type.
  - `LinkList` subtitles only for repeated names.
  - Effect list polarity classes and the hidden group.
  - Colour CSS generation.
  - Campaign filter matching, including empty tags and the faction rule.
  - The prebuild error for a missing reference file.
- **End-to-end:**
  - The factions list defaults to Immortal Empires, and "All" shows more rows.
  - An item page shows its rarity.
  - A unit page has no weapon key.
  - An effect list shows the "Hidden effects" disclosure.
  - A campaign page loads.
  - A region culture picker has no "placeholder" or "%PLACEHOLDER%" entries.

### Baselines

`tests/model/missing_links_baseline.json` and `missing_images_baseline.json` are regenerated deliberately. The pull request explains any count that rises.

## Rollout

The Deploy workflow builds whatever model `site/current` names, and the area A web app reads only model version 3. The pull request description must state this order:

1. Rebuild the model locally: `uv run python -m twwiki.model`.
2. Publish it without deploying: `uv run python -m twwiki.publish --no-deploy`. This puts model version 3 in Firestore and Cloud Storage under the same build id.
3. Merge the pull request. The push to `main` runs Deploy, which builds the version 3 site.

Between steps 2 and 3 the live site keeps serving its existing static release.

## Done means

- Python and web unit tests and end-to-end tests pass.
- After rollout the live site shows:
  - campaign badges, and browse lists defaulting to Immortal Empires;
  - named chains in Altdorf's culture picker, with no "placeholder" or "%PLACEHOLDER%";
  - magic-coloured text in cyan, and no raw `url:` or `tooltip:` text;
  - "(Lord's army)" scope text on a relevant skill effect;
  - hidden effects collapsed;
  - Reikland's repeated unit names and Karl Franz's repeated factions with subtitles.

## Open items for implementation (not blocking)

- **Assumption: `campaign_to_agent_subtypes` restricts subtypes to the listed campaigns.** Before relying on it, check that subtypes listed only for `wh3_main_chaos` are Realm of Chaos–only lords, and that common subtypes such as generic Empire generals have no rows. If the table instead lists every campaign a subtype appears in, the rule stays the same, but record in the model code that an empty list means "no data" rather than "every campaign".

- The unnamed building chain threshold is set from the first real build.
- The initial `UI_LABEL_KEYS` list follows from which pages use game labels. At least the labels for Duration, Cooldown, Uses, Range, Stats, Abilities, Effects and Research Rate are included.
