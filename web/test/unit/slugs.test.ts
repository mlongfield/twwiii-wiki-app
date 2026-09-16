import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import { baseSlug, buildSlugs } from "../../src/data/slugs";

const hash6 = (key: string) => createHash("sha1").update(key).digest("hex").slice(0, 6);

describe("slugs", () => {
  it("lower-cases and replaces unsafe characters", () => {
    expect(baseSlug("wh_main_EMPIRE_settlement_major")).toBe("wh_main_empire_settlement_major");
    expect(baseSlug("wh3_main_*_x&y!z'q-r")).toBe("wh3_main_-_x-y-z-q-r");
  });

  it("keeps unique slugs and disambiguates collisions with a hash suffix", () => {
    const slugs = buildSlugs(["wh2_main_skill_LL_self_defense", "wh2_main_skill_ll_self_defense", "wh_main_emp_inf_greatswords"]);
    expect(slugs.get("wh_main_emp_inf_greatswords")).toBe("wh_main_emp_inf_greatswords");
    expect(slugs.get("wh2_main_skill_LL_self_defense")).toBe(`wh2_main_skill_ll_self_defense-${hash6("wh2_main_skill_LL_self_defense")}`);
    expect(slugs.get("wh2_main_skill_ll_self_defense")).toBe(`wh2_main_skill_ll_self_defense-${hash6("wh2_main_skill_ll_self_defense")}`);
    expect(new Set(slugs.values()).size).toBe(3);
  });
});
