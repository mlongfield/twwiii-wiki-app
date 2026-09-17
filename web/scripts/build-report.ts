/** Prints what the build produced: pages per type, gaps rendered, search index size. */
import { readFile, readdir, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

export interface DistSummary {
  pages: Record<string, number>;
  total: number;
  missingLinks: number;
  placeholderImages: number;
  unknownColours: number;
  searchIndexBytes: number;
}

export async function summarizeDist(distDir: string): Promise<DistSummary> {
  const entries = await readdir(distDir, { recursive: true, withFileTypes: true });
  const pages: Record<string, number> = {};
  let total = 0;
  let missingLinks = 0;
  let placeholderImages = 0;
  let unknownColours = 0;

  for (const entry of entries) {
    if (!entry.isFile() || entry.name !== "index.html") continue;
    const file = path.join(entry.parentPath, entry.name);
    const relative = path.relative(distDir, file).split(path.sep).join("/");
    const segment = relative.includes("/") ? relative.split("/")[0] : "(root)";
    pages[segment] = (pages[segment] ?? 0) + 1;
    total += 1;
    const html = await readFile(file, "utf-8");
    missingLinks += (html.match(/data-missing-link/g) ?? []).length;
    placeholderImages += (html.match(/data-placeholder-image/g) ?? []).length;
    unknownColours += (html.match(/data-unknown-colour/g) ?? []).length;
  }

  const searchIndexBytes = await stat(path.join(distDir, "search-index.json")).then(
    (s) => s.size,
    () => 0,
  );
  return { pages, total, missingLinks, placeholderImages, unknownColours, searchIndexBytes };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const distDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "dist");
  const summary = await summarizeDist(distDir);
  console.log("\nbuild report");
  for (const [segment, count] of Object.entries(summary.pages).sort(([a], [b]) => a.localeCompare(b))) {
    console.log(`  ${segment.padEnd(18)} ${count}`);
  }
  console.log(`  ${"total pages".padEnd(18)} ${summary.total}`);
  console.log(`  ${"missing links".padEnd(18)} ${summary.missingLinks}`);
  console.log(`  ${"placeholder images".padEnd(18)} ${summary.placeholderImages}`);
  console.log(`  ${"unknown colours".padEnd(18)} ${summary.unknownColours}`);
  console.log(`  ${"search index".padEnd(18)} ${(summary.searchIndexBytes / 1024 / 1024).toFixed(1)} MB`);
}
