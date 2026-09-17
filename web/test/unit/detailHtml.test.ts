import path from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import { loadModel } from "../../src/data/load";
import { type Site, createSite } from "../../src/data/site";
import { type EffectApplicationRef, campaignNoteHtml, effectsHtml } from "../../src/lib/detailHtml";

let site: Site;

beforeAll(async () => {
  site = await createSite(await loadModel(path.resolve(__dirname, "../fixtures/model")));
});

const app = (o: Partial<EffectApplicationRef>): EffectApplicationRef => ({
  effect: { key: "not_in_model" }, scope_text: null, value: 5, hidden: false, favourable: null, icon_image: null, ...o,
});

describe("effectsHtml", () => {
  it("marks polarity, shows scope text and sets hidden effects aside", () => {
    const html = effectsHtml(site, [
      app({ favourable: true, scope_text: "([[b]]Lords army[[/b]])" }),
      app({ favourable: false, value: -5 }),
      app({ hidden: true }),
      app({ hidden: true, value: 0 }),
    ]);
    expect(html).toContain(
      '<span class="effect-text fx-good">not_in_model (+5)</span><span class="effect-scope">(<strong>Lords army</strong>)</span>',
    );
    expect(html).toContain('<span class="effect-text fx-bad">not_in_model (-5)</span>');
    expect(html.match(/<li>/g)).toHaveLength(4);
    expect(html).toContain(
      '<details class="hidden-effects"><summary>Hidden effects (2)</summary><p class="muted">The game does not display these effects.</p>',
    );
    expect(html.indexOf("fx-bad")).toBeLessThan(html.indexOf("<details"));
  });

  it("renders nothing without applications and no disclosure without hidden effects", () => {
    expect(effectsHtml(site, [])).toBe("");
    expect(effectsHtml(site, [app({})])).not.toContain("<details");
    expect(effectsHtml(site, [app({})])).toContain('<span class="effect-text">');
  });

  it("adds icons only when asked", () => {
    expect(effectsHtml(site, [app({})], { icons: true })).toContain("game-img game-img-icon placeholder");
    expect(effectsHtml(site, [app({})])).not.toContain("game-img");
  });

  it("notes and links the campaigns a tree node is limited to", () => {
    expect(campaignNoteHtml(site, [])).toBe("");
    expect(campaignNoteHtml(site, [{ key: "wh3_main_chaos", name: "The Realm of Chaos" }])).toBe(
      '<p class="muted campaign-note">Only in <a href="/campaigns/wh3_main_chaos/">The Realm of Chaos</a></p>',
    );
  });

  it("keeps building notes", () => {
    const html = effectsHtml(site, [app({ value_damaged: 2, value_ruined: 0, context_requirement: "port", advancement_stage: "start_turn" })]);
    expect(html).toContain("damaged 2");
    expect(html).toContain("ruined 0");
    expect(html).toContain("when port");
    expect(html).toContain("start turn");
  });
});
