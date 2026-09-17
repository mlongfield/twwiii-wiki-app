/** HTML for tree detail panels, built at build time and passed to the TreeView island. */
import { type Site, imageSrc, urlFor } from "../data/site";
import { formatEffect, formatNumber, polarityClass } from "./effectText";
import { renderGameTextHtml } from "./gameText";
import { escapeHtml } from "./html";

export interface EffectApplicationRef {
  effect: { key: string };
  scope_text: string | null;
  value: number;
  hidden: boolean;
  favourable: boolean | null;
  icon_image: string | null;
  value_damaged?: number | null;
  value_ruined?: number | null;
  context_requirement?: string | null;
  advancement_stage?: string | null;
}

function images(site: Site) {
  return { inline: site.model.inline, src: (p: string) => imageSrc(site, p), colours: site.colourKeys };
}

const note = (text: string) => `<span class="muted effect-note">${escapeHtml(text)}</span>`;

function iconHtml(site: Site, imagePath: string | null): string {
  const src = imageSrc(site, imagePath);
  return src
    ? `<img class="game-img game-img-icon" src="${escapeHtml(src)}" alt="" loading="lazy" decoding="async">`
    : '<span class="game-img game-img-icon placeholder" data-placeholder-image aria-hidden="true"></span>';
}

function effectItemHtml(site: Site, a: EffectApplicationRef, icons: boolean): string {
  const effect = site.model.entities.effect.get(a.effect.key);
  const text = renderGameTextHtml(formatEffect(effect?.description ?? null, a.effect.key, a.value), images(site));
  const polarity = polarityClass(a.favourable);
  const parts = [
    icons ? iconHtml(site, a.icon_image) : "",
    `<span class="${polarity ? `effect-text ${polarity}` : "effect-text"}">${text}</span>`,
  ];
  if (a.scope_text) parts.push(`<span class="effect-scope">${renderGameTextHtml(a.scope_text, images(site))}</span>`);
  if (a.value_damaged != null) parts.push(note(`damaged ${formatNumber(a.value_damaged)}`));
  if (a.value_ruined != null) parts.push(note(`ruined ${formatNumber(a.value_ruined)}`));
  if (a.context_requirement) parts.push(note(`when ${a.context_requirement}`));
  if (a.advancement_stage) parts.push(note(a.advancement_stage.replace(/_/g, " ")));
  return `<li>${parts.join("")}</li>`;
}

/** Effect lines as the game shows them; priority-0 effects go in a closed "Hidden effects" disclosure. */
export function effectsHtml(site: Site, applications: EffectApplicationRef[], { icons = false }: { icons?: boolean } = {}): string {
  if (!applications.length) return "";
  const list = (apps: EffectApplicationRef[]) =>
    `<ul class="effect-list">${apps.map((a) => effectItemHtml(site, a, icons)).join("")}</ul>`;
  const visible = applications.filter((a) => !a.hidden);
  const hidden = applications.filter((a) => a.hidden);
  let html = visible.length ? list(visible) : "";
  if (hidden.length) {
    html +=
      `<details class="hidden-effects"><summary>Hidden effects (${hidden.length})</summary>` +
      `<p class="muted">The game does not display these effects.</p>${list(hidden)}</details>`;
  }
  return html;
}

/** "Only in <campaign> · <campaign>" for tree nodes limited to some campaigns; empty when unrestricted. */
export function campaignNoteHtml(site: Site, campaigns: { key: string; name: string | null }[]): string {
  if (!campaigns.length) return "";
  const links = campaigns.map((c) => {
    const url = urlFor(site, "campaign", c.key);
    const label = escapeHtml(c.name ?? c.key);
    return url ? `<a href="${escapeHtml(url)}">${label}</a>` : label;
  });
  return `<p class="muted campaign-note">Only in ${links.join(" · ")}</p>`;
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
  campaigns: { key: string; name: string | null }[];
}

export function technologyDetailHtml(site: Site, node: TechNodeRef): string {
  const tech = site.model.entities.technology.get(node.technology.key);
  const parts: string[] = [];
  const description = tech ? renderGameTextHtml(tech.description, images(site)) : "";
  if (description) parts.push(`<p>${description}</p>`);
  const perTurn = node.cost_per_round ? ` · cost per turn ${formatNumber(node.cost_per_round)}` : "";
  parts.push(`<p class="muted">Research points: ${formatNumber(node.research_points_required)}${perTurn}</p>`);
  parts.push(campaignNoteHtml(site, node.campaigns));
  for (const r of node.resource_cost?.pooled_resources ?? []) {
    parts.push(`<p class="muted">${escapeHtml(r.pooled_resource_factor.replace(/_/g, " "))}: ${formatNumber(r.amount)}</p>`);
  }
  if (tech) parts.push(effectsHtml(site, tech.effects));
  return parts.join("");
}
