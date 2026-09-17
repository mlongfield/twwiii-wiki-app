import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadModel } from "../../src/data/load";
import { createSite } from "../../src/data/site";
import { uiLabel } from "../../src/data/uiLabels";
import { formatDuration, formatRange, formatUses, hideIfZero } from "../../src/lib/gameValue";

describe("game value display rules", () => {
  it("formats ranges: negative is unlimited, zero hides the row", () => {
    expect(formatRange(-1)).toBe("∞");
    expect(formatRange(0)).toBeNull();
    expect(formatRange(35)).toBe("35");
  });

  it("formats durations: zero or less is unlimited", () => {
    expect(formatDuration(-1)).toBe("∞");
    expect(formatDuration(0)).toBe("∞");
    expect(formatDuration(12.5)).toBe("12.5s");
  });

  it("formats uses: negative hides the row", () => {
    expect(formatUses(-1)).toBeNull();
    expect(formatUses(0)).toBe("0");
    expect(formatUses(3)).toBe("3");
  });

  it("hides zero", () => {
    expect(hideIfZero(0)).toBeNull();
    expect(hideIfZero(0.25)).toBe("0.25");
  });
});

describe("uiLabel", () => {
  it("uses the game label and falls back when there is none", async () => {
    const site = await createSite(await loadModel(path.resolve(__dirname, "../fixtures/model")));
    expect(uiLabel(site, "duration", "Fallback")).toBe("Duration");
    expect(uiLabel(site, "not_a_label", "Fallback")).toBe("Fallback");
  });
});
