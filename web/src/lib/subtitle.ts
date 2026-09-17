/** Short text that tells same-named records apart. */
import type { Site } from "../data/site";
import { stripGameMarkup } from "./gameText";

type Entity = Record<string, any>;
type NamedLink = { key: string; name: string | null } | null | undefined;

/** Types `subtitleFor` returns text for; must stay consistent with the switch below. */
export const SUBTITLE_TYPES: ReadonlySet<string> = new Set([
  "unit",
  "character",
  "building_level",
  "item",
  "faction",
  "technology_tree",
]);

function join(parts: (string | null | undefined)[]): string | null {
  const text = parts
    .filter((p): p is string => Boolean(p))
    .map(stripGameMarkup)
    .filter(Boolean)
    .join(" · ");
  return text || null;
}

export function subtitleFor(site: Site, type: string, entity: Entity): string | null {
  switch (type) {
    case "unit":
      return join([entity.category_name]);
    case "character": {
      const first = entity.factions?.[0];
      const faction = first ? site.model.entities.faction.get(first.key) : undefined;
      return join([entity.agent_types?.[0]?.name, faction?.culture?.name]);
    }
    case "building_level":
      return join([entity.chain?.name]);
    case "item":
      return join([entity.rarity?.name, entity.category?.name]);
    case "faction":
      return join([entity.culture?.name, ...(entity.start_campaigns ?? []).map((c: NamedLink) => c?.name)]);
    case "technology_tree":
      return join([entity.faction?.name ?? entity.culture?.name]);
    default:
      return null;
  }
}

/** Names that appear more than once in a list of links. */
export function repeatedNames(links: NamedLink[]): Set<string> {
  const counts = new Map<string, number>();
  for (const link of links) if (link?.name) counts.set(link.name, (counts.get(link.name) ?? 0) + 1);
  return new Set([...counts].filter(([, n]) => n > 1).map(([name]) => name));
}
