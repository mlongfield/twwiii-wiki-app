/** CSS for game text colours ([[col:…]]), generated from reference/colours.json by the prebuild. */
export interface ColourDefinition {
  key: string;
  dark_hex: string;
}

function slug(key: string): string {
  return key.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

export function colourClassName(key: string): string {
  return `gt-col-${slug(key)}`;
}

export function colourVariable(key: string): string {
  return `--col-${slug(key)}`;
}

export function coloursCss(colours: ColourDefinition[]): string {
  const sorted = [...colours].sort((a, b) => a.key.localeCompare(b.key));
  const variables = sorted.map((c) => `  ${colourVariable(c.key)}: ${c.dark_hex};`).join("\n");
  const rules = sorted.map((c) => `.${colourClassName(c.key)} { color: var(${colourVariable(c.key)}); }`).join("\n");
  return `/* Generated from reference/colours.json by scripts/prebuild.ts. Do not edit. */\n:root {\n${variables}\n}\n${rules}\n`;
}
