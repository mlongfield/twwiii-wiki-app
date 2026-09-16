import { mkdtemp, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { findModelDir } from "../../src/data/modelDir";
import { ModelLoadError } from "../../src/data/load";

async function fakeModel(root: string, name: string, generatedAt: string) {
  await mkdir(path.join(root, name), { recursive: true });
  await writeFile(path.join(root, name, "manifest.json"), JSON.stringify({ build_id: name, generated_at: generatedAt }));
}

describe("findModelDir", () => {
  it("uses MODEL_DIR when set", async () => {
    expect(await findModelDir("/unused", { MODEL_DIR: "some/dir" })).toBe(path.resolve("some/dir"));
  });

  it("picks the newest model by generated_at and ignores staging directories", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "models-"));
    await fakeModel(root, "old", "2026-01-01T00:00:00+00:00");
    await fakeModel(root, "new", "2026-09-15T00:00:00+00:00");
    await fakeModel(root, "newer.partial", "2026-12-01T00:00:00+00:00");
    expect(await findModelDir(root, {})).toBe(path.join(root, "new"));
  });

  it("fails clearly when no model exists", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "models-"));
    await expect(findModelDir(root, {})).rejects.toThrow(ModelLoadError);
    await expect(findModelDir(root, {})).rejects.toThrow(/no model found/);
  });
});
