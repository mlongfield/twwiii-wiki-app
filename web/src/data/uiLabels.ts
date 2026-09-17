import type { Site } from "./site";

/** A game UI label from reference/ui_labels.json, or the fallback when the game has no text for it. */
export function uiLabel(site: Site, name: string, fallback: string): string {
  return site.model.reference.ui_labels[name] ?? fallback;
}
