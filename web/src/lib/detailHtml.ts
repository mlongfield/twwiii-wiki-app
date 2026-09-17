/** HTML for tree detail panels, built at build time and passed to the TreeView island. */
import { type Site, imageSrc } from "../data/site";
import { formatEffect, formatNumber, scopeLabel } from "./effectText";
import { renderGameTextHtml } from "./gameText";
import { escapeHtml } from "./html";

interface ApplicationRef {
  effect: { key: string };
  scope: string | null;
  value: number;
}

function images(site: Site) {
  return { inline: site.model.inline, src: (p: string) => imageSrc(site, p), colours: site.colourKeys };
}

export function effectsHtml(site: Site, applications: ApplicationRef[]): string {
  if (!applications.length) return "";
  const items = applications.map((a) => {
    const effect = site.model.entities.effect.get(a.effect.key);
    const text = renderGameTextHtml(formatEffect(effect?.description ?? null, a.effect.key, a.value), images(site));
    const scope = scopeLabel(a.scope);
    return `<li>${text}${scope ? ` <span class="muted effect-note">${escapeHtml(scope)}</span>` : ""}</li>`;
  });
  return `<ul class="effect-list">${items.join("")}</ul>`;
}

export function skillDetailHtml(site: Site, skillKey: string): string {
  const skill = site.model.entities.skill.get(skillKey);
  if (!skill) return `<p class="missing" data-missing-link>${escapeHtml(skillKey)}</p>`;
  const parts: string[] = [];
  const description = renderGameTextHtml(skill.description, images(site));
  if (description) parts.push(`<p>${description}</p>`);
  if (skill.unlocked_at_rank) parts.push(`<p class="muted">Unlocks at rank ${skill.unlocked_at_rank}</p>`);
  for (const level of skill.levels) {
    const rank = level.unlocked_at_rank != null ? ` <span class="muted">· rank ${level.unlocked_at_rank}</span>` : "";
    parts.push(`<h4>Level ${level.level}${rank}</h4>${effectsHtml(site, level.effects)}`);
  }
  return parts.join("");
}

interface TechNodeRef {
  technology: { key: string };
  research_points_required: number;
  cost_per_round: number;
  resource_cost: { pooled_resources: { pooled_resource_factor: string; amount: number }[] } | null;
}

export function technologyDetailHtml(site: Site, node: TechNodeRef): string {
  const tech = site.model.entities.technology.get(node.technology.key);
  const parts: string[] = [];
  const description = tech ? renderGameTextHtml(tech.description, images(site)) : "";
  if (description) parts.push(`<p>${description}</p>`);
  const perTurn = node.cost_per_round ? ` · cost per turn ${formatNumber(node.cost_per_round)}` : "";
  parts.push(`<p class="muted">Research points: ${formatNumber(node.research_points_required)}${perTurn}</p>`);
  for (const r of node.resource_cost?.pooled_resources ?? []) {
    parts.push(`<p class="muted">${escapeHtml(r.pooled_resource_factor.replace(/_/g, " "))}: ${formatNumber(r.amount)}</p>`);
  }
  if (tech) parts.push(effectsHtml(site, tech.effects));
  return parts.join("");
}
