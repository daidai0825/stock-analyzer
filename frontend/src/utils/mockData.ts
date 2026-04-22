// Development-only mock data. Not imported by production code paths.
import { addDays, format, subDays, subYears } from 'date-fns';
import type {
  BacktestResult,
  IndicatorPoint,
  PricePoint,
  Stock,
  ValuationData,
  Watchlist,
} from '../types/stock';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function randomWalk(start: number, days: number, volatility = 0.02): number[] {
  const prices: number[] = [start];
  for (let i = 1; i < days; i++) {
    const change = (Math.random() - 0.48) * volatility * prices[i - 1];
    prices.push(Math.max(1, prices[i - 1] + change));
  }
  return prices;
}

// ---------------------------------------------------------------------------
// OHLCV data
// ---------------------------------------------------------------------------

export function generateMockPriceHistory(
  symbol: string,
  days = 365,
  startPrice = 150,
): PricePoint[] {
  const closes = randomWalk(startPrice, days);
  const endDate = new Date();
  const result: PricePoint[] = [];

  for (let i = 0; i < days; i++) {
    const date = subDays(endDate, days - 1 - i);
    const close = closes[i];
    const open = close * (1 + (Math.random() - 0.5) * 0.02);
    const high = Math.max(open, close) * (1 + Math.random() * 0.01);
    const low = Math.min(open, close) * (1 - Math.random() * 0.01);
    const volume = Math.floor(Math.random() * 50_000_000 + 10_000_000);
    result.push({
      date: format(date, 'yyyy-MM-dd'),
      open: +open.toFixed(2),
      high: +high.toFixed(2),
      low: +low.toFixed(2),
      close: +close.toFixed(2),
      volume,
      adjClose: +close.toFixed(2),
    });
  }
  // deterministic seed-like variation per symbol
  const offset = symbol.charCodeAt(0) * 2;
  return result.map((p) => ({
    ...p,
    close: +(p.close + offset).toFixed(2),
    open: +(p.open + offset).toFixed(2),
    high: +(p.high + offset).toFixed(2),
    low: +(p.low + offset).toFixed(2),
  }));
}

// ---------------------------------------------------------------------------
// SMA indicator
// ---------------------------------------------------------------------------

export function generateMockSMA(prices: PricePoint[], period = 20): IndicatorPoint[] {
  return prices.slice(period - 1).map((_, i) => {
    const slice = prices.slice(i, i + period);
    const avg = slice.reduce((s, p) => s + p.close, 0) / period;
    return { date: prices[i + period - 1].date, value: +avg.toFixed(2) };
  });
}

// ---------------------------------------------------------------------------
// RSI indicator (simplified)
// ---------------------------------------------------------------------------

export function generateMockRSI(prices: PricePoint[], period = 14): IndicatorPoint[] {
  const result: IndicatorPoint[] = [];
  for (let i = period; i < prices.length; i++) {
    let gains = 0;
    let losses = 0;
    for (let j = i - period + 1; j <= i; j++) {
      const diff = prices[j].close - prices[j - 1].close;
      if (diff > 0) gains += diff;
      else losses -= diff;
    }
    const avgGain = gains / period;
    const avgLoss = losses / period;
    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    const rsi = 100 - 100 / (1 + rs);
    result.push({ date: prices[i].date, value: +rsi.toFixed(2) });
  }
  return result;
}

// ---------------------------------------------------------------------------
// Sample stocks
// ---------------------------------------------------------------------------

export const MOCK_US_STOCKS: Stock[] = [
  { symbol: 'AAPL', name: 'Apple Inc.', market: 'US', industry: 'Technology', price: 189.3, change: 1.2, changePercent: 0.64, volume: 52_000_000 },
  { symbol: 'MSFT', name: 'Microsoft Corporation', market: 'US', industry: 'Technology', price: 415.0, change: -2.1, changePercent: -0.5, volume: 21_000_000 },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', market: 'US', industry: 'Technology', price: 173.5, change: 0.9, changePercent: 0.52, volume: 18_000_000 },
  { symbol: 'AMZN', name: 'Amazon.com Inc.', market: 'US', industry: 'Consumer Discretionary', price: 185.2, change: 3.4, changePercent: 1.87, volume: 31_000_000 },
  { symbol: 'NVDA', name: 'NVIDIA Corporation', market: 'US', industry: 'Technology', price: 875.4, change: 12.3, changePercent: 1.43, volume: 44_000_000 },
  { symbol: 'META', name: 'Meta Platforms Inc.', market: 'US', industry: 'Technology', price: 490.1, change: -5.6, changePercent: -1.13, volume: 15_000_000 },
  { symbol: 'TSLA', name: 'Tesla Inc.', market: 'US', industry: 'Consumer Discretionary', price: 175.0, change: 4.2, changePercent: 2.46, volume: 120_000_000 },
  { symbol: 'BRK.B', name: 'Berkshire Hathaway', market: 'US', industry: 'Financials', price: 395.8, change: 0.3, changePercent: 0.08, volume: 4_200_000 },
];

export const MOCK_TW_STOCKS: Stock[] = [
  { symbol: '2330', name: '台積電', market: 'TW', industry: '半導體', price: 850.0, change: 10, changePercent: 1.19, volume: 28_000_000 },
  { symbol: '2317', name: '鴻海', market: 'TW', industry: '電子製造', price: 168.0, change: -1, changePercent: -0.59, volume: 42_000_000 },
  { symbol: '2454', name: '聯發科', market: 'TW', industry: '半導體', price: 1060.0, change: 20, changePercent: 1.92, volume: 5_800_000 },
  { symbol: '2382', name: '廣達電腦', market: 'TW', industry: '電腦及周邊', price: 285.5, change: 5.5, changePercent: 1.97, volume: 19_000_000 },
  { symbol: '2881', name: '富邦金', market: 'TW', industry: '金融', price: 84.5, change: 0.5, changePercent: 0.6, volume: 22_000_000 },
];

