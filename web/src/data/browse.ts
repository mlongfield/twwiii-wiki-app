import { formatNumber } from "../lib/effectText";
import { type EntityImage, mainImage } from "./images";
import type { PageType } from "./pageTypes";
import { type Site, urlFor } from "./site";

export const BROWSE_FIELDS: Record<PageType, { field: string; label: string }[]> = {
  unit: [
    { field: "caste", label: "Caste" },
    { field: "category", label: "Category" },
    { field: "unit_class", label: "Class" },
    { field: "tier", label: "Tier" },
    { field: "is_naval", label: "Naval" },
  ],
  character: [
    { field: "agent_types", label: "Agent types" },
    { field: "is_caster", label: "Caster" },
  ],
  skill: [{ field: "unlocked_at_rank", label: "Unlock rank" }],
  ability: [
    { field: "type", label: "Type" },
    { field: "source_type", label: "Source" },
  ],
  technology: [{ field: "is_hidden", label: "Hidden" }],
  technology_tree: [],
  building_level: [
    { field: "level", label: "Level" },
    { field: "cultures", label: "Cultures" },
  ],
  building_chain: [{ field: "category", label: "Category" }],
  item: [
    { field: "category", label: "Category" },
    { field: "legendary", label: "Legendary" },
  ],
  trait: [{ field: "hidden", label: "Hidden" }],
  faction: [],
  culture: [],
  subculture: [],
  region: [
    { field: "campaign", label: "Campaign" },
    { field: "is_settlement", label: "Settlement" },
    { field: "template_source", label: "Templates" },
  ],
  province: [{ field: "campaign", label: "Campaign" }],
};

export interface BrowseRow {
  key: string;
  name: string;
  unnamed: boolean;
  url: string;
  image: EntityImage | null;
  values: string[];
}

export interface BrowseFilterSpec {
  index: number;
  label: string;
  options: string[];
}

export function cellText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.map(cellText).join(", ");
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return formatNumber(value);
  return String(value);
}

export function browseRows(site: Site, type: PageType): BrowseRow[] {
  const fields = BROWSE_FIELDS[type];
  const rows: BrowseRow[] = [];
  for (const entity of (site.model.entities[type] as Map<string, Record<string, any>>).values()) {
    const name: string | null = entity.name ?? null;
    rows.push({
      key: entity.key,
      name: name ?? entity.key,
      unnamed: !name,
      url: urlFor(site, type, entity.key)!,
      image: mainImage(site, type, entity),
      values: fields.map((f) => cellText(entity[f.field])),
    });
  }
  return rows.sort((a, b) => a.name.localeCompare(b.name) || a.key.localeCompare(b.key));
}

export function browseFilters(type: PageType, rows: BrowseRow[]): BrowseFilterSpec[] {
  return BROWSE_FIELDS[type].flatMap((field, index) => {
    const options = [...new Set(rows.map((r) => r.values[index]).filter((v) => v !== ""))].sort();
    return options.length >= 2 && options.length <= 40 ? [{ index, label: field.label, options }] : [];
  });
}
