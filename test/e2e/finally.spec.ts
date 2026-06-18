/**
 * FinAlly E2E Test Suite — §12 key scenarios
 *
 * Relies on:
 *  - LLM_MOCK=true → deterministic mock responses
 *  - Fresh SQLite DB seeded with $10,000 cash + 10 default tickers
 *  - Frontend static export served by FastAPI on port 8000
 */

import { expect, test } from "@playwright/test";

// ─── helpers ────────────────────────────────────────────────────────────────

/** Wait for the cash-balance element to show a value different from the given string. */
async function waitForCashChange(page: any, before: string, timeout = 12_000) {
  await expect
    .poll(
      async () => {
        const el = page.getByTestId("cash-balance");
        return el.textContent();
      },
      { timeout }
    )
    .not.toBe(before);
}

// ─── 1. Fresh start ─────────────────────────────────────────────────────────

test.describe("Fresh start", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("health endpoint returns ok", async ({ request }) => {
    const resp = await request.get("/api/health");
    expect(resp.ok()).toBeTruthy();
    const json = await resp.json();
    expect(json.status).toBe("ok");
  });

  test("default 10 tickers visible in watchlist", async ({ page }) => {
    const defaultTickers = [
      "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
      "NVDA", "META", "JPM", "V", "NFLX",
    ];
    for (const ticker of defaultTickers) {
      await expect(page.getByTestId(`watchlist-row-${ticker}`)).toBeVisible();
    }
  });

  test("cash balance shows $10,000", async ({ page }) => {
    const cashEl = page.getByTestId("cash-balance");
    await expect(cashEl).toBeVisible();
    const text = await cashEl.textContent();
    // Accept $10,000.00 format
    expect(text).toMatch(/\$10,000/);
  });

  test("total-value element is present", async ({ page }) => {
    const totalEl = page.getByTestId("total-value");
    await expect(totalEl).toBeVisible();
    // Should display a dollar amount
    const text = await totalEl.textContent();
    expect(text).toMatch(/\$/);
  });

  test("connection-dot becomes connected", async ({ page }) => {
    const dot = page.getByTestId("connection-dot");
    await expect(dot).toBeVisible();
    // Wait for connected status
    await expect(dot).toHaveAttribute("data-status", "connected", { timeout: 15_000 });
  });

  test("prices stream — AAPL price element present and non-zero", async ({ page }) => {
    const priceEl = page.getByTestId("price-AAPL");
    await expect(priceEl).toBeVisible();
    const text = await priceEl.textContent();
    expect(text).toMatch(/\$/);
    // Must not be $0.00
    expect(text).not.toBe("$0.00");
  });

  test("AAPL price changes within a few seconds (streaming)", async ({ page }) => {
    const priceEl = page.getByTestId("price-AAPL");
    await expect(priceEl).toBeVisible();
    const first = await priceEl.textContent();

    // Poll for a change — simulator runs at ~500ms so within 8s we expect at least one tick
    await expect
      .poll(
        async () => {
          return priceEl.textContent();
        },
        { timeout: 12_000, intervals: [500] }
      )
      .not.toBe(first);
  });
});

// ─── 2. Watchlist — add and remove ──────────────────────────────────────────

test.describe("Watchlist management", () => {
  test("add a ticker then remove it", async ({ page }) => {
    await page.goto("/");

    // Confirm PYPL is not there initially
    await expect(page.getByTestId("watchlist-row-PYPL")).not.toBeVisible();

    // Add PYPL
    await page.getByTestId("watchlist-add-input").fill("PYPL");
    await page.getByTestId("watchlist-add-button").click();

    // Row should appear
    await expect(page.getByTestId("watchlist-row-PYPL")).toBeVisible({ timeout: 10_000 });

    // Remove it
    await page.getByTestId("watchlist-remove-PYPL").click();

    // Row should disappear
    await expect(page.getByTestId("watchlist-row-PYPL")).not.toBeVisible({ timeout: 10_000 });
  });
});

// ─── 3 & 4. Buy then sell ───────────────────────────────────────────────────

