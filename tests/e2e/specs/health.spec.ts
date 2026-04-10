import { test, expect } from '@playwright/test';
import { BasePage } from '../pages/base.page';

/**
 * Health / smoke tests.
 *
 * These verify that the application shell loads correctly — the page
 * renders, the header is visible, and there are no console errors that
 * would indicate a broken build.
 */

test.describe('Application Health', () => {
  test('home page loads without errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    expect(errors).toHaveLength(0);
  });

  test('application header is visible', async ({ page }) => {
    const basePage = new BasePage(page);
    await basePage.goto('/');

    await expect(basePage.header).toBeVisible();
  });

  test('application title reads "Stock Analyzer"', async ({ page }) => {
    const basePage = new BasePage(page);
    await basePage.goto('/');

    await expect(basePage.appTitle).toHaveText('Stock Analyzer');
  });

  test('main content area is present', async ({ page }) => {
    const basePage = new BasePage(page);
    await basePage.goto('/');

    await expect(basePage.mainContent).toBeVisible();
  });

  test('page has a valid HTML title', async ({ page }) => {
    await page.goto('/');
    const title = await page.title();
    expect(title.length).toBeGreaterThan(0);
  });

  test('root route renders without crashing', async ({ page }) => {
    // A crash would leave the page empty or show a React error boundary.
    await page.goto('/');
    const body = page.locator('body');
    await expect(body).not.toBeEmpty();
  });
});
