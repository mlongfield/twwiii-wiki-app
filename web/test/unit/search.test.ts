import MiniSearch, { type SearchResult } from "minisearch";
import path from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import { loadModel } from "../../src/data/load";
import { ENTITY_TYPES, PAGE_TYPES } from "../../src/data/pageTypes";
import { buildSearchDocuments, createSearchIndexJson } from "../../src/data/searchIndex";
import { type Site, createSite } from "../../src/data/site";
import { SEARCH_OPTIONS, SEARCH_QUERY, groupResults } from "../../src/lib/search";

const FIXTURE = path.resolve(__dirname, "../fixtures/model");
let site: Site;

beforeAll(async () => {
  site = await createSite(await loadModel(FIXTURE));
});

/**
 * A minimal Site with empty entity maps for every type except the overrides given, for isolating
 * one page type's search-document logic without depending on the shared fixture model.
 */
function minimalSite(overrides: Record<string, Map<string, any>>): Site {
  const entities = Object.fromEntries(ENTITY_TYPES.map((t) => [t, overrides[t] ?? new Map()]));
  return {
    model: { dir: "", manifest: { build_id: "", model_version: 0, generated_at: "", counts: {} }, inline: {}, entities },
    slugs: Object.fromEntries(PAGE_TYPES.map((p) => [p.type, new Map()])),
    chainsByCulture: new Map(),
    images: new Set(),
  } as unknown as Site;
}

describe("buildSearchDocuments", () => {
  it("indexes every entity of every page type", () => {
    const docs = buildSearchDocuments(site);
    const expected = PAGE_TYPES.reduce((n, p) => n + site.model.entities[p.type].size, 0);
    expect(docs).toHaveLength(expected);
    expect(new Set(docs.map((d) => d.id)).size).toBe(docs.length);
  });

  it("stores names, URLs and facts", () => {
    const docs = buildSearchDocuments(site);
    const gs = docs.find((d) => d.id === "unit:wh_main_emp_inf_greatswords")!;
    expect(gs).toMatchObject({ type: "unit", typeLabel: "Unit", name: "Greatswords", url: "/units/wh_main_emp_inf_greatswords/", icon: null });
    expect(gs.category).not.toBe("");
    const chain = docs.find((d) => d.id === "building_chain:wh_main_EMPIRE_barracks")!;
    expect(chain.culture).toContain("The Empire");
    const faction = docs.find((d) => d.id === "faction:wh_main_emp_empire")!;
    expect(faction.culture).toBe("The Empire");
  });

  it("resolves a building_chain's culture via subculture and via faction, not just a direct culture ref", () => {
    const site = minimalSite({
      culture: new Map([["culture_x", { key: "culture_x", name: "Culture X" }]]),
      subculture: new Map([["subculture_x", { key: "subculture_x", culture: { key: "culture_x" } }]]),
      faction: new Map([["faction_x", { key: "faction_x", culture: { key: "culture_x" } }]]),
      building_chain: new Map([
        [
          "chain_x",
          {
            key: "chain_x",
            name: "Chain X",
            category: "test",
            availability: [
              { culture: null, subculture: null, faction: { key: "faction_x" } },
              { culture: null, subculture: { key: "subculture_x" }, faction: null },
            ],
          },
        ],
      ]),
    });
    const chain = buildSearchDocuments(site).find((d) => d.id === "building_chain:chain_x")!;
    expect(chain.culture).toBe("Culture X");
  });
});

describe("search index", () => {
  it("round-trips through JSON and finds Greatswords first", () => {
    const index = MiniSearch.loadJSON(createSearchIndexJson(site), SEARCH_OPTIONS);
    const results = index.search("greatswords", SEARCH_QUERY);
    expect(results[0].id).toBe("unit:wh_main_emp_inf_greatswords");
    expect(results[0].url).toBe("/units/wh_main_emp_inf_greatswords/");
  });
});

describe("groupResults", () => {
  it("groups by type in first-appearance order and caps each group", () => {
    const hit = (id: string, type: string): SearchResult =>
      ({ id, score: 1, terms: [], queryTerms: [], match: {}, type, typeLabel: type.toUpperCase(), key: id, name: id, icon: null, url: `/${id}/` }) as SearchResult;
    const results = [hit("s1", "skill"), hit("u1", "unit"), hit("s2", "skill"), hit("s3", "skill")];
    const groups = groupResults(results, 2);
    expect(groups.map((g) => [g.type, g.items.map((i) => i.id)])).toEqual([
      ["skill", ["s1", "s2"]],
      ["unit", ["u1"]],
    ]);
    expect(groups[0].typeLabel).toBe("SKILL");
  });
});
