import { test, expect } from '@playwright/test';
import { BasePage } from '../pages/base.page';

/**
 * Navigation tests.
 *
 * Verify that client-side routing works correctly.  Tests that depend on
 * pages that have not been built yet are skipped so they act as a living
 * checklist for the frontend team.
 */

test.describe('Navigation', () => {
  test('root route "/" renders without a 404 page', async ({ page }) => {
    const response = await page.goto('/');
    // The dev server should serve index.html for all routes (SPA fallback).
    expect(response?.status()).toBeLessThan(400);
  });

  test('header is consistent across the root route', async ({ page }) => {
    const basePage = new BasePage(page);
    await basePage.goto('/');
    await expect(basePage.header).toBeVisible();
    await expect(basePage.appTitle).toBeVisible();
  });

  test('unknown route falls back to app shell (SPA 404 handling)', async ({ page }) => {
    // React Router renders the <App> shell for unmatched paths; the page
    // must not return an HTTP 404 from the dev server.
    const response = await page.goto('/this-route-does-not-exist');
    expect(response?.status()).toBeLessThan(400);
    // The header is always rendered — it should still be visible.
    const basePage = new BasePage(page);
    await expect(basePage.header).toBeVisible();
  });

  // ------------------------------------------------------------------
  // Skipped — routes that will exist once the frontend is built out
  // ------------------------------------------------------------------

  test.skip('navigating to /stocks renders the stock list page', async ({ page }) => {
    // TODO: implement once StockListPage component exists
    await page.goto('/stocks');
    await expect(page.getByTestId('stock-list')).toBeVisible();
  });

  test.skip('navigating to /stocks/AAPL renders stock detail page', async ({ page }) => {
    // TODO: implement once StockDetailPage component exists
    await page.goto('/stocks/AAPL');
    await expect(page.getByTestId('stock-symbol')).toHaveText('AAPL');
  });

  test.skip('navigating to /watchlists renders the watchlist page', async ({ page }) => {
    // TODO: implement once WatchlistPage component exists
    await page.goto('/watchlists');
    await expect(page.getByTestId('watchlist-container')).toBeVisible();
  });

  test.skip('navigating to /screener renders the screener page', async ({ page }) => {
    // TODO: implement once ScreenerPage component exists (F003)
    await page.goto('/screener');
    await expect(page.getByTestId('screener-filters')).toBeVisible();
  });
});
