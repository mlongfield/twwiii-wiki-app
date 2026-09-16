import path from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import { BROWSE_FIELDS, browseFilters, browseRows, cellText } from "../../src/data/browse";
import { loadModel } from "../../src/data/load";
import { PAGE_TYPES } from "../../src/data/pageTypes";
import { type Site, createSite } from "../../src/data/site";

const FIXTURE = path.resolve(__dirname, "../fixtures/model");
let site: Site;

beforeAll(async () => {
  site = await createSite(await loadModel(FIXTURE));
});

describe("cellText", () => {
  it("formats values for table cells", () => {
    expect(cellText(["general", "wizard"])).toBe("general, wizard");
    expect(cellText(true)).toBe("Yes");
    expect(cellText(false)).toBe("No");
    expect(cellText(2.5)).toBe("2.5");
    expect(cellText(null)).toBe("");
    expect(cellText(undefined)).toBe("");
    expect(cellText("melee_infantry")).toBe("melee_infantry");
  });
});

describe("browseRows", () => {
  it("covers every page type", () => {
    expect(Object.keys(BROWSE_FIELDS).sort()).toEqual(PAGE_TYPES.map((p) => p.type).sort());
  });

  it("lists every entity with URL, name and field values, sorted by name", () => {
    const rows = browseRows(site, "unit");
    expect(rows).toHaveLength(site.model.entities.unit.size);
    const names = rows.map((r) => r.name);
    expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b)));
    const gs = rows.find((r) => r.key === "wh_main_emp_inf_greatswords")!;
    expect(gs.url).toBe("/units/wh_main_emp_inf_greatswords/");
    expect(gs.name).toBe("Greatswords");
    expect(gs.values).toHaveLength(BROWSE_FIELDS.unit.length);
    expect(gs.values[3]).toBe("3");
  });
});

describe("browseFilters", () => {
  it("offers dropdowns only for columns with 2 to 40 distinct values", () => {
    const filters = browseFilters("unit", browseRows(site, "unit"));
    expect(filters.map((f) => f.label)).toContain("Caste");
    expect(filters.map((f) => f.label)).not.toContain("Naval");
    const caste = filters.find((f) => f.label === "Caste")!;
    expect(caste.index).toBe(0);
    expect(caste.options).toEqual([...caste.options].sort());
  });
});
