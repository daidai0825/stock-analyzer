import { type Page, type Locator } from '@playwright/test';
import { BasePage } from './base.page';

/**
 * ScreenerPage  (placeholder)
 *
 * Page object for the stock screener view.
 * Selectors and actions will be filled in once the screener UI (F003)
 * is implemented by the frontend team.
 */
export class ScreenerPage extends BasePage {
  constructor(page: Page) {
    super(page);
  }

  // ------------------------------------------------------------------
  // Selectors  (placeholders — update when UI exists)
  // ------------------------------------------------------------------

  /** The screener filter panel. */
  get filterPanel(): Locator {
    return this.page.getByTestId('screener-filters');
  }

  /** Market selector dropdown (US / TW). */
  get marketSelector(): Locator {
    return this.page.getByTestId('market-selector');
  }

  /** Table / grid that shows screener results. */
  get resultsTable(): Locator {
    return this.page.getByTestId('screener-results');
  }

  /** Individual result rows inside the results table. */
  get resultRows(): Locator {
    return this.resultsTable.locator('tr[data-testid="result-row"]');
  }

  /** "Run Screener" / "Apply Filters" submit button. */
  get runButton(): Locator {
    return this.page.getByRole('button', { name: /run|apply|screen/i });
  }

  /** Loading indicator while screener results are being fetched. */
  get loadingIndicator(): Locator {
    return this.page.getByTestId('screener-loading');
  }

  // ------------------------------------------------------------------
  // Actions  (placeholders)
  // ------------------------------------------------------------------

  /** Navigate to the screener page. */
  async gotoScreener(): Promise<void> {
    await this.goto('/screener');
  }

  /**
   * Select the target market.
   *
   * @param market - "US" or "TW"
   */
  async selectMarket(market: 'US' | 'TW'): Promise<void> {
    await this.marketSelector.selectOption(market);
  }

  /** Click the run button and wait for results to load. */
  async runScreener(): Promise<void> {
    await this.runButton.click();
    await this.loadingIndicator.waitFor({ state: 'hidden', timeout: 15_000 });
  }
}
