import { type Page, type Locator } from '@playwright/test';

/**
 * BasePage
 *
 * Shared selectors and helpers that every page object can inherit.
 * All locators are defined as getters so they are lazily resolved at
 * call-time, keeping the constructor lightweight.
 */
export class BasePage {
  constructor(protected readonly page: Page) {}

  // ------------------------------------------------------------------
  // Common layout selectors
  // ------------------------------------------------------------------

  /** Top-level application header element. */
  get header(): Locator {
    return this.page.locator('header');
  }

  /** The application title text rendered inside the header. */
  get appTitle(): Locator {
    return this.page.locator('header h1');
  }

  /** Primary navigation element (if present). */
  get nav(): Locator {
    return this.page.locator('nav');
  }

  /** Main content area. */
  get mainContent(): Locator {
    return this.page.locator('main');
  }

  // ------------------------------------------------------------------
  // Common actions
  // ------------------------------------------------------------------

  /**
   * Navigate to a path relative to the configured baseURL.
   *
   * @param path - e.g. "/" or "/stocks/AAPL"
   */
  async goto(path: string = '/'): Promise<void> {
    await this.page.goto(path);
  }

  /**
   * Wait until the network is idle (no in-flight requests for 500 ms).
   * Useful after navigating to ensure data-fetch calls have settled.
   */
  async waitForNetworkIdle(): Promise<void> {
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Return the current page <title>.
   */
  async getTitle(): Promise<string> {
    return this.page.title();
  }
}
