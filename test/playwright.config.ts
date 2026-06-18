import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E configuration for FinAlly.
 *
 * Tests live in test/e2e/*.spec.ts
 * The app is started via webServer config below.
 */

export default defineConfig({
  testDir: "./e2e",
  // Give each test generous time — market data needs to stream before assertions
  timeout: 60_000,
  expect: { timeout: 15_000 },
  // Fail fast in CI; useful locally to see all failures
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "line",

  use: {
    baseURL: "http://127.0.0.1:8001",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  webServer: {
    command: "bash test/start-server.sh",
    url: "http://127.0.0.1:8001/api/health",
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: "pipe",
    stderr: "pipe",
    cwd: "..",
  },

  globalSetup: "./global-setup.ts",
});
