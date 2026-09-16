import path from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import { loadModel } from "../../src/data/load";
import { type Site, chainCultureKeys, createSite, imageSrc, urlFor } from "../../src/data/site";

const FIXTURE = path.resolve(__dirname, "../fixtures/model");
let site: Site;

beforeAll(async () => {
  site = await createSite(await loadModel(FIXTURE));
});

describe("createSite", () => {
  it("builds slugs and URLs for page types only", () => {
    expect(site.slugs.unit.get("wh_main_emp_inf_greatswords")).toBe("wh_main_emp_inf_greatswords");
    expect(urlFor(site, "unit", "wh_main_emp_inf_greatswords")).toBe("/units/wh_main_emp_inf_greatswords/");
    expect(urlFor(site, "building_chain", "wh_main_EMPIRE_barracks")).toBe("/building-chains/wh_main_empire_barracks/");
    expect(urlFor(site, "unit", "not_in_model")).toBeNull();
    const effectKey = [...site.model.entities.effect.keys()][0];
    expect(urlFor(site, "effect", effectKey)).toBeNull();
  });

  it("lists chains available per culture", () => {
    const empire = site.chainsByCulture.get("wh_main_emp_empire") ?? [];
    expect(empire).toContain("wh_main_EMPIRE_settlement_major");
    expect(empire).toContain("wh_main_EMPIRE_barracks");
  });

  it("only resolves images that exist", () => {
    expect(site.images.size).toBe(0);
    expect(imageSrc(site, "ui/battle ui/x.png")).toBeNull();
    expect(imageSrc(site, null)).toBeNull();
    site.images.add("ui/battle ui/x.png");
    expect(imageSrc(site, "ui/battle ui/x.png")).toBe("/images/ui/battle%20ui/x.png");
    site.images.delete("ui/battle ui/x.png");
  });
});

describe("chainCultureKeys", () => {
  it("resolves culture directly, via subculture, and via faction", () => {
    const keys = chainCultureKeys(
      [
        { culture: { key: "emp" }, subculture: null, faction: null },
        { culture: null, subculture: { key: "sc_dwf" }, faction: null },
        { culture: null, subculture: null, faction: { key: "f_chs" } },
        { culture: null, subculture: { key: "unknown" }, faction: null },
      ],
      (k) => (k === "sc_dwf" ? "dwf" : undefined),
      (k) => (k === "f_chs" ? "chs" : undefined),
    );
    expect([...keys].sort()).toEqual(["chs", "dwf", "emp"]);
  });
});
