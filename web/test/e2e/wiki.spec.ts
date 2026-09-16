import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const distIndex = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../dist/index.html");

// Astro islands (`client:visible` / `client:idle`) render static SSR markup first and
// only attach their event handlers once they hydrate. A click or a select fired before
// that finishes is lost silently (the DOM updates, but no handler is listening yet) and
// nothing retries it, so tests that interact with an island must wait for it to become
// interactive first — `ssr` is removed from the <astro-island> element once hydration
// completes. Just polling the *result* of an interaction (as most `expect(...)` calls
// already do) isn't enough here, because the one-shot interaction itself can be missed.
async function waitForHydrated(page: import("@playwright/test").Page, componentUrlPart: string) {
  await expect(page.locator(`astro-island[component-url*="${componentUrlPart}"][ssr]`)).toHaveCount(0);
}

test.describe("wiki", () => {
  test.skip(!existsSync(distIndex), "run `npm run build` first");

  test("unit page shows stats and a card image", async ({ page }) => {
    await page.goto("/units/wh_main_emp_inf_greatswords/");
    await expect(page.locator("h1")).toHaveText("Greatswords");
    const row = page.locator("tr", { has: page.getByRole("rowheader", { name: "Melee attack", exact: true }) });
    await expect(row.locator("td")).toHaveText("32");
    const card = page.locator("img.game-img-card").first();
    await expect(card).toBeVisible();
    // The card image loads with native `loading="lazy"`, so the browser defers the
    // fetch by a frame or two after the element becomes visible; poll instead of
    // reading naturalWidth once immediately after toBeVisible() resolves.
    await expect
      .poll(() => card.evaluate((img: HTMLImageElement) => img.naturalWidth))
      .toBeGreaterThan(0);
  });

  test("skill tree shows details for the selected skill", async ({ page }) => {
    await page.goto("/characters/wh_main_emp_karl_franz/");
    const node = page.locator("button.tree-node", { hasText: "Devastating Charge" }).first();
    await node.scrollIntoViewIfNeeded();
    await waitForHydrated(page, "TreeView");
    await node.click();
    await expect(page.locator(".tree-panel h3")).toHaveText("Devastating Charge");
  });

  test("skill tree collapses to lines on a narrow screen", async ({ page }) => {
    await page.setViewportSize({ width: 400, height: 800 });
    await page.goto("/characters/wh_main_emp_karl_franz/");
    // The tree island only hydrates once it scrolls into view (client:visible), and on
    // Karl Franz's full real page the skill tree sits well below the fold; scroll to it
    // first so the narrow-screen switch to line view actually fires.
    await page.locator("button.tree-node").first().scrollIntoViewIfNeeded();
    await expect(page.locator(".tree-lines").first()).toBeVisible();
  });

  test("region page lists special slots and swaps chains per culture", async ({ page }) => {
    await page.goto("/regions/wh3_main_combi_region_altdorf/");
    await expect(page.getByText("wh_main_special_altdorf_primary")).toBeVisible();
    const picker = page.locator(".culture-picker");
    await picker.scrollIntoViewIfNeeded();
    await waitForHydrated(page, "CulturePicker");
    const chains = picker.locator(".chain-group li");
    const before = await chains.count();
    expect(before).toBeGreaterThan(0);
    const select = picker.locator("select");
    const other = await select.locator("option").nth(3).getAttribute("value");
    await select.selectOption(other!);
    await expect(picker.getByText("building chains")).toBeVisible();
    await expect.poll(async () => chains.count(), { timeout: 10_000 }).not.toBe(before);
  });

  test("search finds a unit and opens it", async ({ page }) => {
    await page.goto("/");
    await waitForHydrated(page, "SearchBox");
    const box = page.getByLabel("Search the wiki");
    await box.click();
    await box.fill("greatswords");
    const hit = page.locator("a.search-hit", { hasText: "Greatswords" }).first();
    await expect(hit).toBeVisible({ timeout: 15_000 });
    await box.press("Enter");
    await expect(page).toHaveURL(/\/units\//);
  });

  test("browse page lists every unit", async ({ page }) => {
    await page.goto("/units/");
    await expect(page.locator("#browse-table tbody tr")).toHaveCount(2609);
  });

  test("unknown pages show the 404 page", async ({ page }) => {
    const response = await page.goto("/effects/anything/");
    expect(response?.status()).toBe(404);
    await expect(page.locator("h1")).toHaveText("Page not found");
  });
});
