import { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { summarizeDist } from "../../scripts/build-report";

async function page(dist: string, relative: string, html: string) {
  await mkdir(path.join(dist, relative), { recursive: true });
  await writeFile(path.join(dist, relative, "index.html"), html);
}

describe("summarizeDist", () => {
  it("counts pages per segment, gaps and the search index size", async () => {
    const dist = await mkdtemp(path.join(tmpdir(), "dist-"));
    await page(dist, ".", "<html>home</html>");
    await page(dist, "units", "<html>browse</html>");
    await page(dist, "units/a", '<span data-missing-link>x</span><span data-placeholder-image></span>');
    await page(dist, "units/b", '<span data-placeholder-image></span><span class="gt-col" data-unknown-colour="blue">x</span>');
    await page(dist, "regions/c", "<html>region</html>");
    await writeFile(path.join(dist, "search-index.json"), "12345");

    const summary = await summarizeDist(dist);

    expect(summary.pages).toEqual({ "(root)": 1, units: 3, regions: 1 });
    expect(summary.total).toBe(5);
    expect(summary.missingLinks).toBe(1);
    expect(summary.placeholderImages).toBe(2);
    expect(summary.unknownColours).toBe(1);
    expect(summary.searchIndexBytes).toBe(5);
  });

  it("reports zero for a search index that is not there", async () => {
    const dist = await mkdtemp(path.join(tmpdir(), "dist-"));
    await page(dist, ".", "<html>home</html>");
    expect((await summarizeDist(dist)).searchIndexBytes).toBe(0);
  });
});
