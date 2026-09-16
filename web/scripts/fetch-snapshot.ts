/**
 * Download a published model snapshot from Cloud Storage for the site build.
 *
 *   npx tsx scripts/fetch-snapshot.ts --project twwiii-wiki --bucket <bucket> [--build-id ID] [--out ../model]
 *
 * Without --build-id it uses Firestore `site/current`. The build must be "ready".
 * Progress goes to stderr; the last stdout line is the model folder, for MODEL_DIR.
 * Credentials: GOOGLE_APPLICATION_CREDENTIALS (the deploy workflow) or Application Default Credentials.
 */
import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

export interface SnapshotSource {
  getDocument(docPath: string): Promise<Record<string, unknown> | null>;
  listFiles(prefix: string): Promise<string[]>;
  download(name: string, destination: string): Promise<void>;
}

export class SnapshotError extends Error {}

export interface FetchOptions {
  buildId?: string;
  out: string;
  concurrency?: number;
  log?: (message: string) => void;
}

export async function resolveBuildId(source: SnapshotSource, buildId?: string): Promise<string> {
  let id = buildId;
  if (!id) {
    const current = await source.getDocument("site/current");
    id = typeof current?.build_id === "string" ? current.build_id : undefined;
    if (!id) throw new SnapshotError("site/current names no build; publish a build first or pass --build-id");
  }
  const build = await source.getDocument(`builds/${id}`);
  const status = typeof build?.status === "string" ? build.status : "missing";
  if (status !== "ready") throw new SnapshotError(`build ${id} is not ready (status: ${status})`);
  return id;
}

export async function fetchSnapshot(source: SnapshotSource, options: FetchOptions): Promise<string> {
  const log = options.log ?? (() => {});
  const buildId = await resolveBuildId(source, options.buildId);
  const prefix = `builds/${buildId}/`;
  const names = (await source.listFiles(prefix)).filter((name) => !name.endsWith("/"));
  if (names.length === 0) throw new SnapshotError(`no snapshot files under ${prefix}`);

  const target = path.join(options.out, buildId);
  const queue = [...names];
  const workerCount = Math.min(options.concurrency ?? 16, queue.length);
  await Promise.all(
    Array.from({ length: workerCount }, async () => {
      for (let name = queue.shift(); name !== undefined; name = queue.shift()) {
        const destination = path.join(target, ...name.slice(prefix.length).split("/"));
        await mkdir(path.dirname(destination), { recursive: true });
        await source.download(name, destination);
      }
    }),
  );
  log(`downloaded ${names.length} files for build ${buildId}`);

  let manifestBuild: unknown;
  try {
    manifestBuild = JSON.parse(await readFile(path.join(target, "manifest.json"), "utf-8")).build_id;
  } catch {
    throw new SnapshotError(`snapshot for build ${buildId} has no readable manifest.json`);
  }
  if (manifestBuild !== buildId) {
    throw new SnapshotError(`manifest.json in snapshot ${buildId} names build ${String(manifestBuild)}`);
  }
  return target;
}

async function firebaseSource(projectId: string, bucketName: string) {
  const { deleteApp, initializeApp } = await import("firebase-admin/app");
  const { getFirestore } = await import("firebase-admin/firestore");
  const { getStorage } = await import("firebase-admin/storage");
  const app = initializeApp({ projectId, storageBucket: bucketName });
  const db = getFirestore(app);
  const bucket = getStorage(app).bucket(bucketName);
  const source: SnapshotSource = {
    async getDocument(docPath) {
      const snapshot = await db.doc(docPath).get();
      return snapshot.exists ? (snapshot.data() ?? null) : null;
    },
    async listFiles(prefix) {
      const [files] = await bucket.getFiles({ prefix });
      return files.map((file) => file.name);
    },
    async download(name, destination) {
      await bucket.file(name).download({ destination });
    },
  };
  return { source, close: () => deleteApp(app) };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const defaultOut = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "model");
  const { values } = parseArgs({
    options: {
      project: { type: "string" },
      bucket: { type: "string" },
      "build-id": { type: "string" },
      out: { type: "string", default: defaultOut },
    },
  });
  if (!values.project || !values.bucket) {
    console.error("usage: tsx scripts/fetch-snapshot.ts --project ID --bucket NAME [--build-id ID] [--out DIR]");
    process.exitCode = 2;
  } else {
    const { source, close } = await firebaseSource(values.project, values.bucket);
    try {
      const dir = await fetchSnapshot(source, {
        buildId: values["build-id"],
        out: path.resolve(values.out),
        log: (message) => console.error(message),
      });
      console.log(dir);
    } catch (e) {
      console.error(e instanceof SnapshotError ? `fetch-snapshot: ${e.message}` : e);
      process.exitCode = 1;
    } finally {
      await close();
    }
  }
}
