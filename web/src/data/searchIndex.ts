import MiniSearch from "minisearch";
import { SEARCH_OPTIONS, type SearchDocument } from "../lib/search";
import { mainImage } from "./images";
import { PAGE_TYPES, type PageType } from "./pageTypes";
import { type Site, chainCultureKeys, imageSrc, urlFor } from "./site";

type Entity = Record<string, any>;

function cultureNames(site: Site, keys: (string | null | undefined)[]): string {
  const names = keys.filter((k): k is string => Boolean(k)).map((k) => site.model.entities.culture.get(k)?.name ?? k);
  return [...new Set(names)].join(" ");
}

function searchCulture(site: Site, type: PageType, e: Entity): string {
  switch (type) {
    case "faction":
    case "subculture":
    case "technology_tree":
      return cultureNames(site, [e.culture?.key]);
    case "building_level":
      return cultureNames(site, e.cultures ?? []);
    case "building_chain": {
      const subcultureCulture = (key: string) => site.model.entities.subculture.get(key)?.culture?.key;
      const factionCulture = (key: string) => site.model.entities.faction.get(key)?.culture?.key;
      const keys = chainCultureKeys(e.availability ?? [], subcultureCulture, factionCulture);
      return cultureNames(site, [...keys]);
    }
    default:
      return "";
  }
}

function searchCategory(type: PageType, e: Entity): string {
  switch (type) {
    case "unit":
      return e.category_name ?? e.category ?? "";
    case "item":
    case "building_chain":
      return e.category ?? "";
    case "ability":
      return e.type ?? "";
    default:
      return "";
  }
}

export function buildSearchDocuments(site: Site): SearchDocument[] {
  const docs: SearchDocument[] = [];
  for (const info of PAGE_TYPES) {
    for (const entity of (site.model.entities[info.type] as Map<string, Entity>).values()) {
      docs.push({
        id: `${info.type}:${entity.key}`,
        type: info.type,
        typeLabel: info.singular,
        key: entity.key,
        name: entity.name ?? entity.key,
        culture: searchCulture(site, info.type, entity),
        category: searchCategory(info.type, entity),
        icon: imageSrc(site, mainImage(site, info.type, entity)?.path),
        url: urlFor(site, info.type, entity.key)!,
      });
    }
  }
  return docs;
}

export function createSearchIndexJson(site: Site): string {
  const index = new MiniSearch<SearchDocument>(SEARCH_OPTIONS);
  index.addAll(buildSearchDocuments(site));
  return JSON.stringify(index);
}
