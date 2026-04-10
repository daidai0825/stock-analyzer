import axios from 'axios';
import type {
  Alert,
  AlertCheckResult,
  AlertType,
  ApiResponse,
  BacktestConfig,
  BacktestResult,
  PricePoint,
  ScreenerCondition,
  Stock,
  ValuationData,
  Watchlist,
} from '../types/stock';

export const api = axios.create({
  baseURL: '/api/v1',
});

// Attach the JWT Bearer token to every outgoing request when one is stored.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ---------------------------------------------------------------------------
// Stock endpoints
// ---------------------------------------------------------------------------

export async function fetchStocks(params: {
  market?: string;
  q?: string;
  page?: number;
  limit?: number;
}): Promise<ApiResponse<Stock[]>> {
  const { data } = await api.get<ApiResponse<Stock[]>>('/stocks', { params });
  return data;
}

export async function fetchStockDetail(symbol: string): Promise<Stock> {
  const { data } = await api.get<ApiResponse<Stock>>(`/stocks/${symbol}`);
  return data.data;
}

export async function fetchStockHistory(
  symbol: string,
  period = '1y',
  interval = '1d',
): Promise<PricePoint[]> {
  const { data } = await api.get<ApiResponse<PricePoint[]>>(`/stocks/${symbol}/history`, {
    params: { period, interval },
  });
  return data.data;
}

export async function fetchStockIndicators(
  symbol: string,
  indicators = 'sma,rsi',
): Promise<Record<string, { date: string; value: number }[]>> {
  const { data } = await api.get<ApiResponse<Record<string, { date: string; value: number }[]>>>(
    `/stocks/${symbol}/indicators`,
    { params: { indicators } },
  );
  return data.data;
}

export async function fetchStockValuation(symbol: string): Promise<ValuationData> {
  const { data } = await api.get<ApiResponse<Record<string, unknown>>>(`/stocks/${symbol}/valuation`);
  const raw = data.data;
  // Backend returns snake_case; frontend uses camelCase.
  return {
    peRatio: (raw.pe_ratio as number) ?? null,
    pbRatio: (raw.pb_ratio as number) ?? null,
    psRatio: (raw.ps_ratio as number) ?? null,
    dividendYield: (raw.dividend_yield as number) ?? null,
    marketCap: (raw.market_cap as number) ?? null,
    eps: (raw.eps as number) ?? null,
  };
}

export async function searchStocks(q: string, market = 'US'): Promise<Stock[]> {
  const { data } = await api.get<ApiResponse<Stock[]>>('/stocks', { params: { q, market } });
  return data.data;
}

// ---------------------------------------------------------------------------
// Screener
// ---------------------------------------------------------------------------

export async function runScreener(request: {
  conditions: ScreenerCondition[];
  market?: string;
  limit?: number;
}): Promise<Stock[]> {
  const { data } = await api.post<ApiResponse<{ symbol: string; indicators: Record<string, unknown> }[]>>(
    '/screener',
    request,
  );
  // Transform screener results into Stock-compatible objects.
  return data.data.map((item) => ({
    symbol: item.symbol,
    name: item.symbol,
    market: (request.market ?? 'US') as 'US' | 'TW',
  }));
}

// ---------------------------------------------------------------------------
// Backtest
// ---------------------------------------------------------------------------

export async function runBacktest(request: BacktestConfig): Promise<BacktestResult> {
  // Convert camelCase frontend config to snake_case backend schema.
  const payload = {
    symbol: request.symbol,
    strategy: request.strategy,
    start_date: request.startDate,
    end_date: request.endDate,
    initial_capital: request.initialCapital,
    commission: request.commission,
    tax: request.tax,
    params: request.params,
  };
  const { data } = await api.post<ApiResponse<Record<string, unknown>>>('/backtest', payload);
  const raw = data.data;
  // Convert snake_case response to camelCase frontend types.
  return {
    totalReturn: raw.total_return as number,
    annualizedReturn: raw.annualized_return as number,
    maxDrawdown: raw.max_drawdown as number,
    sharpeRatio: raw.sharpe_ratio as number,
    winRate: raw.win_rate as number,
    totalTrades: raw.total_trades as number,
    finalValue: raw.final_value as number,
    equityCurve: (raw.equity_curve as { date: string; value: number }[]) ?? [],
    trades: (raw.trades as { date: string; action: string; price: number; shares: number }[]) ?? [],
  };
}

// ---------------------------------------------------------------------------
// Watchlists
// ---------------------------------------------------------------------------

export async function fetchWatchlists(): Promise<Watchlist[]> {
  const { data } = await api.get<ApiResponse<Watchlist[]>>('/watchlists');
  return data.data;
}

export async function fetchWatchlist(id: number): Promise<Watchlist> {
  const { data } = await api.get<ApiResponse<Watchlist>>(`/watchlists/${id}`);
  return data.data;
}

export async function createWatchlist(payload: {
  name: string;
  symbols: string[];
}): Promise<Watchlist> {
  const { data } = await api.post<ApiResponse<Watchlist>>('/watchlists', payload);
  return data.data;
}

export async function updateWatchlist(
  id: number,
  payload: { name?: string; symbols?: string[] },
): Promise<Watchlist> {
  const { data } = await api.put<ApiResponse<Watchlist>>(`/watchlists/${id}`, payload);
  return data.data;
}

export async function deleteWatchlist(id: number): Promise<void> {
  await api.delete(`/watchlists/${id}`);
}

// ---------------------------------------------------------------------------
// Portfolios
// ---------------------------------------------------------------------------

export async function fetchPortfolios(): Promise<unknown[]> {
  const { data } = await api.get<ApiResponse<unknown[]>>('/portfolios');
  return data.data;
}

export async function createPortfolio(payload: {
  name: string;
  description?: string;
}): Promise<unknown> {
  const { data } = await api.post<ApiResponse<unknown>>('/portfolios', payload);
  return data.data;
}

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------

export async function fetchAlerts(params?: {
  symbol?: string;
  is_active?: boolean;
  page?: number;
  limit?: number;
}): Promise<ApiResponse<Alert[]>> {
  const { data } = await api.get<ApiResponse<Alert[]>>('/alerts', { params });
  return data;
}

export async function fetchAlert(id: number): Promise<Alert> {
  const { data } = await api.get<ApiResponse<Alert>>(`/alerts/${id}`);
  return data.data;
}

export async function createAlert(payload: {
  symbol: string;
  alert_type: AlertType;
  condition: Record<string, number>;
}): Promise<Alert> {
  const { data } = await api.post<ApiResponse<Alert>>('/alerts', payload);
  return data.data;
}

export async function updateAlert(
  id: number,
  payload: { is_active?: boolean; condition?: Record<string, number> },
): Promise<Alert> {
  const { data } = await api.put<ApiResponse<Alert>>(`/alerts/${id}`, payload);
  return data.data;
}

export async function deleteAlert(id: number): Promise<void> {
  await api.delete(`/alerts/${id}`);
}

export async function checkAlertNow(id: number): Promise<AlertCheckResult> {
  const { data } = await api.get<AlertCheckResult>(`/alerts/${id}/check`);
  return data;
}
