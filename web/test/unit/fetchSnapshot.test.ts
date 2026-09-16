import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { type SnapshotSource, SnapshotError, fetchSnapshot, resolveBuildId } from "../../scripts/fetch-snapshot";

type Docs = Record<string, Record<string, unknown>>;

function fakeSource(docs: Docs, files: Record<string, string>): SnapshotSource & { downloads: string[] } {
  const downloads: string[] = [];
  return {
    downloads,
    async getDocument(docPath) {
      return docs[docPath] ?? null;
    },
    async listFiles(prefix) {
      return Object.keys(files).filter((name) => name.startsWith(prefix));
    },
    async download(name, destination) {
      downloads.push(name);
      await writeFile(destination, files[name]);
    },
  };
}

const FILES = {
  "builds/b1/manifest.json": JSON.stringify({ build_id: "b1" }),
  "builds/b1/entities/unit.jsonl": '{"key":"u1"}\n',
  "builds/b1/images/ui/campaign ui/icon.png": "png",
  "builds/b2/manifest.json": JSON.stringify({ build_id: "b2" }),
};
const READY: Docs = {
  "site/current": { build_id: "b1" },
  "builds/b1": { status: "ready" },
  "builds/b2": { status: "ready" },
};

async function tempOut() {
  return mkdtemp(path.join(tmpdir(), "snapshot-"));
}

describe("fetchSnapshot", () => {
  it("downloads the current build into <out>/<build id>", async () => {
    const out = await tempOut();
    const source = fakeSource(READY, FILES);
    const dir = await fetchSnapshot(source, { out });
    expect(dir).toBe(path.join(out, "b1"));
    expect(await readFile(path.join(dir, "entities", "unit.jsonl"), "utf-8")).toBe('{"key":"u1"}\n');
    expect(await readFile(path.join(dir, "images", "ui", "campaign ui", "icon.png"), "utf-8")).toBe("png");
    expect(source.downloads.sort()).toEqual(Object.keys(FILES).filter((n) => n.startsWith("builds/b1/")).sort());
  });

  it("uses an explicit build id instead of site/current", async () => {
    const out = await tempOut();
    expect(await fetchSnapshot(fakeSource(READY, FILES), { out, buildId: "b2", concurrency: 1 })).toBe(
      path.join(out, "b2"),
    );
  });

  it("refuses builds that are not ready", async () => {
    const docs: Docs = { "site/current": { build_id: "b1" }, "builds/b1": { status: "loading" } };
    await expect(resolveBuildId(fakeSource(docs, FILES))).rejects.toThrow(/not ready \(status: loading\)/);
    await expect(resolveBuildId(fakeSource(READY, FILES), "b9")).rejects.toThrow(/not ready \(status: missing\)/);
  });

  it("fails when site/current names no build", async () => {
    await expect(resolveBuildId(fakeSource({}, FILES))).rejects.toThrow(SnapshotError);
    await expect(resolveBuildId(fakeSource({}, FILES))).rejects.toThrow(/names no build/);
  });

  it("fails when the snapshot is empty or its manifest names another build", async () => {
    const docs: Docs = { ...READY, "builds/b3": { status: "ready" }, "builds/b4": { status: "ready" } };
    const files = { ...FILES, "builds/b4/manifest.json": JSON.stringify({ build_id: "other" }) };
    await expect(fetchSnapshot(fakeSource(docs, files), { out: await tempOut(), buildId: "b3" })).rejects.toThrow(
      /no snapshot files under builds\/b3\//,
    );
    await expect(fetchSnapshot(fakeSource(docs, files), { out: await tempOut(), buildId: "b4" })).rejects.toThrow(
      /names build other/,
    );
  });
});