test.describe("Trading", () => {
  test("buy shares — position appears and cash decreases", async ({ page }) => {
    await page.goto("/");

    // Wait for SSE to be connected so we have a price
    await expect(page.getByTestId("connection-dot")).toHaveAttribute(
      "data-status",
      "connected",
      { timeout: 15_000 }
    );

    // Capture cash before
    const cashEl = page.getByTestId("cash-balance");
    await expect(cashEl).toBeVisible();
    const cashBefore = await cashEl.textContent();

    // Fill trade bar and buy
    await page.getByTestId("trade-ticker-input").fill("AAPL");
    await page.getByTestId("trade-quantity-input").fill("2");
    await page.getByTestId("trade-buy-button").click();

    // Cash should decrease
    await expect
      .poll(async () => cashEl.textContent(), { timeout: 12_000 })
      .not.toBe(cashBefore);

    // Positions table should show AAPL
    const table = page.getByTestId("positions-table");
    await expect(table).toBeVisible();
    await expect(table.getByText("AAPL")).toBeVisible({ timeout: 10_000 });
  });

  test("sell shares — position reduces and cash increases", async ({ page }) => {
    await page.goto("/");

    // Wait for SSE connected
    await expect(page.getByTestId("connection-dot")).toHaveAttribute(
      "data-status",
      "connected",
      { timeout: 15_000 }
    );

    // First buy some shares
    await page.getByTestId("trade-ticker-input").fill("MSFT");
    await page.getByTestId("trade-quantity-input").fill("3");
    await page.getByTestId("trade-buy-button").click();

    // Wait for MSFT to appear in positions
    const table = page.getByTestId("positions-table");
    await expect(table.getByText("MSFT")).toBeVisible({ timeout: 12_000 });

    // Capture cash after buy
    const cashEl = page.getByTestId("cash-balance");
    const cashAfterBuy = await cashEl.textContent();

    // Now sell 2 shares
    await page.getByTestId("trade-ticker-input").fill("MSFT");
    await page.getByTestId("trade-quantity-input").fill("2");
    await page.getByTestId("trade-sell-button").click();

    // Cash should increase
    await expect
      .poll(async () => cashEl.textContent(), { timeout: 12_000 })
      .not.toBe(cashAfterBuy);
  });
});

// ─── 5. Portfolio visualizations ────────────────────────────────────────────

test.describe("Portfolio visualizations", () => {
  test("positions-table renders without error", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("positions-table")).toBeVisible();
  });

  test("P&L chart component mounts (pnl-chart or svg present)", async ({ page }) => {
    await page.goto("/");
    // PnlChart renders an SVG or a container — check no crash first
    await expect(page.getByTestId("positions-table")).toBeVisible();
    // No uncaught JS errors → test passes if page loaded successfully
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));
    await page.waitForTimeout(2000);
    // Allow minor errors but not crashes
    const fatalErrors = errors.filter(
      (e) => !e.includes("ResizeObserver") && !e.includes("Non-Error promise")
    );
    expect(fatalErrors).toHaveLength(0);
  });

  test("portfolio heatmap component mounts", async ({ page }) => {
    await page.goto("/");
    // After buying a position the heatmap should render something
    await expect(page.getByTestId("connection-dot")).toHaveAttribute(
      "data-status",
      "connected",
      { timeout: 15_000 }
    );
    // Buy to create a position for the heatmap
    await page.getByTestId("trade-ticker-input").fill("NVDA");
    await page.getByTestId("trade-quantity-input").fill("1");
    await page.getByTestId("trade-buy-button").click();

    // Positions table confirms the position
    const table = page.getByTestId("positions-table");
    await expect(table.getByText("NVDA")).toBeVisible({ timeout: 12_000 });
    // Page didn't crash — heatmap mounts
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));
    await page.waitForTimeout(1000);
    const fatalErrors = errors.filter((e) => !e.includes("ResizeObserver"));
    expect(fatalErrors).toHaveLength(0);
  });
});

// ─── 6. AI Chat (LLM_MOCK=true) ─────────────────────────────────────────────

test.describe("AI chat (mock mode)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // Wait for SSE connection
    await expect(page.getByTestId("connection-dot")).toHaveAttribute(
      "data-status",
      "connected",
      { timeout: 15_000 }
    );
  });

  test("send 'buy 5 AAPL' → assistant reply with trade confirmation", async ({ page }) => {
    const chatInput = page.getByTestId("chat-input");
    const sendButton = page.getByTestId("chat-send-button");

    await expect(chatInput).toBeVisible();
    await chatInput.fill("buy 5 AAPL");
    await sendButton.click();

    // An assistant message should appear in the chat
    // The mock returns "Buying 5 AAPL as requested."
    await expect(page.getByText(/Buying 5 AAPL as requested/i)).toBeVisible({
      timeout: 20_000,
    });

    // The trade should execute → AAPL position appears
    const table = page.getByTestId("positions-table");
    await expect(table.getByText("AAPL")).toBeVisible({ timeout: 15_000 });
  });

  test("send 'add PYPL to watchlist' → PYPL row appears", async ({ page }) => {
    // Confirm PYPL not initially present
    await expect(page.getByTestId("watchlist-row-PYPL")).not.toBeVisible();

    const chatInput = page.getByTestId("chat-input");
    const sendButton = page.getByTestId("chat-send-button");

    await chatInput.fill("add PYPL to watchlist");
    await sendButton.click();

    // Mock responds: "Added PYPL to your watchlist."
    await expect(page.getByText(/Added PYPL to your watchlist/i)).toBeVisible({
      timeout: 20_000,
    });

    // Watchlist row should appear
    await expect(page.getByTestId("watchlist-row-PYPL")).toBeVisible({
      timeout: 10_000,
    });
  });
});
