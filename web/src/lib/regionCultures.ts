import { type Site, imageSrc, urlFor } from "../data/site";

export interface ChainOption {
  key: string;
  name: string;
  url: string | null;
  icon: string | null;
}

export interface ChainGroup {
  category: string;
  chains: ChainOption[];
}

export interface CultureChoice {
  key: string;
  name: string;
}

export function cultureChoices(site: Site): CultureChoice[] {
  return [...site.model.entities.culture.values()]
    .filter((c) => c.name)
    .map((c) => ({ key: c.key, name: c.name! }))
    .sort((a, b) => a.name.localeCompare(b.name) || a.key.localeCompare(b.key));
}

export function defaultCulture(site: Site, region: { starting_owner: { key: string } | null }): string | null {
  const owner = region.starting_owner ? site.model.entities.faction.get(region.starting_owner.key) : undefined;
  const ownerCulture = owner?.culture?.key;
  if (ownerCulture && site.model.entities.culture.has(ownerCulture)) return ownerCulture;
  return cultureChoices(site)[0]?.key ?? null;
}

/** Chains a culture can build, grouped by chain category (categories sorted, chains in name order). */
export function chainGroups(site: Site, cultureKey: string): ChainGroup[] {
  const byCategory = new Map<string, ChainOption[]>();
  for (const key of site.chainsByCulture.get(cultureKey) ?? []) {
    const chain = site.model.entities.building_chain.get(key)!;
    if (!chain.name) continue;
    const firstLevel = chain.levels[0] ? site.model.entities.building_level.get(chain.levels[0].key) : undefined;
    const option: ChainOption = {
      key,
      name: chain.name,
      url: urlFor(site, "building_chain", key),
      icon: imageSrc(site, firstLevel?.icon_image),
    };
    const category = chain.category ?? "other";
    const list = byCategory.get(category);
    if (list) list.push(option);
    else byCategory.set(category, [option]);
  }
  return [...byCategory.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([category, chains]) => ({ category, chains }));
}

export function allCultureChains(site: Site): Record<string, ChainGroup[]> {
  return Object.fromEntries(cultureChoices(site).map((c) => [c.key, chainGroups(site, c.key)]));
}
