import path from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import { mainImage } from "../../src/data/images";
import { loadModel } from "../../src/data/load";
import { type Site, createSite } from "../../src/data/site";

const FIXTURE = path.resolve(__dirname, "../fixtures/model");
let site: Site;
const get = (type: string, key: string) => (site.model.entities as any)[type].get(key);

beforeAll(async () => {
  site = await createSite(await loadModel(FIXTURE));
});

describe("mainImage", () => {
  it("uses the unit card, falling back to the portrait", () => {
    const gs = get("unit", "wh_main_emp_inf_greatswords");
    expect(mainImage(site, "unit", gs)).toEqual({ path: gs.card_image, kind: "card" });
    expect(mainImage(site, "unit", { card_image: null, portrait_image: "p.png" })).toEqual({ path: "p.png", kind: "portrait" });
  });

  it("uses the associated unit's portrait for characters", () => {
    const karl = get("character", "wh_main_emp_karl_franz");
    const unit = get("unit", karl.associated_unit.key);
    expect(mainImage(site, "character", karl)).toEqual({ path: unit.portrait_image ?? unit.card_image ?? null, kind: "portrait" });
  });

  it("uses flags for factions, icons for icon types, nothing for others", () => {
    const faction = get("faction", "wh_main_emp_empire");
    expect(mainImage(site, "faction", faction)).toEqual({ path: faction.flag_image, kind: "flag" });
    const skill = [...site.model.entities.skill.values()][0];
    expect(mainImage(site, "skill", skill)).toEqual({ path: skill.icon_image, kind: "icon" });
    expect(mainImage(site, "region", get("region", "wh3_main_combi_region_altdorf"))).toBeNull();
  });
});
