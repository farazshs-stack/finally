/**
 * Smoke tests — basic connectivity and sanity checks.
 * These run AFTER finally.spec.ts (alphabetical order) so the DB may have
 * existing trades; assertions are tolerant of that.
 */

import { expect, test } from "@playwright/test";

test.describe("FinAlly smoke", () => {
  test("health endpoint returns ok", async ({ request }) => {
    const resp = await request.get("/api/health");
    expect(resp.ok()).toBeTruthy();
    const json = await resp.json();
    expect(json.status).toBe("ok");
  });

  test("home page loads and shows watchlist", async ({ page }) => {
    await page.goto("/");
    // Use testid to avoid strict-mode violations (AAPL appears in multiple places)
    await expect(page.getByTestId("watchlist-row-AAPL")).toBeVisible();
  });

  test("cash-balance element is visible with a dollar amount", async ({ page }) => {
    await page.goto("/");
    // The header shows cash balance — by this point trades may have occurred.
    // Just verify the element exists and shows a dollar amount.
    const cashEl = page.getByTestId("cash-balance");
    await expect(cashEl).toBeVisible();
    const text = await cashEl.textContent();
    expect(text).toMatch(/^\$/);
  });

  test("connection-dot is visible", async ({ page }) => {
    await page.goto("/");
    const dot = page.getByTestId("connection-dot");
    await expect(dot).toBeVisible();
    await expect(dot).toHaveAttribute("data-status", "connected", { timeout: 15_000 });
  });
});
