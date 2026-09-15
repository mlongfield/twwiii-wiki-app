import { mkdtemp, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { ModelLoadError } from "../../src/data/load";
import { MODEL_VERSION, validateModelDir } from "../../src/data/validate";

const FIXTURE = path.resolve(__dirname, "../fixtures/model");

async function tempModel(manifest: object | null, entityTypes: string[]): Promise<string> {
  const dir = await mkdtemp(path.join(tmpdir(), "model-"));
  await mkdir(path.join(dir, "entities"));
  if (manifest) await writeFile(path.join(dir, "manifest.json"), JSON.stringify(manifest));
  for (const t of entityTypes) await writeFile(path.join(dir, "entities", `${t}.jsonl`), "");
  return dir;
}

describe("validateModelDir", () => {
  it("accepts the fixture model", async () => {
    const manifest = await validateModelDir(FIXTURE);
    expect(manifest.model_version).toBe(MODEL_VERSION);
    expect(typeof manifest.build_id).toBe("string");
  });

  it("rejects a directory without manifest.json", async () => {
    const dir = await tempModel(null, []);
    await expect(validateModelDir(dir)).rejects.toThrow(ModelLoadError);
    await expect(validateModelDir(dir)).rejects.toThrow(/manifest\.json is missing/);
  });

  it("rejects another model version", async () => {
    const dir = await tempModel({ build_id: "x", model_version: 1, generated_at: "", counts: {} }, []);
    await expect(validateModelDir(dir)).rejects.toThrow(/model_version 1, expected 2/);
  });

  it("lists missing entity files", async () => {
    const dir = await tempModel({ build_id: "x", model_version: 2, generated_at: "", counts: {} }, ["unit"]);
    await expect(validateModelDir(dir)).rejects.toThrow(/missing entity files: character\.jsonl/);
  });
});
