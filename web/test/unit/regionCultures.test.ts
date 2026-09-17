import path from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import { loadModel } from "../../src/data/load";
import { type Site, createSite } from "../../src/data/site";
import { allCultureChains, chainGroups, cultureChoices, defaultCulture } from "../../src/lib/regionCultures";

const FIXTURE = path.resolve(__dirname, "../fixtures/model");
let site: Site;

beforeAll(async () => {
  site = await createSite(await loadModel(FIXTURE));
});

describe("region cultures", () => {
  it("lists cultures by name", () => {
    expect(cultureChoices(site)).toEqual([{ key: "wh_main_emp_empire", name: "The Empire" }]);
  });

  it("defaults to the starting owner's culture, else the first culture", () => {
    const altdorf = site.model.entities.region.get("wh3_main_combi_region_altdorf")!;
    expect(defaultCulture(site, altdorf)).toBe("wh_main_emp_empire");
    expect(defaultCulture(site, { starting_owner: null })).toBe("wh_main_emp_empire");
    expect(defaultCulture(site, { starting_owner: { key: "not_a_faction" } })).toBe("wh_main_emp_empire");
  });

  it("groups a culture's chains by category", () => {
    const groups = chainGroups(site, "wh_main_emp_empire");
    expect(groups.map((g) => g.category)).toEqual(["happiness", "military", "money"]);
    const all = groups.flatMap((g) => g.chains);
    const named = site.chainsByCulture.get("wh_main_emp_empire")!.filter((k) => site.model.entities.building_chain.get(k)!.name);
    expect(all).toHaveLength(named.length);
    expect(all.every((c) => c.name && !/placeholder/i.test(c.name))).toBe(true);
    const major = all.find((c) => c.key === "wh_main_EMPIRE_settlement_major")!;
    expect(major.url).toBe("/building-chains/wh_main_empire_settlement_major/");
    expect(major.icon).toBeNull();
    expect(chainGroups(site, "no_such_culture")).toEqual([]);
  });

  it("builds the shared culture file", () => {
    expect(Object.keys(allCultureChains(site))).toEqual(["wh_main_emp_empire"]);
  });
});
