import { describe, expect, it } from "vitest";
import { formatEffect, formatNumber, polarityClass, signed } from "../../src/lib/effectText";

describe("numbers", () => {
  it("drops trailing zeros and rounds to two decimals", () => {
    expect(formatNumber(2)).toBe("2");
    expect(formatNumber(2.0)).toBe("2");
    expect(formatNumber(0.333333)).toBe("0.33");
    expect(formatNumber(-12.5)).toBe("-12.5");
  });

  it("signs values", () => {
    expect(signed(4)).toBe("+4");
    expect(signed(-5)).toBe("-5");
    expect(signed(0)).toBe("+0");
  });
});

describe("formatEffect", () => {
  it("substitutes signed and unsigned placeholders", () => {
    expect(formatEffect("Melee attack: %+n", "e", 4)).toBe("Melee attack: +4");
    expect(formatEffect("Melee attack: %+n", "e", -5)).toBe("Melee attack: -5");
    expect(formatEffect("Recruitment cost: %+n%", "e", -10)).toBe("Recruitment cost: -10%");
    expect(formatEffect("Armour: %n", "e", 20)).toBe("Armour: 20");
    expect(formatEffect("Chance: %n%", "e", 12.5)).toBe("Chance: 12.5%");
    expect(formatEffect("Odd: %-n%", "e", 7)).toBe("Odd: 7%");
  });

  it("appends the value when there is no placeholder or no description", () => {
    expect(formatEffect("Enables Rampage", "e", 1)).toBe("Enables Rampage (+1)");
    expect(formatEffect(null, "wh_effect_x", 3)).toBe("wh_effect_x (+3)");
  });
});

describe("polarityClass", () => {
  it("colours favourable and unfavourable values and leaves others neutral", () => {
    expect(polarityClass(true)).toBe("fx-good");
    expect(polarityClass(false)).toBe("fx-bad");
    expect(polarityClass(null)).toBeNull();
    expect(polarityClass(undefined)).toBeNull();
  });
});
