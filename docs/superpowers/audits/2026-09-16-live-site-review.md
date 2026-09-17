# Live site visual review (https://twwiii-wiki.web.app, build 1eb25ce70f3a)

## Ambiguous duplicates everywhere (names without context)
- Browse lists: Units "Alarielle the Radiant" x4, Building chains "Barracks" x8+, "Altar Recruitment" x5; Technology trees "Favours of Chaos" x6, "Kislev Tech" x2. No culture/faction column or filter; the Key column is the only disambiguator (and hidden on mobile).
- Faction Reikland "Units": ~100 flat entries mixing RoRs, lords, heroes, line units; duplicates (Amethyst Wizard x3, Engineer x3, Master Engineer x4 = mount/variant units) with no caste grouping or variant label.
- Ability Hold the Line "Units": Boris Todbringer x4, Empire Captain x4, General of the Empire x5, Karl Franz x5; "Characters": General of the Empire x3.
- Karl Franz "Factions": The Empire x4 (different faction keys, same display name).
- Unit Greatswords "Recruited at": Small Occupied Settlement / Occupied Settlement / Large Occupied Settlement each twice, plus Gathering Place / Military Encampment (rogue-army buildings) mixed with Empire Barracks; no culture grouping.
- Search dropdown: two "Greatswords" results with identical rows (no key facts shown to tell them apart).

## Raw keys and sentinel values shown to readers
- Unit: melee Weapon "wh_main_emp_greatsword"; Caste, Category and Class all display "Melee Infantry" (three different fields resolved to the same label, or mislabelled).
- Character: Agent types "general"; Skill tree subtitle "wh_main_skill_node_set_emp_karl_franz".
- Ability: "Phase" row shows the phase key; section titled "Phase 2" for the first/only phase; Activation shows -1 sentinels (Active time -1, Recharge -1, Uses -1, Allied units affected -1) instead of "Passive"/"Unlimited"/"All".
- Item Ghal Maraz: Type "wh_main_anc_weapon", Category "weapon", "Applies to ." , Legendary "No" (it is a legendary weapon), Unique in the world "No".
- Effects everywhere print the scope key in words ("character to character own", "province to province own unseen", "character to province own factionwide") under each effect; building effect shows "damaged 1 ruined 0".
- Building level Rally Field (barracks_2): Level "1" (0-based), Construction time "2" (no unit), Cultures "wh_main_emp_empire" (a faction key under a Cultures label).
- Region Altdorf: Campaign "wh3_main_combi" (not "Immortal Empires"); Region groups list of internal keys (cai_region_hint_..., wh3_dlc25_...); slot template keys shown.
- Region culture picker: option "%PLACEHOLDER%" (culture "*"), "Kislev" listed twice; 638 building-chain entries named "placeholder"; The Empire's list includes Bretonnian Culture, Kislev Palace, Couronne, Miragliano, Bordeleaux (other cultures' landmark/occupation chains).
- Faction: Colour "E00606" as text (no swatch).
- Technology trees list: "cth_mil" and "rogue_mil" unnamed; "Tech" (lzd_nakai); tree names don't say whose tree it is.
- Home: technology tree list repeats the same raw/duplicate names.

## Missing context a reader expects
- Unit: no armour/shield/missile block when absent is fine, but no ranged stats summary, no abilities section for units without abilities, no faction/culture ownership, no mount, no "used by lords/heroes" etc. Multiplayer cost equals recruitment cost with no explanation.
- Character: no starting army / playable faction / campaign info; Items list mixes mounts with items; skill detail says "Unlocks at rank 6" and "Level 1 · rank 3" together (contradictory).
- Building chain: header has no icon; Levels list has no level numbers, costs or recruit summary; Available-to table is sparse.
- Building level: no upkeep, no previous/next level navigation, recruits without icons.
- Technology tree: node detail shows research points but no turns; tree does not say which faction(s) use it.
- Faction: no playable flag, starting lord(s), tech tree, capital, campaign.

## Layout / alignment
- Two-column card grid aligns rows: a short card (Overview) leaves large empty gaps before the next row (Greatswords, Karl Franz).
- Unit card image in the header is 60x130 with a dark transparent background: nearly invisible on the dark theme at desktop.
- "Type: Augment (Area)" on abilities and "Unit: …", "Chain: …", "Culture: …", "Province: …" are rendered as loose label lines outside the stat tables, inconsistent with table rows on the same card.
- Skill/tech tree views: node labels truncated ("Deadly Bla…", "Majestic Enforcer" clipped), no visible prerequisite lines, horizontal scroll inside the card; tree rows don't reflect the game's layout (no rank/tier markers).
- Mobile: the site nav takes ~6 lines before content; browse filters wrap raggedly (Caste / Category+Class / Tier rows of different widths); browse table shows only Name (key hidden) so duplicates are indistinguishable; tree clipped with inner scroll.
- Search: first query shows "Loading search…" for ~4–5 s (11.4 MB index, 0.9 MB compressed, parsed client-side).