// ---------------------------------------------------------------------------
// Valuation
// ---------------------------------------------------------------------------

export function getMockValuation(symbol: string): ValuationData {
  const seed = symbol.split('').reduce((s, c) => s + c.charCodeAt(0), 0);
  return {
    peRatio: +(15 + (seed % 30)).toFixed(1),
    pbRatio: +(1 + (seed % 10) * 0.3).toFixed(2),
    psRatio: +(2 + (seed % 8) * 0.5).toFixed(2),
    dividendYield: seed % 3 === 0 ? null : +((seed % 4) * 0.5).toFixed(2),
    marketCap: (seed % 100 + 10) * 1e9,
    eps: +(1 + (seed % 20) * 0.5).toFixed(2),
    revenue: (seed % 50 + 5) * 1e9,
    profitMargin: +((seed % 30) * 0.01).toFixed(3),
    beta: null,
    fiftyTwoWeekHigh: null,
    fiftyTwoWeekLow: null,
    debtToEquity: null,
    currentRatio: null,
    quickRatio: null,
    roe: null,
    roa: null,
    operatingMargin: null,
    grossMargin: null,
    freeCashFlow: null,
    revenueGrowth: null,
    earningsGrowth: null,
    pegRatio: null,
    evToEbitda: null,
    forwardPe: null,
    targetMeanPrice: null,
    recommendationKey: null,
    numberOfAnalysts: null,
    insiderHolding: null,
    institutionalHolding: null,
    shortRatio: null,
    shortPercentOfFloat: null,
    payoutRatio: null,
    dividendRate: null,
    fiveYearAvgDividendYield: null,
  };
}

// ---------------------------------------------------------------------------
// Watchlists
// ---------------------------------------------------------------------------

export const MOCK_WATCHLISTS: Watchlist[] = [
  {
    id: 1,
    name: 'Tech Giants',
    items: [
      { id: 1, symbol: 'AAPL' },
      { id: 2, symbol: 'MSFT' },
      { id: 3, symbol: 'NVDA' },
    ],
  },
  {
    id: 2,
    name: '台股精選',
    items: [
      { id: 4, symbol: '2330' },
      { id: 5, symbol: '2454' },
    ],
  },
];

// ---------------------------------------------------------------------------
// Backtest
// ---------------------------------------------------------------------------

export function generateMockBacktestResult(
  initialCapital: number,
  days = 365,
): BacktestResult {
  const values = randomWalk(initialCapital, days, 0.015);
  const endDate = new Date();
  const equityCurve = values.map((v, i) => ({
    date: format(subDays(endDate, days - 1 - i), 'yyyy-MM-dd'),
    value: +v.toFixed(2),
  }));

  const finalValue = values[values.length - 1];
  const totalReturn = (finalValue - initialCapital) / initialCapital;

  // Max drawdown
  let peak = initialCapital;
  let maxDD = 0;
  for (const v of values) {
    if (v > peak) peak = v;
    const dd = (peak - v) / peak;
    if (dd > maxDD) maxDD = dd;
  }

  const trades: BacktestResult['trades'] = [];
  for (let i = 0; i < 12; i++) {
    const dayOffset = Math.floor(Math.random() * days);
    trades.push({
      date: format(subDays(endDate, days - dayOffset), 'yyyy-MM-dd'),
      action: i % 2 === 0 ? 'BUY' : 'SELL',
      price: +(150 + Math.random() * 100).toFixed(2),
      shares: Math.floor(Math.random() * 100 + 10),
    });
  }
  trades.sort((a, b) => a.date.localeCompare(b.date));

  return {
    totalReturn: +totalReturn.toFixed(4),
    annualizedReturn: +(Math.pow(1 + totalReturn, 365 / days) - 1).toFixed(4),
    maxDrawdown: +maxDD.toFixed(4),
    sharpeRatio: +(1 + Math.random() * 1.5).toFixed(2),
    winRate: +(0.4 + Math.random() * 0.3).toFixed(2),
    totalTrades: trades.length,
    finalValue: +finalValue.toFixed(2),
    equityCurve,
    trades,
  };
}

// ---------------------------------------------------------------------------
// Screener results (stub)
// ---------------------------------------------------------------------------

export function getMockScreenerResults(): Stock[] {
  return [...MOCK_US_STOCKS, ...MOCK_TW_STOCKS];
}

// ---------------------------------------------------------------------------
// Date helpers
// ---------------------------------------------------------------------------

export function getPeriodStartDate(period: string): Date {
  const now = new Date();
  switch (period) {
    case '1D': return subDays(now, 1);
    case '1W': return subDays(now, 7);
    case '1M': return subDays(now, 30);
    case '3M': return subDays(now, 90);
    case '6M': return subDays(now, 180);
    case '1Y': return subDays(now, 365);
    case '5Y': return subYears(now, 5);
    default:   return subDays(now, 365);
  }
}

export function filterByPeriod(prices: PricePoint[], period: string): PricePoint[] {
  const start = getPeriodStartDate(period);
  const startStr = format(start, 'yyyy-MM-dd');
  return prices.filter((p) => p.date >= startStr);
}

// ---------------------------------------------------------------------------
// Unused import suppressor — keep date-fns addDays available for callers
// ---------------------------------------------------------------------------
export { addDays };
