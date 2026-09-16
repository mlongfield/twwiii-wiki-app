import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  type RulesTestEnvironment,
  assertFails,
  assertSucceeds,
  initializeTestEnvironment,
} from "@firebase/rules-unit-testing";
import { collection, deleteDoc, doc, getDoc, getDocs, setDoc } from "firebase/firestore";
import { getBytes, ref, uploadString } from "firebase/storage";
import { afterAll, beforeAll, describe, it } from "vitest";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
const emulatorsRunning = Boolean(
  process.env.FIRESTORE_EMULATOR_HOST && process.env.FIREBASE_STORAGE_EMULATOR_HOST,
);

describe.skipIf(!emulatorsRunning)("security rules", () => {
  let env: RulesTestEnvironment;

  beforeAll(async () => {
    env = await initializeTestEnvironment({
      projectId: "demo-twwiki",
      firestore: { rules: readFileSync(path.join(repoRoot, "firestore.rules"), "utf-8") },
      storage: { rules: readFileSync(path.join(repoRoot, "storage.rules"), "utf-8") },
    });
    await env.withSecurityRulesDisabled(async (context) => {
      const db = context.firestore();
      await setDoc(doc(db, "site/current"), { build_id: "b1" });
      await setDoc(doc(db, "builds/b1"), { status: "ready" });
      await setDoc(doc(db, "builds/b1/unit/u1"), { key: "u1" });
      await setDoc(doc(db, "private/x"), { secret: true });
      await uploadString(ref(context.storage(), "builds/b1/manifest.json"), "{}");
    });
  });

  afterAll(async () => {
    await env?.cleanup();
  });

  it("lets anyone read the current pointer, builds and entity documents", async () => {
    const db = env.unauthenticatedContext().firestore();
    await assertSucceeds(getDoc(doc(db, "site/current")));
    await assertSucceeds(getDoc(doc(db, "builds/b1")));
    await assertSucceeds(getDoc(doc(db, "builds/b1/unit/u1")));
    await assertSucceeds(getDocs(collection(db, "builds/b1/unit")));
  });

  it("rejects browser writes, signed in or not", async () => {
    for (const db of [env.unauthenticatedContext().firestore(), env.authenticatedContext("someone").firestore()]) {
      await assertFails(setDoc(doc(db, "site/current"), { build_id: "evil" }));
      await assertFails(setDoc(doc(db, "builds/b1"), { status: "loading" }));
      await assertFails(setDoc(doc(db, "builds/b1/unit/u1"), { key: "changed" }));
      await assertFails(deleteDoc(doc(db, "builds/b1/unit/u1")));
    }
  });

  it("denies other Firestore paths", async () => {
    await assertFails(getDoc(doc(env.unauthenticatedContext().firestore(), "private/x")));
  });

  it("denies all browser access to Cloud Storage", async () => {
    for (const storage of [env.unauthenticatedContext().storage(), env.authenticatedContext("someone").storage()]) {
      await assertFails(getBytes(ref(storage, "builds/b1/manifest.json")));
      await assertFails(uploadString(ref(storage, "builds/b1/evil.json"), "{}"));
    }
  });
});
