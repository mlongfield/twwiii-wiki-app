/** Game UI markup: [[b]], [[i]], [[col:…]], [[overridecol:…]], [[img:…]], [[opacity:…]], other tags, {{…}}, \n and title||body. */
import { colourClassName } from "./coloursCss";
import { escapeHtml } from "./html";

export type SpanStyle = "bold" | "italic" | "colour" | "hidden" | "plain";

export type GameNode =
  | { kind: "text"; text: string }
  | { kind: "br" }
  | { kind: "img"; target: string }
  | { kind: "span"; tag: string; style: SpanStyle; colour: string | null; children: GameNode[] };

type SpanNode = Extract<GameNode, { kind: "span" }>;

export interface ParsedGameText {
  title: GameNode[] | null;
  body: GameNode[];
}

export interface GameTextImages {
  inline: Record<string, string | null>;
  src: (path: string) => string | null;
  /** Lower-case ui_colours keys. When given, other col: names render uncoloured and marked. */
  colours?: ReadonlySet<string>;
}

// [[/name:arg]] tags, {{…}} tokens, a literal backslash-n, or a real newline.
const TOKEN = /\[\[(\/?)([A-Za-z_]+)(?::([^\]]*))?\]\]|\{\{[^}]*\}\}|\\n|\r?\n/g;

function spanStyle(tag: string, arg: string | undefined): SpanStyle {
  if (tag === "b") return "bold";
  if (tag === "i") return "italic";
  if (tag === "col" || tag === "overridecol") return "colour";
  if (tag === "opacity" && arg !== undefined && arg.trim() !== "" && Number(arg) === 0) return "hidden";
  // sl, sl_link, sl_tooltip, url, tooltip, fragment, opacity > 0 and unknown tags show their inner text.
  return "plain";
}

function parseNodes(text: string): GameNode[] {
  const root: GameNode[] = [];
  const stack: SpanNode[] = [];
  const current = () => (stack.length ? stack[stack.length - 1].children : root);
  const pushText = (value: string) => {
    if (!value) return;
    const nodes = current();
    const last = nodes[nodes.length - 1];
    if (last && last.kind === "text") last.text += value;
    else nodes.push({ kind: "text", text: value });
  };

  let pos = 0;
  for (const match of text.matchAll(TOKEN)) {
    pushText(text.slice(pos, match.index));
    pos = match.index! + match[0].length;
    const [whole, closing, name, arg] = match;
    if (whole.startsWith("{{")) continue;
    if (name === undefined) {
      current().push({ kind: "br" });
      continue;
    }
    const tag = name.toLowerCase();
    if (closing) {
      // Close the most recent open tag with the same name; a close with no match is ignored.
      for (let i = stack.length - 1; i >= 0; i -= 1) {
        if (stack[i].tag === tag) {
          stack.length = i;
          break;
        }
      }
      continue;
    }
    if (tag === "img") {
      if (arg) current().push({ kind: "img", target: arg });
      continue;
    }
    const style = spanStyle(tag, arg);
    const span: SpanNode = { kind: "span", tag, style, colour: style === "colour" ? (arg ?? null) : null, children: [] };
    current().push(span);
    stack.push(span);
  }
  pushText(text.slice(pos));
  return root;
}

export function parseGameText(text: string): ParsedGameText {
  const separator = text.indexOf("||");
  if (separator === -1) return { title: null, body: parseNodes(text) };
  const title = text.slice(0, separator);
  return { title: title.trim() ? parseNodes(title) : null, body: parseNodes(text.slice(separator + 2)) };
}

function renderColour(node: SpanNode, inner: string, images: GameTextImages): string {
  const colour = node.colour?.trim().toLowerCase() ?? "";
  if (!colour) return `<span class="gt-col">${inner}</span>`;
  if (images.colours && !images.colours.has(colour)) {
    return `<span class="gt-col" data-unknown-colour="${escapeHtml(colour)}">${inner}</span>`;
  }
  return `<span class="gt-col ${colourClassName(colour)}">${inner}</span>`;
}

function renderNodes(nodes: GameNode[], images: GameTextImages): string {
  return nodes
    .map((node) => {
      switch (node.kind) {
        case "text":
          return escapeHtml(node.text);
        case "br":
          return "<br>";
        case "img": {
          const imagePath = images.inline[node.target];
          const src = imagePath ? images.src(imagePath) : null;
          return src
            ? `<img class="game-img game-img-inline" src="${escapeHtml(src)}" alt="" loading="lazy" decoding="async">`
            : '<span class="game-img game-img-inline placeholder" data-placeholder-image aria-hidden="true"></span>';
        }
        case "span": {
          if (node.style === "hidden") return "";
          const inner = renderNodes(node.children, images);
          if (node.style === "bold") return `<strong>${inner}</strong>`;
          if (node.style === "italic") return `<em>${inner}</em>`;
          if (node.style === "plain") return inner;
          return renderColour(node, inner, images);
        }
      }
    })
    .join("");
}

export function renderGameTextHtml(text: string | null | undefined, images: GameTextImages): string {
  if (!text) return "";
  const { title, body } = parseGameText(text);
  const bodyHtml = renderNodes(body, images);
  return title ? `<span class="gt-title">${renderNodes(title, images)}</span>${bodyHtml}` : bodyHtml;
}

/** Plain text for places that can't show markup: tags and {{…}} tokens removed. */
export function stripGameMarkup(text: string): string {
  return text.replace(/\[\[[^\]]*\]\]|\{\{[^}]*\}\}/g, "").replace(/\s+/g, " ").trim();
}
