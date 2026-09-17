import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { ModelLoadError, loadModel, readJsonl } from "../../src/data/load";

export const FIXTURE = path.resolve(__dirname, "../fixtures/model");

describe("loadModel", () => {
  it("loads the fixture model", async () => {
    const model = await loadModel(FIXTURE);
    expect(model.manifest.model_version).toBe(3);
    expect(model.entities.unit.get("wh_main_emp_inf_greatswords")?.name).toBe("Greatswords");
    expect(model.entities.character.has("wh_main_emp_karl_franz")).toBe(true);
    expect(model.entities.skill.size).toBe(53);
    expect(model.entities.technology.size).toBe(136);
    expect(model.entities.region.size).toBe(4);
    expect(model.entities.building_level.size).toBe(9);
    expect(model.entities.effect_bundle.size).toBe(0);
    expect(typeof model.inline).toBe("object");
    expect(model.reference.campaigns.map((c) => c.key)).toEqual(["wh3_main_chaos", "wh3_main_combi", "wh3_main_prologue"]);
    expect(model.reference.colours.find((c) => c.key === "magic")?.dark_hex).toMatch(/^#[0-9A-F]{6}$/);
    expect(model.reference.ui_labels.duration).toBe("Duration");
    expect(model.entities.campaign.size).toBe(3);
  });
});

describe("readJsonl", () => {
  it("names the file and line of invalid JSON", async () => {
    const dir = await mkdtemp(path.join(tmpdir(), "jsonl-"));
    const file = path.join(dir, "unit.jsonl");
    await writeFile(file, '{"key": "a"}\n{not json\n');
    await expect(readJsonl(file)).rejects.toThrow(ModelLoadError);
    await expect(readJsonl(file)).rejects.toThrow(/unit\.jsonl:2: invalid JSON/);
  });

  it("rejects entities without a string key", async () => {
    const dir = await mkdtemp(path.join(tmpdir(), "jsonl-"));
    const file = path.join(dir, "unit.jsonl");
    await writeFile(file, '{"name": "x"}\n');
    await expect(readJsonl(file)).rejects.toThrow(/unit\.jsonl:1: entity has no string "key"/);
  });

  it("skips blank lines", async () => {
    const dir = await mkdtemp(path.join(tmpdir(), "jsonl-"));
    const file = path.join(dir, "unit.jsonl");
    await writeFile(file, '{"key": "a"}\n\n{"key": "b"}\n');
    expect([...(await readJsonl(file)).keys()]).toEqual(["a", "b"]);
  });
});
