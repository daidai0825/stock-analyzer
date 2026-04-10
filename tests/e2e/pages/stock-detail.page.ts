import { type Page, type Locator } from '@playwright/test';
import { BasePage } from './base.page';

/**
 * StockDetailPage
 *
 * Page object for the stock detail view (e.g. /stocks/AAPL).
 * Selectors are intentionally broad so they survive minor markup
 * changes; tighten them as the UI stabilises.
 */
export class StockDetailPage extends BasePage {
  constructor(page: Page) {
    super(page);
  }

  // ------------------------------------------------------------------
  // Selectors
  // ------------------------------------------------------------------

  /** Container that holds the stock symbol / ticker heading. */
  get symbolHeading(): Locator {
    return this.page.getByTestId('stock-symbol');
  }

  /** Company name label next to / below the symbol. */
  get companyName(): Locator {
    return this.page.getByTestId('stock-name');
  }

  /** Price chart canvas or SVG rendered by Recharts. */
  get priceChart(): Locator {
    // Recharts renders an <svg> inside the chart wrapper div
    return this.page.locator('[data-testid="price-chart"] svg');
  }

  /** Current price displayed on the detail page. */
  get currentPrice(): Locator {
    return this.page.getByTestId('current-price');
  }

  /** Technical-indicator section container. */
  get indicatorsSection(): Locator {
    return this.page.getByTestId('indicators-section');
  }

  /** Loading skeleton / spinner shown while data is fetched. */
  get loadingSpinner(): Locator {
    return this.page.getByTestId('loading-spinner');
  }

  /** Error message displayed when a stock is not found or fetch fails. */
  get errorMessage(): Locator {
    return this.page.getByTestId('error-message');
  }

  // ------------------------------------------------------------------
  // Actions
  // ------------------------------------------------------------------

  /**
   * Navigate directly to the stock detail page for the given symbol.
   *
   * @param symbol - e.g. "AAPL" or "2330"
   */
  async gotoStock(symbol: string): Promise<void> {
    await this.goto(`/stocks/${symbol}`);
  }

  /**
   * Wait until the loading spinner disappears, indicating that data has
   * been fetched (or an error state has been reached).
   */
  async waitForDataLoaded(): Promise<void> {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 10_000 });
  }
}
