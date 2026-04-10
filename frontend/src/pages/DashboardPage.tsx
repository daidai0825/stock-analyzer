import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useWatchlists } from '../hooks/useWatchlists';
import { Spinner } from '../components/common/Spinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { fetchStocks } from '../services/api';
import type { Stock } from '../types/stock';

function MarketCard({
  market,
  stocks,
  isLoading,
  error,
}: {
  market: 'US' | 'TW';
  stocks: Stock[];
  isLoading: boolean;
  error: string | null;
}) {
  const gainers = stocks.filter((s) => (s.changePercent ?? 0) > 0).length;
  const losers = stocks.filter((s) => (s.changePercent ?? 0) < 0).length;

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900">{market === 'US' ? '美股市場' : '台股市場'}</h3>
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            market === 'US' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'
          }`}
        >
          {market}
        </span>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-6"><Spinner /></div>
      ) : error ? (
        <ErrorMessage message={error} />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="text-center rounded-lg bg-green-50 py-2">
              <p className="text-lg font-bold text-green-600">{gainers}</p>
              <p className="text-xs text-green-500">漲幅</p>
            </div>
            <div className="text-center rounded-lg bg-red-50 py-2">
              <p className="text-lg font-bold text-red-600">{losers}</p>
              <p className="text-xs text-red-500">跌幅</p>
            </div>
          </div>
          <ul className="space-y-1.5">
            {stocks.slice(0, 4).map((s) => (
              <li key={s.symbol} className="flex items-center justify-between">
                <Link
                  to={`/stocks/${s.symbol}`}
                  className="text-sm font-semibold text-blue-600 hover:underline"
                >
                  {s.symbol}
                </Link>
                <span className="text-sm font-mono text-gray-700">
                  {s.price != null ? `$${s.price.toFixed(2)}` : '—'}
                </span>
                <span
                  className={`text-xs font-mono ${
                    (s.changePercent ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {(s.changePercent ?? 0) >= 0 ? '+' : ''}
                  {(s.changePercent ?? 0).toFixed(2)}%
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export function DashboardPage() {
  const navigate = useNavigate();
  const { watchlists, isLoading: watchlistsLoading } = useWatchlists();

  const [usStocks, setUsStocks] = useState<Stock[]>([]);
  const [twStocks, setTwStocks] = useState<Stock[]>([]);
  const [usLoading, setUsLoading] = useState(true);
  const [twLoading, setTwLoading] = useState(true);
  const [usError, setUsError] = useState<string | null>(null);
  const [twError, setTwError] = useState<string | null>(null);

  useEffect(() => {
    fetchStocks({ market: 'US', limit: 20 })
      .then((res) => setUsStocks(res.data))
      .catch(() => setUsError('無法載入美股市場資料'))
      .finally(() => setUsLoading(false));

    fetchStocks({ market: 'TW', limit: 20 })
      .then((res) => setTwStocks(res.data))
      .catch(() => setTwError('無法載入台股市場資料'))
      .finally(() => setTwLoading(false));
  }, []);

  return (
    <div className="space-y-8">
      {/* Hero search */}
      <div className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-700 p-8 text-white">
        <h1 className="text-2xl font-bold mb-1">股票分析</h1>
        <p className="text-blue-100 mb-5 text-sm">分析美股與台股 — 圖表、篩選器、回測一站搞定</p>
        <div className="flex gap-2 max-w-md">
          <input
            type="text"
            placeholder="快速搜尋：AAPL、2330..."
            className="flex-1 rounded-lg px-4 py-2.5 text-gray-900 text-sm focus:outline-none"
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                const val = (e.target as HTMLInputElement).value.trim().toUpperCase();
                if (val) navigate(`/stocks/${val}`);
              }
            }}
          />
          <button
            className="rounded-lg bg-white/20 px-4 py-2.5 text-sm font-semibold hover:bg-white/30 transition-colors"
          >
            搜尋
          </button>
        </div>
      </div>

      {/* Market overview */}
      <div>
        <h2 className="text-lg font-bold text-gray-900 mb-4">市場概覽</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <MarketCard market="US" stocks={usStocks} isLoading={usLoading} error={usError} />
          <MarketCard market="TW" stocks={twStocks} isLoading={twLoading} error={twError} />
        </div>
      </div>

      {/* Quick links */}
      <div>
        <h2 className="text-lg font-bold text-gray-900 mb-4">工具</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Link
            to="/screener"
            className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md hover:border-blue-300 transition-all"
          >
            <div className="mb-2 h-8 w-8 rounded-lg bg-purple-100 flex items-center justify-center">
              <svg className="h-4 w-4 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 010 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h10a1 1 0 010 2H4a1 1 0 01-1-1zM3 16a1 1 0 011-1h4a1 1 0 010 2H4a1 1 0 01-1-1z" />
              </svg>
            </div>
            <h3 className="font-semibold text-gray-900">股票篩選</h3>
            <p className="text-xs text-gray-500 mt-1">依技術面與基本面條件篩選股票</p>
          </Link>
          <Link
            to="/backtest"
            className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md hover:border-blue-300 transition-all"
          >
            <div className="mb-2 h-8 w-8 rounded-lg bg-orange-100 flex items-center justify-center">
              <svg className="h-4 w-4 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 className="font-semibold text-gray-900">回測系統</h3>
            <p className="text-xs text-gray-500 mt-1">以歷史數據測試交易策略</p>
          </Link>
          <Link
            to="/watchlists"
            className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md hover:border-blue-300 transition-all"
          >
            <div className="mb-2 h-8 w-8 rounded-lg bg-green-100 flex items-center justify-center">
              <svg className="h-4 w-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
            </div>
            <h3 className="font-semibold text-gray-900">觀察列表</h3>
            <p className="text-xs text-gray-500 mt-1">追蹤你關注的股票</p>
          </Link>
        </div>
      </div>

      {/* Watchlist preview */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-900">你的觀察列表</h2>
          <Link to="/watchlists" className="text-sm text-blue-600 hover:underline">
            查看全部
          </Link>
        </div>
        {watchlistsLoading ? (
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : watchlists.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center text-gray-400 text-sm">
            尚無觀察列表。{' '}
            <Link to="/watchlists" className="text-blue-500 hover:underline">
              建立一個
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {watchlists.slice(0, 3).map((wl) => (
              <div
                key={wl.id}
                className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
              >
                <h3 className="font-semibold text-gray-900 mb-2">{wl.name}</h3>
                <div className="flex flex-wrap gap-1.5">
                  {wl.items.map((item) => (
                    <Link
                      key={item.id}
                      to={`/stocks/${item.symbol}`}
                      className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700 hover:bg-blue-100 hover:text-blue-700 transition-colors"
                    >
                      {item.symbol}
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
