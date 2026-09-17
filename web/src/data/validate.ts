import { access, readFile } from "node:fs/promises";
import path from "node:path";
import { ModelLoadError, type Manifest } from "./load";
import { ENTITY_TYPES } from "./pageTypes";

export const MODEL_VERSION = 3;
export const REFERENCE_FILES = ["campaigns", "colours", "ui_labels"] as const;

export async function validateModelDir(dir: string): Promise<Manifest> {
  let manifest: Manifest;
  try {
    manifest = JSON.parse(await readFile(path.join(dir, "manifest.json"), "utf-8"));
  } catch {
    throw new ModelLoadError(`${dir}: manifest.json is missing or unreadable`);
  }
  if (manifest.model_version !== MODEL_VERSION) {
    throw new ModelLoadError(
      `${dir}: model_version ${manifest.model_version}, expected ${MODEL_VERSION}; rebuild the model with \`uv run python -m twwiki.model\``,
    );
  }
  const missing: string[] = [];
  for (const type of ENTITY_TYPES) {
    try {
      await access(path.join(dir, "entities", `${type}.jsonl`));
    } catch {
      missing.push(`${type}.jsonl`);
    }
  }
  if (missing.length) throw new ModelLoadError(`${dir}: missing entity files: ${missing.join(", ")}`);
  const missingReference: string[] = [];
  for (const name of REFERENCE_FILES) {
    try {
      await access(path.join(dir, "reference", `${name}.json`));
    } catch {
      missingReference.push(`reference/${name}.json`);
    }
  }
  if (missingReference.length) throw new ModelLoadError(`${dir}: missing reference files: ${missingReference.join(", ")}`);
  return manifest;
}
