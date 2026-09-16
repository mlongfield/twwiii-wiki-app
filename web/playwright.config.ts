import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "test/e2e",
  // 60s: `astro preview` is serving a dist/ built from all 26,637 pages of the real
  // model, and some tests wait on an island hydrating and fetching data (the search
  // index, the culture-chains file) before it settles.
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: true,
  reporter: [["list"]],
  use: { baseURL: "http://localhost:4321", trace: "off" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    // `astro preview` (7.3.2) always daemonizes: the launched command detaches once the
    // server is up and exits 0, which Playwright reads as "process exited early" if
    // nothing was already listening on the port. Start `npm run preview -- --port 4321`
    // yourself first if a cold `npm run test:e2e` fails with that error; this config's
    // `reuseExistingServer: true` then finds it and proceeds normally.
    command: "npm run preview -- --port 4321",
    url: "http://localhost:4321/",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
