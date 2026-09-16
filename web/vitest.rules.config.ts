import { defineConfig } from "vitest/config";

// Rules tests need the Firebase emulators: run them with `npm run test:rules`.
export default defineConfig({
  test: {
    include: ["test/rules/**/*.test.ts"],
    testTimeout: 30_000,
    hookTimeout: 60_000,
    fileParallelism: false,
  },
});
