import { test, expect } from '@playwright/test';

/**
 * Stock search / screener input tests.
 *
 * The first group of tests verify infrastructure that should exist NOW
 * (search input element present, accessible, keyboard-navigable).
 *
 * Tests that depend on real data or unbuilt components are skipped.
 */

test.describe('Stock Search Input', () => {
  // ------------------------------------------------------------------
  // Structural tests — pass once a search input is added to the shell
  // ------------------------------------------------------------------

  test.skip('search input element is present on the page', async ({ page }) => {
    // TODO: add a search <input> or combobox to the App shell / header
    await page.goto('/');
    const searchInput = page.getByRole('searchbox').or(
      page.getByPlaceholder(/search|find|symbol/i),
    );
    await expect(searchInput).toBeVisible();
  });

  test.skip('search input accepts keyboard input', async ({ page }) => {
    await page.goto('/');
    const searchInput = page.getByRole('searchbox').or(
      page.getByPlaceholder(/search|find|symbol/i),
    );
    await searchInput.fill('AAPL');
    await expect(searchInput).toHaveValue('AAPL');
  });

  test.skip('search input is accessible with a label or aria-label', async ({ page }) => {
    await page.goto('/');
    // getByLabel will fail if there is no accessible name — intentional.
    const searchInput = page.getByLabel(/search/i);
    await expect(searchInput).toBeVisible();
  });

  // ------------------------------------------------------------------
  // Functional tests — depend on real data from the Data Engineer
  // ------------------------------------------------------------------

  test.skip('typing "AAPL" shows Apple in the suggestions dropdown', async ({ page }) => {
    // TODO: implement once autocomplete component + API integration exists
    await page.goto('/');
    const searchInput = page.getByRole('searchbox');
    await searchInput.fill('AAPL');
    const suggestion = page.getByText(/apple/i);
    await expect(suggestion).toBeVisible({ timeout: 5_000 });
  });

  test.skip('typing "台積電" shows 2330 in suggestions (TW market)', async ({ page }) => {
    // TODO: implement once TW stock search is wired up
    await page.goto('/');
    const searchInput = page.getByRole('searchbox');
    await searchInput.fill('台積電');
    const suggestion = page.getByText('2330');
    await expect(suggestion).toBeVisible({ timeout: 5_000 });
  });

  test.skip('clicking a suggestion navigates to the stock detail page', async ({ page }) => {
    // TODO: implement once routing + autocomplete are connected
    await page.goto('/');
    const searchInput = page.getByRole('searchbox');
    await searchInput.fill('AAPL');
    await page.getByText(/apple/i).first().click();
    await expect(page).toHaveURL(/\/stocks\/AAPL/i);
  });

  test.skip('pressing Enter on a search query navigates to results', async ({ page }) => {
    // TODO: implement once search-results page route exists
    await page.goto('/');
    const searchInput = page.getByRole('searchbox');
    await searchInput.fill('AAPL');
    await searchInput.press('Enter');
    await expect(page).toHaveURL(/AAPL/);
  });

  test.skip('empty search shows no suggestions / does not crash', async ({ page }) => {
    await page.goto('/');
    const searchInput = page.getByRole('searchbox');
    await searchInput.fill('');
    const dropdown = page.getByTestId('search-suggestions');
    // Either hidden or not present — both are acceptable
    const isVisible = await dropdown.isVisible().catch(() => false);
    expect(isVisible).toBe(false);
  });
});
