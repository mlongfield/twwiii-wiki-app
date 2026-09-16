import type { Site } from "./site";

export type ImageKind = "icon" | "card" | "portrait" | "flag";

export interface EntityImage {
  path: string | null;
  kind: ImageKind;
}

const ICON_TYPES = new Set(["skill", "ability", "technology", "building_level", "item", "trait", "effect", "effect_bundle"]);

/** The picture that represents an entity in headers, links and search results. */
export function mainImage(site: Site, type: string, entity: Record<string, any>): EntityImage | null {
  if (type === "unit") {
    return entity.card_image ? { path: entity.card_image, kind: "card" } : { path: entity.portrait_image ?? null, kind: "portrait" };
  }
  if (type === "character") {
    const unit = entity.associated_unit ? site.model.entities.unit.get(entity.associated_unit.key) : undefined;
    return { path: unit?.portrait_image ?? unit?.card_image ?? null, kind: "portrait" };
  }
  if (type === "faction") return { path: entity.flag_image ?? null, kind: "flag" };
  if (ICON_TYPES.has(type)) return { path: entity.icon_image ?? null, kind: "icon" };
  return null;
}
