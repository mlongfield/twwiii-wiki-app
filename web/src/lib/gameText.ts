/** Game UI markup: [[b]], [[i]], [[sl:…]], [[col:…]], [[overridecol:…]], [[img:…]], {{…}}, \n and title||body. */
import { escapeHtml } from "./html";

export type GameNode =
  | { kind: "text"; text: string }
  | { kind: "br" }
  | { kind: "img"; target: string }
  | { kind: "span"; style: "bold" | "italic" | "help" | "colour"; colour: string | null; children: GameNode[] };

type SpanNode = Extract<GameNode, { kind: "span" }>;

export interface ParsedGameText {
  title: GameNode[] | null;
  body: GameNode[];
}

export interface GameTextImages {
  inline: Record<string, string | null>;
  src: (path: string) => string | null;
}

export const KNOWN_COLOURS: readonly string[] = ["yellow", "white", "red", "green", "magic", "fe_white", "ancillary_unique"];

// [[/name:arg]] tags, {{…}} tokens, a literal backslash-n, or a real newline.
const TOKEN = /\[\[(\/?)([A-Za-z_]+)(?::([^\]]*))?\]\]|\{\{([^}]*)\}\}|\\n|\r?\n/g;

const STYLES: Record<string, SpanNode["style"]> = { b: "bold", i: "italic", sl: "help", col: "colour", overridecol: "colour" };

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
    const [, closing, name, arg, braces] = match;
    if (braces !== undefined) {
      pushText(braces);
      continue;
    }
    if (name === undefined) {
      current().push({ kind: "br" });
      continue;
    }
    const tag = name.toLowerCase();
    if (closing) {
      // Game data sometimes closes the wrong tag: close the innermost open one. [[/img]] closes nothing.
      if (tag !== "img" && stack.length) stack.pop();
      continue;
    }
    if (tag === "img") {
      if (arg) current().push({ kind: "img", target: arg });
      continue;
    }
    const style = STYLES[tag];
    if (!style) {
      pushText(arg !== undefined ? `${name}:${arg}` : name);
      continue;
    }
    const span: SpanNode = { kind: "span", style, colour: style === "colour" ? (arg ?? null) : null, children: [] };
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
          const inner = renderNodes(node.children, images);
          if (node.style === "bold") return `<strong>${inner}</strong>`;
          if (node.style === "italic") return `<em>${inner}</em>`;
          if (node.style === "help") return `<span class="gt-help">${inner}</span>`;
          const colourClass =
            node.colour && KNOWN_COLOURS.includes(node.colour) ? ` gt-col-${node.colour.replace(/_/g, "-")}` : "";
          return `<span class="gt-col${colourClass}">${inner}</span>`;
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
