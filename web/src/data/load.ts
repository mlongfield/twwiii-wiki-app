import { createReadStream } from "node:fs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { createInterface } from "node:readline";
import type { EntityTypeMap } from "../generated/index";
import { ENTITY_TYPES, type EntityType } from "./pageTypes";

export class ModelLoadError extends Error {}

export interface Manifest {
  build_id: string;
  model_version: number;
  generated_at: string;
  counts: Record<string, number>;
}

export type EntityMaps = { [T in EntityType]: Map<string, EntityTypeMap[T]> };

export interface Model {
  dir: string;
  manifest: Manifest;
  inline: Record<string, string | null>;
  entities: EntityMaps;
}

export async function readJsonl<T extends { key: string }>(file: string): Promise<Map<string, T>> {
  const rows = new Map<string, T>();
  const lines = createInterface({ input: createReadStream(file, "utf-8"), crlfDelay: Infinity });
  let lineNo = 0;
  for await (const line of lines) {
    lineNo += 1;
    if (!line.trim()) continue;
    let row: unknown;
    try {
      row = JSON.parse(line);
    } catch (e) {
      throw new ModelLoadError(`${file}:${lineNo}: invalid JSON (${(e as Error).message})`);
    }
    const key = (row as { key?: unknown }).key;
    if (typeof key !== "string") throw new ModelLoadError(`${file}:${lineNo}: entity has no string "key"`);
    rows.set(key, row as T);
  }
  return rows;
}

export async function loadModel(dir: string): Promise<Model> {
  const manifest = JSON.parse(await readFile(path.join(dir, "manifest.json"), "utf-8")) as Manifest;
  let inline: Record<string, string | null> = {};
  try {
    inline = JSON.parse(await readFile(path.join(dir, "images", "inline.json"), "utf-8"));
  } catch {
    inline = {};
  }
  const loaded = await Promise.all(
    ENTITY_TYPES.map(async (type) => [type, await readJsonl(path.join(dir, "entities", `${type}.jsonl`))] as const),
  );
  return { dir, manifest, inline, entities: Object.fromEntries(loaded) as unknown as EntityMaps };
}
