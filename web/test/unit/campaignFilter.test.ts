import { describe, expect, it } from "vitest";
import { campaignMatches, campaignRestriction, campaignTag } from "../../src/lib/campaignFilter";

const combi = { key: "wh3_main_combi", name: "Immortal Empires" };
const chaos = { key: "wh3_main_chaos", name: "The Realm of Chaos" };
const prologue = { key: "wh3_main_prologue", name: "The Lost God" };

describe("campaignTag", () => {
  it("tags factions by start position and other types by campaign, empty meaning every campaign", () => {
    expect(campaignTag("faction", { start_campaigns: [chaos, combi] })).toBe("wh3_main_chaos wh3_main_combi");
    expect(campaignTag("faction", { start_campaigns: [] })).toBe("");
    expect(campaignTag("character", { campaigns: [] })).toBe("*");
    expect(campaignTag("character", { campaigns: [chaos] })).toBe("wh3_main_chaos");
    expect(campaignTag("region", { campaign: combi })).toBe("wh3_main_combi");
    expect(campaignTag("province", { campaign: null })).toBe("*");
    expect(campaignTag("technology_tree", { campaign: null })).toBe("*");
    expect(campaignTag("unit", {})).toBeNull();
  });
});

describe("campaignMatches", () => {
  it("matches a listed campaign or every campaign, and everything when no campaign is selected", () => {
    expect(campaignMatches("wh3_main_chaos wh3_main_combi", "wh3_main_combi")).toBe(true);
    expect(campaignMatches("wh3_main_chaos", "wh3_main_combi")).toBe(false);
    expect(campaignMatches("*", "wh3_main_combi")).toBe(true);
    expect(campaignMatches("", "wh3_main_combi")).toBe(false);
    expect(campaignMatches("", "")).toBe(true);
  });
});

describe("campaignRestriction", () => {
  it("names campaigns only for entities in some but not all campaigns", () => {
    expect(campaignRestriction("character", { campaigns: [chaos, combi] }, 3)).toEqual([chaos, combi]);
    expect(campaignRestriction("character", { campaigns: [chaos, combi, prologue] }, 3)).toEqual([]);
    expect(campaignRestriction("character", { campaigns: [] }, 3)).toEqual([]);
    expect(campaignRestriction("faction", { start_campaigns: [prologue] }, 3)).toEqual([prologue]);
    expect(campaignRestriction("region", { campaign: combi }, 3)).toEqual([combi]);
    expect(campaignRestriction("unit", {}, 3)).toEqual([]);
  });
});
