import { createHash } from "node:crypto";

/** Lower-case key with every character outside [a-z0-9_-] replaced by "-". */
export function baseSlug(key: string): string {
  return key.toLowerCase().replace(/[^a-z0-9_-]/g, "-");
}

function shortHash(key: string): string {
  return createHash("sha1").update(key).digest("hex").slice(0, 6);
}

/** Slugs for one entity type; keys whose base slugs collide get a hash suffix. */
export function buildSlugs(keys: Iterable<string>): Map<string, string> {
  const byBase = new Map<string, string[]>();
  for (const key of keys) {
    const base = baseSlug(key);
    const group = byBase.get(base);
    if (group) group.push(key);
    else byBase.set(base, [key]);
  }
  const slugs = new Map<string, string>();
  for (const [base, group] of byBase) {
    if (group.length === 1) slugs.set(group[0], base);
    else for (const key of group) slugs.set(key, `${base}-${shortHash(key)}`);
  }
  return slugs;
}
