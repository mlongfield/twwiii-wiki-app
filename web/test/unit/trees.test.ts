import path from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import { loadModel } from "../../src/data/load";
import { type Site, createSite } from "../../src/data/site";
import { skillTreeLayout, technologyTreeLayout } from "../../src/data/trees";
import { HIDDEN_ROW } from "../../src/lib/treeLayout";

const FIXTURE = path.resolve(__dirname, "../fixtures/model");
let site: Site;

beforeAll(async () => {
  site = await createSite(await loadModel(FIXTURE));
});

describe("skillTreeLayout", () => {
  it("lays out Karl Franz's visible skills with links and details", () => {
    const tree = site.model.entities.character.get("wh_main_emp_karl_franz")!.skill_trees[0];
    const layout = skillTreeLayout(site, tree);
    const visible = tree.nodes.filter((n) => n.visible_in_ui && n.indent !== HIDDEN_ROW);
    expect(layout.cells).toHaveLength(visible.length);
    const charge = layout.cells.find((c) => c.node.label === "Devastating Charge")!;
    expect(charge.node.url).toBe("/skills/wh2_dlc11_skill_all_lord_self_devastating_charge/");
    expect(charge.node.detailHtml).toContain("Level 1");
    expect(layout.links.length).toBeGreaterThan(0);
  });
});

describe("technologyTreeLayout", () => {
  it("lays out Empire Civil Tech with research costs in the details", () => {
    const tree = site.model.entities.technology_tree.get("emp_civ_reworkd")!;
    const layout = technologyTreeLayout(site, tree);
    expect(layout.cells).toHaveLength(tree.nodes.length);
    const heavy = layout.cells.find((c) => c.node.label === "Improved Heavy Weapons")!;
    expect(heavy.node.url).toBe("/technologies/wh2_dlc13_tech_emp_infantry_1_c/");
    expect(heavy.node.detailHtml).toContain("Research points: 900");
  });
});
