import { readdir } from "node:fs/promises";
import path from "node:path";
import type { Model } from "./load";
import { PAGE_TYPES, hasPage, imageUrl, pageTypeInfo, type PageType } from "./pageTypes";
import { buildSlugs } from "./slugs";

export interface Site {
  model: Model;
  slugs: Record<PageType, Map<string, string>>;
  chainsByCulture: Map<string, string[]>;
  images: Set<string>;
}

export interface AvailabilityRef {
  culture: { key: string } | null;
  subculture: { key: string } | null;
  faction: { key: string } | null;
}

/** Culture keys a chain's availability rows grant, resolving subculture and faction rows to their culture. */
export function chainCultureKeys(
  availability: AvailabilityRef[],
  subcultureCulture: (key: string) => string | undefined,
  factionCulture: (key: string) => string | undefined,
): Set<string> {
  const keys = new Set<string>();
  for (const row of availability) {
    const culture =
      row.culture?.key ??
      (row.subculture ? subcultureCulture(row.subculture.key) : undefined) ??
      (row.faction ? factionCulture(row.faction.key) : undefined);
    if (culture) keys.add(culture);
  }
  return keys;
}

async function listImages(modelDir: string): Promise<Set<string>> {
  const root = path.join(modelDir, "images");
  try {
    const entries = await readdir(root, { recursive: true, withFileTypes: true });
    return new Set(
      entries
        .filter((e) => e.isFile())
        .map((e) => path.relative(root, path.join(e.parentPath, e.name)).split(path.sep).join("/"))
        .filter((p) => p !== "inline.json"),
    );
  } catch {
    return new Set();
  }
}

export async function createSite(model: Model): Promise<Site> {
  const slugs = Object.fromEntries(
    PAGE_TYPES.map((p) => [p.type, buildSlugs(model.entities[p.type].keys())]),
  ) as Record<PageType, Map<string, string>>;

  const subcultureCulture = (key: string) => model.entities.subculture.get(key)?.culture?.key ?? undefined;
  const factionCulture = (key: string) => model.entities.faction.get(key)?.culture?.key ?? undefined;
  const chainsByCulture = new Map<string, string[]>();
  for (const chain of model.entities.building_chain.values()) {
    for (const culture of chainCultureKeys(chain.availability, subcultureCulture, factionCulture)) {
      const list = chainsByCulture.get(culture);
      if (list) list.push(chain.key);
      else chainsByCulture.set(culture, [chain.key]);
    }
  }
  const chainName = (key: string) => model.entities.building_chain.get(key)?.name ?? key;
  for (const list of chainsByCulture.values()) {
    list.sort((a, b) => chainName(a).localeCompare(chainName(b)) || a.localeCompare(b));
  }

  return { model, slugs, chainsByCulture, images: await listImages(model.dir) };
}

/** URL of an entity page, or null when the type has no pages or the key is not in the model. */
export function urlFor(site: Site, type: string, key: string): string | null {
  if (!hasPage(type)) return null;
  const slug = site.slugs[type].get(key);
  return slug ? `/${pageTypeInfo(type)!.segment}/${slug}/` : null;
}

/** Public URL for a model image path, or null when the path is empty or the file was not copied. */
export function imageSrc(site: Site, imagePath: string | null | undefined): string | null {
  return imagePath && site.images.has(imagePath) ? imageUrl(imagePath) : null;
}
