import { describe, expect, it } from "vitest";
import { ENTITY_TYPES, PAGE_TYPES, hasPage, imageUrl, pageTypeBySegment, pageTypeInfo } from "../../src/data/pageTypes";

describe("page types", () => {
  it("lists 20 entity types and 16 page types", () => {
    expect(ENTITY_TYPES).toHaveLength(20);
    expect(PAGE_TYPES.map((p) => p.segment)).toEqual([
      "units", "characters", "skills", "abilities", "technologies", "technology-trees", "buildings",
      "building-chains", "items", "traits", "factions", "cultures", "subcultures", "regions", "provinces", "campaigns",
    ]);
  });

  it("knows which types have pages", () => {
    expect(hasPage("unit")).toBe(true);
    expect(hasPage("building_level")).toBe(true);
    for (const t of ["effect", "effect_bundle", "difficulty_level", "campaign_variable", "nonsense"]) {
      expect(hasPage(t)).toBe(false);
    }
  });

  it("looks up page types by type and segment", () => {
    expect(pageTypeInfo("technology_tree")?.segment).toBe("technology-trees");
    expect(pageTypeBySegment("buildings")?.type).toBe("building_level");
    expect(pageTypeBySegment("effects")).toBeUndefined();
  });

  it("encodes image path segments", () => {
    expect(imageUrl("ui/battle ui/ability_icons/hold.png")).toBe("/images/ui/battle%20ui/ability_icons/hold.png");
  });
});
