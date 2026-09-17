/** Campaign tags on browse rows, the rule the Campaign filter applies, and when a page shows a campaign badge. */
export const DEFAULT_CAMPAIGN = "wh3_main_combi";
export const EVERY_CAMPAIGN = "*";
export const CAMPAIGN_FILTER_TYPES: ReadonlySet<string> = new Set(["faction", "character", "region", "province", "technology_tree"]);

export interface CampaignLink {
  key: string;
  name: string | null;
}

type Entity = Record<string, any>;

function campaignLinks(type: string, entity: Entity): CampaignLink[] {
  if (type === "character") return entity.campaigns ?? [];
  if (type === "faction") return entity.start_campaigns ?? [];
  if (type === "region" || type === "province" || type === "technology_tree") return entity.campaign ? [entity.campaign] : [];
  return [];
}

/**
 * A row's data-campaigns value: space-separated campaign keys, "*" for every campaign, or null
 * for types without the filter. A faction in no start position has an empty tag and only shows under "All".
 */
export function campaignTag(type: string, entity: Entity): string | null {
  if (!CAMPAIGN_FILTER_TYPES.has(type)) return null;
  const keys = campaignLinks(type, entity).map((c) => c.key).join(" ");
  return keys || (type === "faction" ? "" : EVERY_CAMPAIGN);
}

export function campaignMatches(tag: string, selected: string): boolean {
  if (!selected) return true;
  return tag === EVERY_CAMPAIGN || tag.split(" ").includes(selected);
}

/** The campaigns a page badge names: only when the entity is in some, but not all, campaigns. */
export function campaignRestriction(type: string, entity: Entity, totalCampaigns: number): CampaignLink[] {
  const links = campaignLinks(type, entity);
  return links.length > 0 && links.length < totalCampaigns ? links : [];
}
