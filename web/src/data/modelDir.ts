import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { ModelLoadError } from "./load";

/** MODEL_DIR if set, else the newest model under modelRoot by manifest generated_at. */
export async function findModelDir(modelRoot: string, env: NodeJS.ProcessEnv = process.env): Promise<string> {
  if (env.MODEL_DIR) return path.resolve(env.MODEL_DIR);
  let names: string[] = [];
  try {
    names = await readdir(modelRoot);
  } catch {
    names = [];
  }
  let best: { dir: string; generatedAt: string } | null = null;
  for (const name of names) {
    if (name.endsWith(".partial") || name.endsWith(".old")) continue;
    const dir = path.join(modelRoot, name);
    try {
      const manifest = JSON.parse(await readFile(path.join(dir, "manifest.json"), "utf-8"));
      const generatedAt = String(manifest.generated_at ?? "");
      if (!best || generatedAt > best.generatedAt) best = { dir, generatedAt };
    } catch {
      continue;
    }
  }
  if (!best) {
    throw new ModelLoadError(
      `no model found under ${modelRoot}; run \`uv run python -m twwiki.model\` in the repository root or set MODEL_DIR`,
    );
  }
  return best.dir;
}
