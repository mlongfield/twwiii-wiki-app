import { describe, expect, it } from "vitest";
import { type GameTextImages, parseGameText, renderGameTextHtml } from "../../src/lib/gameText";

const images: GameTextImages = {
  inline: { icon_hero: "ui/skins/default/icon_agent_small.png", icon_gone: null },
  src: (p) => `/images/${p}`,
};
const html = (text: string | null) => renderGameTextHtml(text, images);
const PLACEHOLDER = '<span class="game-img game-img-inline placeholder" data-placeholder-image aria-hidden="true"></span>';

describe("parseGameText", () => {
  it("builds a node tree", () => {
    expect(parseGameText("[[b]]x")).toEqual({
      title: null,
      body: [{ kind: "span", style: "bold", colour: null, children: [{ kind: "text", text: "x" }] }],
    });
  });

  it("splits a title at the first ||", () => {
    const parsed = parseGameText("Rampage||A unit||more");
    expect(parsed.title).toEqual([{ kind: "text", text: "Rampage" }]);
    expect(parsed.body).toEqual([{ kind: "text", text: "A unit||more" }]);
  });
});

describe("renderGameTextHtml", () => {
  it("escapes plain text and handles empty input", () => {
    expect(html("a < b & \"c\"")).toBe("a &lt; b &amp; &quot;c&quot;");
    expect(html(null)).toBe("");
    expect(html("")).toBe("");
  });

  it("renders bold, italic, help and colour tags", () => {
    expect(html("[[b]]x[[/b]] [[i]]y[[/i]] [[sl:campaign_armies]]z[[/sl]] [[col:red]]r[[/col]]")).toBe(
      '<strong>x</strong> <em>y</em> <span class="gt-help">z</span> <span class="gt-col gt-col-red">r</span>',
    );
    expect(html("[[overridecol:fe_white]]w[[/overridecol]]")).toBe('<span class="gt-col gt-col-fe-white">w</span>');
    expect(html("[[col:blue]]b[[/col]]")).toBe('<span class="gt-col">b</span>');
  });

  it("tolerates nesting, mismatched, stray and unclosed tags", () => {
    expect(html("A [[b]][[col:red]]Rampaging[[/col]][[/b]] unit")).toBe(
      'A <strong><span class="gt-col gt-col-red">Rampaging</span></strong> unit',
    );
    expect(html("[[b]]Corrupt Units[[/i]] allows")).toBe("<strong>Corrupt Units</strong> allows");
    expect(html("[[b]]open")).toBe("<strong>open</strong>");
    expect(html("x[[/b]]y")).toBe("xy");
  });

  it("turns literal and real newlines into line breaks", () => {
    expect(html("a\\nb")).toBe("a<br>b");
    expect(html("a\nb")).toBe("a<br>b");
  });

  it("renders a title line", () => {
    expect(html("Rampage||A [[b]]unit[[/b]]")).toBe('<span class="gt-title">Rampage</span>A <strong>unit</strong>');
  });

  it("shows unresolved and unknown tokens as text", () => {
    expect(html("{{tr:research}}: [[foo:bar]] [[baz]]")).toBe("tr:research: foo:bar baz");
  });

  it("renders inline icons through inline.json and placeholders otherwise", () => {
    expect(html("[[img:icon_hero]][[/img]]Hero")).toBe(
      '<img class="game-img game-img-inline" src="/images/ui/skins/default/icon_agent_small.png" alt="" loading="lazy" decoding="async">Hero',
    );
    expect(html("[[img:icon_gone]][[/img]]")).toBe(PLACEHOLDER);
    expect(html("[[img:unknown]][[/img]]")).toBe(PLACEHOLDER);
  });

  it("shows a placeholder when the resolved image file is not available", () => {
    const noFiles: GameTextImages = { inline: images.inline, src: () => null };
    expect(renderGameTextHtml("[[img:icon_hero]][[/img]]", noFiles)).toBe(PLACEHOLDER);
  });
});
