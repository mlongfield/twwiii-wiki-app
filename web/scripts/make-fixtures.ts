/** Regenerate test/fixtures/model from the real model: a small, consistent real subset. */
import { copyFile, cp, mkdir, readFile, rm, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { readJsonl } from "../src/data/load";
import { findModelDir } from "../src/data/modelDir";
import { ENTITY_TYPES, type EntityType } from "../src/data/pageTypes";
import { chainCultureKeys } from "../src/data/site";

type Row = { key: string; [field: string]: any };

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outDir = path.join(webRoot, "test", "fixtures", "model");

function collectEffectKeys(value: unknown, out: Set<string>): void {
  if (Array.isArray(value)) {
    for (const item of value) collectEffectKeys(item, out);
  } else if (value && typeof value === "object") {
    const obj = value as Record<string, unknown>;
    if (obj.type === "effect" && typeof obj.key === "string" && "missing" in obj) out.add(obj.key);
    for (const child of Object.values(obj)) collectEffectKeys(child, out);
  }
}

async function main(): Promise<void> {
  const source = await findModelDir(path.join(webRoot, "..", "model"));
  console.log(`reading ${source}`);
  const all = Object.fromEntries(
    await Promise.all(ENTITY_TYPES.map(async (t) => [t, await readJsonl<Row>(path.join(source, "entities", `${t}.jsonl`))] as const)),
  ) as Record<EntityType, Map<string, Row>>;
  const picked = Object.fromEntries(ENTITY_TYPES.map((t) => [t, new Set<string>()])) as Record<EntityType, Set<string>>;
  const add = (type: EntityType, key: string): Row => {
    const row = all[type].get(key);
    if (!row) throw new Error(`fixture entity ${type}:${key} is not in the model`);
    picked[type].add(key);
    return row;
  };

  add("unit", "wh_main_emp_inf_greatswords");
  const karl = add("character", "wh_main_emp_karl_franz");
  add("unit", karl.associated_unit.key);
  for (const tree of karl.skill_trees) for (const node of tree.nodes) add("skill", node.skill.key);
  add("ability", "wh_main_lord_passive_hold_the_line");
  add("item", "wh2_dlc09_anc_magic_standard_banner_of_the_hidden_dead");
  const techTree = add("technology_tree", "emp_civ_reworkd");
  for (const node of techTree.nodes) add("technology", node.technology.key);
  const province = add("province", "wh3_main_combi_province_reikland");
  for (const region of province.regions) add("region", region.key);
  add("culture", "wh_main_emp_empire");
  add("subculture", "wh_main_sc_emp_empire");
  add("subculture", "wh_main_sc_teb_teb");
  add("faction", "wh_main_emp_empire");

  for (const key of all.campaign.keys()) add("campaign", key);
  add("building_chain", "wh2_dlc09_special_settlement_khemri_tmb");
  const firstWith = (type: EntityType, test: (row: Row) => boolean, what: string): Row => {
    for (const row of all[type].values()) if (test(row)) return add(type, row.key);
    throw new Error(`the model has no ${type} with ${what}`);
  };
  const skillApps = (s: Row) => s.levels.flatMap((l: Row) => l.effects);
  firstWith("skill", (s) => skillApps(s).some((a: Row) => a.hidden), "a hidden effect");
  firstWith("skill", (s) => skillApps(s).some((a: Row) => a.favourable === false), "an unfavourable effect");
  firstWith("item", (i) => i.rarity !== null && i.rarity.colour !== null, "a coloured rarity");
  const restricted = firstWith("technology_tree", (t) => t.nodes.some((n: Row) => n.campaigns.length > 0), "a campaign-restricted node");
  for (const node of restricted.nodes) add("technology", node.technology.key);

  const subcultureCulture = (k: string) => all.subculture.get(k)?.culture?.key;
  const factionCulture = (k: string) => all.faction.get(k)?.culture?.key;
  for (const chain of all.building_chain.values()) {
    if (chainCultureKeys(chain.availability, subcultureCulture, factionCulture).has("wh_main_emp_empire")) {
      add("building_chain", chain.key);
    }
  }
  for (const chainKey of ["wh_main_EMPIRE_settlement_major", "wh_main_EMPIRE_barracks"]) {
    for (const level of add("building_chain", chainKey).levels) add("building_level", level.key);
  }

  const effects = new Set<string>();
  for (const type of ENTITY_TYPES) {
    if (type === "effect") continue;
    for (const key of picked[type]) collectEffectKeys(all[type].get(key), effects);
  }
  for (const key of effects) if (all.effect.has(key)) add("effect", key);

  await rm(outDir, { recursive: true, force: true });
  await mkdir(path.join(outDir, "entities"), { recursive: true });
  await mkdir(path.join(outDir, "images"), { recursive: true });
  const counts: Record<string, number> = {};
  let bytes = 0;
  for (const type of ENTITY_TYPES) {
    const lines = [...picked[type]].sort().map((key) => JSON.stringify(all[type].get(key)));
    const text = lines.length ? lines.join("\n") + "\n" : "";
    await writeFile(path.join(outDir, "entities", `${type}.jsonl`), text, "utf-8");
    counts[type] = lines.length;
    bytes += Buffer.byteLength(text);
  }
  const manifest = JSON.parse(await readFile(path.join(source, "manifest.json"), "utf-8"));
  await writeFile(
    path.join(outDir, "manifest.json"),
    JSON.stringify({ build_id: manifest.build_id, model_version: manifest.model_version, generated_at: manifest.generated_at, counts }, null, 2) + "\n",
  );
  await copyFile(path.join(source, "images", "inline.json"), path.join(outDir, "images", "inline.json"));
  await cp(path.join(source, "schema"), path.join(outDir, "schema"), { recursive: true });
  await cp(path.join(source, "reference"), path.join(outDir, "reference"), { recursive: true });
  console.log(counts);
  console.log(`entity bytes: ${bytes}; inline.json bytes: ${(await stat(path.join(outDir, "images", "inline.json"))).size}`);
}

await main();
