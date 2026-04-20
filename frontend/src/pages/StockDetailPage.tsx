import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { PriceChart } from '../components/charts/PriceChart';
import { IndicatorChart } from '../components/charts/IndicatorChart';
import { MacdChart } from '../components/charts/MacdChart';
import { BollingerChart } from '../components/charts/BollingerChart';
import { KdChart } from '../components/charts/KdChart';
import { ScoreCard } from '../components/stock/ScoreCard';
import { FullPageSpinner } from '../components/common/Spinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { useStockHistory } from '../hooks/useStockHistory';
import { useIndicators } from '../hooks/useIndicators';
import { fetchStockDetail, fetchStockValuation, fetchStockScore } from '../services/api';
import { addRecentSearch } from '../components/layout/Sidebar';
import type { Stock, StockScore, ValuationData } from '../types/stock';

const PERIODS = ['1W', '1M', '3M', '6M', '1Y', '5Y'] as const;
type Period = (typeof PERIODS)[number];

type TechnicalIndicator = 'macd' | 'bollinger' | 'kd';

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

function formatRevenue(v: number | null) {
  if (v == null) return null;
  if (v >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  return `$${v.toFixed(0)}`;
}

const FALLBACK_VALUATION: ValuationData = {
  peRatio: null,
  pbRatio: null,
  psRatio: null,
  dividendYield: null,
  marketCap: null,
  eps: null,
  revenue: null,
  profitMargin: null,
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

const TECHNICAL_INDICATOR_LABELS: Record<TechnicalIndicator, string> = {
  macd: 'MACD',
  bollinger: '布林通道',
  kd: 'KD',
};

export function StockDetailPage() {
  const { symbol = '' } = useParams<{ symbol: string }>();
  const [period, setPeriod] = useState<Period>('1Y');
  const [showSMA20, setShowSMA20] = useState(false);
  const [showSMA50, setShowSMA50] = useState(false);
  const [showRSI, setShowRSI] = useState(false);
  const [activeTechnical, setActiveTechnical] = useState<TechnicalIndicator | null>(null);

  const [stock, setStock] = useState<Stock | null>(null);
  const [stockError, setStockError] = useState<string | null>(null);
  const [valuation, setValuation] = useState<ValuationData>(FALLBACK_VALUATION);
  const [score, setScore] = useState<StockScore | null>(null);

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

  // Fetch score
  useEffect(() => {
    if (!symbol) return;
    fetchStockScore(symbol)
      .then(setScore)
      .catch(() => setScore(null));
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

  function toggleTechnical(indicator: TechnicalIndicator) {
    setActiveTechnical((prev) => (prev === indicator ? null : indicator));
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="text-sm text-gray-500">
        <Link to="/" className="hover:text-gray-700">
          首頁
        </Link>
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
            <p className="text-3xl font-bold text-gray-900">${latestPrice.toFixed(2)}</p>
            <p className={`text-sm font-semibold ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
              {isPositive ? '+' : ''}
              {dayChange.toFixed(2)} ({isPositive ? '+' : ''}
              {dayChangePct.toFixed(2)}%)
            </p>
          </div>
        </div>
      </div>

      {/* Score card */}
      {score && <ScoreCard score={score} />}

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
                  period === p ? 'bg-blue-600 text-white' : 'text-gray-500 hover:bg-gray-100'
                }`}
              >
                {p}
              </button>
            ))}
          </div>

          {/* Overlay toggles */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-gray-400 font-medium">疊加：</span>
            {[
              {
                key: 'sma20',
                label: 'SMA20',
                color: 'text-orange-500',
                active: showSMA20,
                toggle: () => setShowSMA20((v) => !v),
              },
              {
                key: 'sma50',
                label: 'SMA50',
                color: 'text-purple-500',
                active: showSMA50,
                toggle: () => setShowSMA50((v) => !v),
              },
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
            {(['macd', 'bollinger', 'kd'] as TechnicalIndicator[]).map((ind) => (
              <button
                key={ind}
                onClick={() => toggleTechnical(ind)}
                className={`rounded-full px-2.5 py-1 font-semibold border transition-colors ${
                  activeTechnical === ind
                    ? 'border-teal-400 text-teal-600'
                    : 'border-gray-200 text-gray-400 hover:border-gray-300'
                }`}
              >
                {TECHNICAL_INDICATOR_LABELS[ind]}
              </button>
            ))}
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

        {activeTechnical === 'macd' && (
          <div className="mt-4">
            <MacdChart data={indicators.macd} height={160} />
          </div>
        )}

        {activeTechnical === 'bollinger' && (
          <div className="mt-4">
            <BollingerChart
              prices={prices}
              upper={indicators.bollingerUpper}
              middle={indicators.bollingerMiddle}
              lower={indicators.bollingerLower}
              height={200}
            />
          </div>
        )}

        {activeTechnical === 'kd' && (
          <div className="mt-4">
            <KdChart kData={indicators.kd_k} dData={indicators.kd_d} height={160} />
          </div>
        )}
      </div>

      {/* Valuation & fundamentals */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* 估值 */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">估值</h2>
          <ValuationRow
            label="本益比"
            value={valuation.peRatio != null ? valuation.peRatio.toFixed(1) : null}
          />
          <ValuationRow
            label="股價淨值比"
            value={valuation.pbRatio != null ? valuation.pbRatio.toFixed(2) : null}
          />
          <ValuationRow
            label="股價營收比"
            value={valuation.psRatio != null ? valuation.psRatio.toFixed(2) : null}
          />
          <ValuationRow
            label="每股盈餘"
            value={valuation.eps != null ? `$${valuation.eps.toFixed(2)}` : null}
          />
          <ValuationRow label="營收" value={formatRevenue(valuation.revenue)} />
          <ValuationRow
            label="利潤率"
            value={valuation.profitMargin != null ? `${(valuation.profitMargin * 100).toFixed(1)}%` : null}
          />
        </div>

        {/* 市場資料 */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">市場資料</h2>
          <ValuationRow label="市值" value={formatMarketCap(valuation.marketCap)} />
          <ValuationRow
            label="股息殖利率"
            value={valuation.dividendYield != null ? `${valuation.dividendYield.toFixed(2)}%` : null}
          />
          <ValuationRow
            label="成交量（最新）"
            value={prices.length > 0 ? prices[prices.length - 1].volume.toLocaleString() : '—'}
          />
          <ValuationRow
            label="交易所"
            value={displayStock.market === 'US' ? 'NASDAQ / NYSE' : 'TWSE / TPEx'}
          />
          <ValuationRow
            label="52 週最高/最低"
            value={
              valuation.fiftyTwoWeekHigh != null || valuation.fiftyTwoWeekLow != null
                ? `${valuation.fiftyTwoWeekHigh?.toFixed(2) ?? '—'} / ${valuation.fiftyTwoWeekLow?.toFixed(2) ?? '—'}`
                : null
            }
          />
          <ValuationRow
            label="Beta"
            value={valuation.beta != null ? valuation.beta.toFixed(2) : null}
          />
        </div>

        {/* 進階估值 */}
        {(valuation.pegRatio != null || valuation.forwardPe != null || valuation.evToEbitda != null) && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">進階估值</h2>
            <ValuationRow
              label="PEG 比率"
              value={valuation.pegRatio != null ? valuation.pegRatio.toFixed(2) : null}
            />
            <ValuationRow
              label="預估本益比"
              value={valuation.forwardPe != null ? valuation.forwardPe.toFixed(1) : null}
            />
            <ValuationRow
              label="EV/EBITDA"
              value={valuation.evToEbitda != null ? valuation.evToEbitda.toFixed(1) : null}
            />
          </div>
        )}

        {/* 獲利能力 */}
        {(valuation.roe != null ||
          valuation.roa != null ||
          valuation.operatingMargin != null ||
          valuation.grossMargin != null ||
          valuation.freeCashFlow != null) && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">獲利能力</h2>
            <ValuationRow
              label="股東權益報酬率 (ROE)"
              value={valuation.roe != null ? `${(valuation.roe * 100).toFixed(1)}%` : null}
            />
            <ValuationRow
              label="資產報酬率 (ROA)"
              value={valuation.roa != null ? `${(valuation.roa * 100).toFixed(1)}%` : null}
            />
            <ValuationRow
              label="營業利益率"
              value={
                valuation.operatingMargin != null
                  ? `${(valuation.operatingMargin * 100).toFixed(1)}%`
                  : null
              }
            />
            <ValuationRow
              label="毛利率"
              value={
                valuation.grossMargin != null ? `${(valuation.grossMargin * 100).toFixed(1)}%` : null
              }
            />
            <ValuationRow label="自由現金流" value={formatMarketCap(valuation.freeCashFlow)} />
          </div>
        )}

        {/* 財務健康 */}
        {(valuation.debtToEquity != null ||
          valuation.currentRatio != null ||
          valuation.quickRatio != null) && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">財務健康</h2>
            <ValuationRow
              label="負債權益比"
              value={valuation.debtToEquity != null ? valuation.debtToEquity.toFixed(1) : null}
            />
            <ValuationRow
              label="流動比率"
              value={valuation.currentRatio != null ? valuation.currentRatio.toFixed(2) : null}
            />
            <ValuationRow
              label="速動比率"
              value={valuation.quickRatio != null ? valuation.quickRatio.toFixed(2) : null}
            />
          </div>
        )}

        {/* 成長指標 */}
        {(valuation.revenueGrowth != null || valuation.earningsGrowth != null) && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">成長指標</h2>
            <ValuationRow
              label="營收成長率"
              value={
                valuation.revenueGrowth != null
                  ? `${(valuation.revenueGrowth * 100).toFixed(1)}%`
                  : null
              }
            />
            <ValuationRow
              label="盈餘成長率"
              value={
                valuation.earningsGrowth != null
                  ? `${(valuation.earningsGrowth * 100).toFixed(1)}%`
                  : null
              }
            />
          </div>
        )}

        {/* 分析師評價 */}
        {(valuation.targetMeanPrice != null ||
          valuation.recommendationKey != null ||
          valuation.numberOfAnalysts != null) && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">分析師評價</h2>
            <ValuationRow
              label="目標價"
              value={
                valuation.targetMeanPrice != null ? valuation.targetMeanPrice.toFixed(2) : null
              }
            />
            <ValuationRow
              label="評級"
              value={
                valuation.recommendationKey != null
                  ? (
                      {
                        buy: '買入',
                        hold: '持有',
                        sell: '賣出',
                        strong_buy: '強力買入',
                        strong_sell: '強力賣出',
                      } as Record<string, string>
                    )[valuation.recommendationKey] ?? valuation.recommendationKey
                  : null
              }
            />
            <ValuationRow
              label="分析師人數"
              value={
                valuation.numberOfAnalysts != null ? String(valuation.numberOfAnalysts) : null
              }
            />
          </div>
        )}

        {/* 持股結構 */}
        {(valuation.insiderHolding != null ||
          valuation.institutionalHolding != null ||
          valuation.shortRatio != null ||
          valuation.shortPercentOfFloat != null) && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">持股結構</h2>
            <ValuationRow
              label="內部人持股"
              value={
                valuation.insiderHolding != null
                  ? `${(valuation.insiderHolding * 100).toFixed(1)}%`
                  : null
              }
            />
            <ValuationRow
              label="法人持股"
              value={
                valuation.institutionalHolding != null
                  ? `${(valuation.institutionalHolding * 100).toFixed(1)}%`
                  : null
              }
            />
            <ValuationRow
              label="做空比率"
              value={valuation.shortRatio != null ? valuation.shortRatio.toFixed(1) : null}
            />
            <ValuationRow
              label="做空佔流通比"
              value={
                valuation.shortPercentOfFloat != null
                  ? `${(valuation.shortPercentOfFloat * 100).toFixed(1)}%`
                  : null
              }
            />
          </div>
        )}

        {/* 股息詳情 */}
        {(valuation.dividendRate != null ||
          valuation.payoutRatio != null ||
          valuation.fiveYearAvgDividendYield != null) && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">股息詳情</h2>
            <ValuationRow
              label="年化股息"
              value={valuation.dividendRate != null ? valuation.dividendRate.toFixed(2) : null}
            />
            <ValuationRow
              label="配息率"
              value={
                valuation.payoutRatio != null
                  ? `${(valuation.payoutRatio * 100).toFixed(1)}%`
                  : null
              }
            />
            <ValuationRow
              label="五年平均殖利率"
              value={
                valuation.fiveYearAvgDividendYield != null
                  ? `${valuation.fiveYearAvgDividendYield.toFixed(2)}%`
                  : null
              }
            />
          </div>
        )}
      </div>

      {/* Company description */}
      {displayStock.description && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-gray-700 mb-2">公司簡介</h2>
          <p className="text-sm text-gray-600 leading-relaxed">{displayStock.description}</p>
        </div>
      )}
    </div>
  );
}
