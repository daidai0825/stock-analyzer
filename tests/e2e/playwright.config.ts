import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Stock Analyzer E2E tests.
 *
 * The frontend dev server runs at http://localhost:5173 (Vite default).
 * Set PLAYWRIGHT_BASE_URL to override in CI or staging environments.
 *
 * Run:  npx playwright test
 * Debug: npx playwright test --debug
 */
export default defineConfig({
  testDir: './specs',
  timeout: 30_000,
  expect: {
    /** Assertion timeout — most assertions should resolve in under 5 s. */
    timeout: 5_000,
  },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['html', { open: 'never' }], ['list']],

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Start the Vite dev server automatically when running locally. */
  webServer: {
    command: 'npm run dev',
    cwd: '../../frontend',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
