import { describe, expect, it } from "vitest";
import { colourClassName, colourVariable, coloursCss } from "../../src/lib/coloursCss";

describe("coloursCss", () => {
  it("names classes and variables from lower-cased, hyphenated keys", () => {
    expect(colourClassName("Ancillary_Rare")).toBe("gt-col-ancillary-rare");
    expect(colourVariable("fe_white")).toBe("--col-fe-white");
  });

  it("writes one variable and one rule per colour, sorted by key, using the dark-background hex", () => {
    expect(coloursCss([{ key: "red", dark_hex: "#FF3333" }, { key: "fe_white", dark_hex: "#F4EFE4" }])).toBe(
      "/* Generated from reference/colours.json by scripts/prebuild.ts. Do not edit. */\n" +
        ":root {\n  --col-fe-white: #F4EFE4;\n  --col-red: #FF3333;\n}\n" +
        ".gt-col-fe-white { color: var(--col-fe-white); }\n.gt-col-red { color: var(--col-red); }\n",
    );
  });
});
