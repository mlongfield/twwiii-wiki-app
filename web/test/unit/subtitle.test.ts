import { describe, expect, it } from "vitest";
import type { Site } from "../../src/data/site";
import { repeatedNames, subtitleFor } from "../../src/lib/subtitle";

const link = (key: string, name: string | null) => ({ type: "x", key, name, missing: false });
const site = {
  model: { entities: { faction: new Map([["reikland", { key: "reikland", culture: link("emp", "The Empire") }]]) } },
} as unknown as Site;

describe("subtitleFor", () => {
  it("describes units by category", () => {
    expect(subtitleFor(site, "unit", { category_name: "Melee Infantry" })).toBe("Melee Infantry");
  });

  it("describes characters by agent type and the culture of their first faction", () => {
    expect(subtitleFor(site, "character", { agent_types: [{ key: "general", name: "Lord" }], factions: [link("reikland", "Reikland")] }))
      .toBe("Lord · The Empire");
    expect(subtitleFor(site, "character", { agent_types: [], factions: [] })).toBeNull();
  });

  it("describes building levels by chain", () => {
    expect(subtitleFor(site, "building_level", { chain: link("c", "Barracks") })).toBe("Barracks");
  });

  it("describes items by rarity and category, without markup", () => {
    expect(subtitleFor(site, "item", {
      rarity: { key: "r", name: "[[col:ancillary_rare]]Rare[[/col]]", colour: "#FFFFFF" },
      category: { key: "weapon", name: "Weapon" },
    })).toBe("Rare · Weapon");
  });

  it("describes factions by culture and start campaigns", () => {
    expect(subtitleFor(site, "faction", {
      culture: link("emp", "The Empire"),
      start_campaigns: [link("a", "Immortal Empires"), link("b", "The Realm of Chaos")],
    })).toBe("The Empire · Immortal Empires · The Realm of Chaos");
  });

  it("describes technology trees by faction, else culture", () => {
    expect(subtitleFor(site, "technology_tree", { faction: link("f", "Wulfhart"), culture: link("c", "The Empire") })).toBe("Wulfhart");
    expect(subtitleFor(site, "technology_tree", { faction: null, culture: link("c", "Grand Cathay") })).toBe("Grand Cathay");
  });

  it("has no subtitle for other types", () => {
    expect(subtitleFor(site, "skill", { key: "s" })).toBeNull();
  });
});

describe("repeatedNames", () => {
  it("finds names used more than once", () => {
    expect(repeatedNames([link("a", "Greatswords"), link("b", "Greatswords"), link("c", "Halberdiers"), link("d", null), null]))
      .toEqual(new Set(["Greatswords"]));
  });
});
