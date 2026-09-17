export type EntityType =
  | "unit" | "character" | "skill" | "ability" | "effect" | "effect_bundle" | "building_level" | "building_chain"
  | "technology" | "technology_tree" | "item" | "trait" | "faction" | "culture" | "subculture"
  | "difficulty_level" | "campaign_variable" | "region" | "province" | "campaign";

export const ENTITY_TYPES: readonly EntityType[] = [
  "unit", "character", "skill", "ability", "effect", "effect_bundle", "building_level", "building_chain",
  "technology", "technology_tree", "item", "trait", "faction", "culture", "subculture",
  "difficulty_level", "campaign_variable", "region", "province", "campaign",
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
  { type: "campaign", segment: "campaigns", label: "Campaigns", singular: "Campaign" },
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
