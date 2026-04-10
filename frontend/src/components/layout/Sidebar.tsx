import { Link } from 'react-router-dom';
import { useWatchlists } from '../../hooks/useWatchlists';

const RECENT_SEARCHES_KEY = 'stock_analyzer_recent';

export function getRecentSearches(): string[] {
  try {
    return JSON.parse(localStorage.getItem(RECENT_SEARCHES_KEY) ?? '[]');
  } catch {
    return [];
  }
}

export function addRecentSearch(symbol: string) {
  const existing = getRecentSearches().filter((s) => s !== symbol);
  const updated = [symbol, ...existing].slice(0, 5);
  localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(updated));
}

export function Sidebar() {
  const { watchlists, isLoading } = useWatchlists();
  const recent = getRecentSearches();

  return (
    <aside className="w-56 shrink-0 hidden lg:block">
      <div className="space-y-6">
        {/* Recent Searches */}
        {recent.length > 0 && (
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
              最近瀏覽
            </h3>
            <ul className="space-y-1">
              {recent.map((symbol) => (
                <li key={symbol}>
                  <Link
                    to={`/stocks/${symbol}`}
                    className="block rounded-md px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                  >
                    {symbol}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Watchlists */}
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
            觀察列表
          </h3>
          {isLoading ? (
            <div className="space-y-1">
              {[1, 2].map((i) => (
                <div key={i} className="h-6 bg-gray-200 rounded animate-pulse" />
              ))}
            </div>
          ) : (
            <ul className="space-y-1">
              {watchlists.map((wl) => (
                <li key={wl.id}>
                  <Link
                    to={`/watchlists`}
                    className="block rounded-md px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                  >
                    <span className="font-medium">{wl.name}</span>
                    <span className="ml-1 text-xs text-gray-400">({wl.items.length})</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </aside>
  );
}
