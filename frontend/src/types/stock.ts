export interface Stock {
  symbol: string;
  name: string;
  market: 'US' | 'TW';
  industry?: string;
  description?: string;
  price?: number;
  change?: number;
  changePercent?: number;
  volume?: number;
}

export interface PricePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adjClose?: number;
}

export interface IndicatorPoint {
  date: string;
  value: number;
}

export interface Watchlist {
  id: number;
  name: string;
  items: { id: number; symbol: string }[];
}

export interface BacktestConfig {
  symbol: string;
  strategy: string;
  startDate: string;
  endDate: string;
  initialCapital: number;
  commission?: number;
  tax?: number;
  params?: Record<string, number>;
}

export interface BacktestResult {
  totalReturn: number;
  annualizedReturn: number;
  maxDrawdown: number;
  sharpeRatio: number;
  winRate: number;
  totalTrades: number;
  finalValue: number;
  equityCurve: { date: string; value: number }[];
  trades: { date: string; action: string; price: number; shares: number }[];
}

export interface ScreenerCondition {
  indicator: string;
  operator: 'gt' | 'gte' | 'lt' | 'lte' | 'eq';
  value: number | string;
}

export interface ValuationData {
  peRatio: number | null;
  pbRatio: number | null;
  psRatio: number | null;
  dividendYield: number | null;
  marketCap: number | null;
  eps: number | null;
  revenue: number | null;
  profitMargin: number | null;

  // 風險指標
  beta: number | null;
  fiftyTwoWeekHigh: number | null;
  fiftyTwoWeekLow: number | null;

  // 財務健康
  debtToEquity: number | null;
  currentRatio: number | null;
  quickRatio: number | null;

  // 獲利能力
  roe: number | null;
  roa: number | null;
  operatingMargin: number | null;
  grossMargin: number | null;
  freeCashFlow: number | null;

  // 成長
  revenueGrowth: number | null;
  earningsGrowth: number | null;

  // 進階估值
  pegRatio: number | null;
  evToEbitda: number | null;
  forwardPe: number | null;

  // 分析師
  targetMeanPrice: number | null;
  recommendationKey: string | null;
  numberOfAnalysts: number | null;

  // 持股結構
  insiderHolding: number | null;
  institutionalHolding: number | null;

  // 做空
  shortRatio: number | null;
  shortPercentOfFloat: number | null;

  // 股息詳情
  payoutRatio: number | null;
  dividendRate: number | null;
  fiveYearAvgDividendYield: number | null;
}

export interface StockScore {
  overallScore: number;
  valuationScore: number;
  technicalScore: number;
  fundamentalScore: number;
  grade: string;
  signals: { type: 'positive' | 'negative' | 'neutral'; message: string }[];
}

export interface ApiResponse<T> {
  data: T;
  meta?: { total: number; page: number; limit: number };
}

export type Market = 'US' | 'TW' | 'ALL';

export type AlertType =
  | 'price_above'
  | 'price_below'
  | 'rsi_above'
  | 'rsi_below'
  | 'sma_cross'
  | 'volume_above';

export interface Alert {
  id: number;
  symbol: string;
  alert_type: AlertType;
  condition: Record<string, number>;
  is_active: boolean;
  triggered_at: string | null;
  created_at: string;
}

export interface AlertCheckResult {
  triggered: boolean;
  current_value: number;
}
