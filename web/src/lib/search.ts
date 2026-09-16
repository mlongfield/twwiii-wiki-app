/** Search options and result grouping; imported by the browser island, so no Node imports here. */
import type { Options, SearchOptions, SearchResult } from "minisearch";

export interface SearchDocument {
  id: string;
  type: string;
  typeLabel: string;
  key: string;
  name: string;
  culture: string;
  category: string;
  icon: string | null;
  url: string;
}

export const SEARCH_OPTIONS: Options<SearchDocument> = {
  idField: "id",
  fields: ["name", "key", "culture", "category"],
  storeFields: ["type", "typeLabel", "key", "name", "icon", "url"],
};

export const SEARCH_QUERY: SearchOptions = { prefix: true, fuzzy: 0.2, boost: { name: 3 }, combineWith: "AND" };

export interface SearchHit {
  id: string;
  type: string;
  typeLabel: string;
  key: string;
  name: string;
  icon: string | null;
  url: string;
}

export interface ResultGroup {
  type: string;
  typeLabel: string;
  items: SearchHit[];
}

export function groupResults(results: SearchResult[], perType = 8): ResultGroup[] {
  const groups = new Map<string, ResultGroup>();
  for (const result of results) {
    const hit: SearchHit = {
      id: String(result.id),
      type: result.type,
      typeLabel: result.typeLabel,
      key: result.key,
      name: result.name,
      icon: result.icon ?? null,
      url: result.url,
    };
    let group = groups.get(hit.type);
    if (!group) {
      group = { type: hit.type, typeLabel: hit.typeLabel, items: [] };
      groups.set(hit.type, group);
    }
    if (group.items.length < perType) group.items.push(hit);
  }
  return [...groups.values()];
}
