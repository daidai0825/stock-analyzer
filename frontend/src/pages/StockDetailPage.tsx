import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { PriceChart } from '../components/charts/PriceChart';
import { IndicatorChart } from '../components/charts/IndicatorChart';
import { FullPageSpinner } from '../components/common/Spinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { useStockHistory } from '../hooks/useStockHistory';
import { useIndicators } from '../hooks/useIndicators';
import { fetchStockDetail, fetchStockValuation } from '../services/api';
import { addRecentSearch } from '../components/layout/Sidebar';
import type { Stock, ValuationData } from '../types/stock';

const PERIODS = ['1W', '1M', '3M', '6M', '1Y', '5Y'] as const;
type Period = (typeof PERIODS)[number];

interface ValuationRowProps {
  label: string;
  value: string | null;
}

function ValuationRow({ label, value }: ValuationRowProps) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm font-semibold text-gray-900">{value ?? '—'}</span>
    </div>
  );
}

function formatMarketCap(v: number | null) {
  if (v == null) return null;
  if (v >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  return `$${v.toFixed(0)}`;
}

const FALLBACK_VALUATION: ValuationData = {
  peRatio: null,
  pbRatio: null,
  psRatio: null,
  dividendYield: null,
  marketCap: null,
  eps: null,
};

export function StockDetailPage() {
  const { symbol = '' } = useParams<{ symbol: string }>();
  const [period, setPeriod] = useState<Period>('1Y');
  const [showSMA20, setShowSMA20] = useState(false);
  const [showSMA50, setShowSMA50] = useState(false);
  const [showRSI, setShowRSI] = useState(false);

  const [stock, setStock] = useState<Stock | null>(null);
  const [stockError, setStockError] = useState<string | null>(null);

  const [valuation, setValuation] = useState<ValuationData>(FALLBACK_VALUATION);

  const { data: prices, isLoading, error } = useStockHistory(symbol, period);
  const indicators = useIndicators(prices, symbol);

  // Fetch stock detail
  useEffect(() => {
    if (!symbol) return;
    setStockError(null);
    fetchStockDetail(symbol)
      .then(setStock)
      .catch(() => setStockError('無法載入股票資料'));
  }, [symbol]);

  // Fetch valuation data
  useEffect(() => {
    if (!symbol) return;
    fetchStockValuation(symbol)
      .then(setValuation)
      .catch(() => setValuation(FALLBACK_VALUATION));
  }, [symbol]);

  // Track recent searches
  useEffect(() => {
    if (symbol) addRecentSearch(symbol.toUpperCase());
  }, [symbol]);

  if (isLoading) return <FullPageSpinner />;
  if (error) return <ErrorMessage message={error} />;
  if (stockError) return <ErrorMessage message={stockError} />;

  // Build display stock from API data or minimal fallback from the URL symbol
  const displayStock: Stock = stock ?? {
    symbol: symbol.toUpperCase(),
    name: symbol.toUpperCase(),
    market: 'US',
    price: undefined,
    change: 0,
    changePercent: 0,
  };

  const latestPrice = prices.length > 0 ? prices[prices.length - 1].close : (displayStock.price ?? 0);
  const prevPrice = prices.length > 1 ? prices[prices.length - 2].close : latestPrice;
  const dayChange = latestPrice - prevPrice;
  const dayChangePct = prevPrice !== 0 ? (dayChange / prevPrice) * 100 : 0;
  const isPositive = dayChange >= 0;

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="text-sm text-gray-500">
        <Link to="/" className="hover:text-gray-700">首頁</Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900 font-medium">{displayStock.symbol}</span>
      </div>

      {/* Header */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900">{displayStock.symbol}</h1>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  displayStock.market === 'US'
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-green-100 text-green-700'
                }`}
              >
                {displayStock.market}
              </span>
              {displayStock.industry && (
                <span className="text-xs text-gray-500 bg-gray-100 rounded-full px-2 py-0.5">
                  {displayStock.industry}
                </span>
              )}
            </div>
            <p className="text-gray-500 text-sm mt-0.5">{displayStock.name}</p>
          </div>
          <div className="text-right">
            <p className="text-3xl font-bold text-gray-900">
              ${latestPrice.toFixed(2)}
            </p>
            <p className={`text-sm font-semibold ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
              {isPositive ? '+' : ''}{dayChange.toFixed(2)} ({isPositive ? '+' : ''}{dayChangePct.toFixed(2)}%)
            </p>
          </div>
        </div>
      </div>

      {/* Chart card */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        {/* Period selector */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-1">
            {PERIODS.map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`rounded-md px-3 py-1 text-xs font-semibold transition-colors ${
                  period === p
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-500 hover:bg-gray-100'
                }`}
              >
                {p}
              </button>
            ))}
          </div>

          {/* Overlay toggles */}
          <div className="flex items-center gap-2 text-xs">
            <span className="text-gray-400 font-medium">疊加：</span>
            {[
              { key: 'sma20', label: 'SMA20', color: 'text-orange-500', active: showSMA20, toggle: () => setShowSMA20((v) => !v) },
              { key: 'sma50', label: 'SMA50', color: 'text-purple-500', active: showSMA50, toggle: () => setShowSMA50((v) => !v) },
            ].map(({ key, label, color, active, toggle }) => (
              <button
                key={key}
                onClick={toggle}
                className={`rounded-full px-2.5 py-1 font-semibold border transition-colors ${
                  active
                    ? `border-current ${color} bg-opacity-10`
                    : 'border-gray-200 text-gray-400 hover:border-gray-300'
                }`}
              >
                {label}
              </button>
            ))}
            <span className="text-gray-400 font-medium ml-2">指標：</span>
            <button
              onClick={() => setShowRSI((v) => !v)}
              className={`rounded-full px-2.5 py-1 font-semibold border transition-colors ${
                showRSI
                  ? 'border-indigo-400 text-indigo-500'
                  : 'border-gray-200 text-gray-400 hover:border-gray-300'
              }`}
            >
              RSI
            </button>
          </div>
        </div>

        <PriceChart
          prices={prices}
          sma20={indicators.sma20}
          sma50={indicators.sma50}
          showSMA20={showSMA20}
          showSMA50={showSMA50}
          height={400}
        />

        {showRSI && (
          <div className="mt-4">
            <IndicatorChart
              data={indicators.rsi14}
              label="RSI (14)"
              color="#6366f1"
              height={130}
              domain={[0, 100]}
              referenceLines={[
                { value: 70, color: '#ef4444', label: '超買 70' },
                { value: 30, color: '#22c55e', label: '超賣 30' },
              ]}
            />
          </div>
        )}
      </div>

      {/* Valuation */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">估值</h2>
          <ValuationRow label="本益比" value={valuation.peRatio != null ? valuation.peRatio.toFixed(1) : null} />
          <ValuationRow label="股價淨值比" value={valuation.pbRatio != null ? valuation.pbRatio.toFixed(2) : null} />
          <ValuationRow label="股價營收比" value={valuation.psRatio != null ? valuation.psRatio.toFixed(2) : null} />
          <ValuationRow label="每股盈餘" value={valuation.eps != null ? `$${valuation.eps.toFixed(2)}` : null} />
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">市場資料</h2>
          <ValuationRow
            label="市值"
            value={formatMarketCap(valuation.marketCap)}
          />
          <ValuationRow
            label="股息殖利率"
            value={valuation.dividendYield != null ? `${valuation.dividendYield.toFixed(2)}%` : null}
          />
          <ValuationRow
            label="成交量（最新）"
            value={
              prices.length > 0
                ? prices[prices.length - 1].volume.toLocaleString()
                : '—'
            }
          />
          <ValuationRow label="交易所" value={displayStock.market === 'US' ? 'NASDAQ / NYSE' : 'TWSE / TPEx'} />
        </div>
      </div>
    </div>
  );
}
