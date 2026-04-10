import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useStockSearch } from '../../hooks/useStockSearch';
import { isAuthenticated, logout } from '../../services/auth';
import type { Market } from '../../types/stock';

interface NavbarProps {
  market: Market;
  onMarketChange: (m: Market) => void;
}

export function Navbar({ market, onMarketChange }: NavbarProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [authed, setAuthed] = useState(isAuthenticated());
  const searchRef = useRef<HTMLDivElement>(null);

  function handleLogout() {
    logout();
    setAuthed(false);
    navigate('/login');
  }

  const { results, isLoading } = useStockSearch(query, market === 'ALL' ? 'ALL' : market);

  // Close dropdown on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  function handleSelect(symbol: string) {
    setQuery('');
    setShowDropdown(false);
    navigate(`/stocks/${symbol}`);
  }

  const navLinks = [
    { to: '/', label: '儀表板' },
    { to: '/screener', label: '股票篩選' },
    { to: '/backtest', label: '回測' },
    { to: '/watchlists', label: '觀察列表' },
    { to: '/alerts', label: '警報' },
  ];

  return (
    <nav className="bg-gray-900 text-white shadow-lg">
      <div className="mx-auto max-w-7xl px-4">
        <div className="flex h-14 items-center gap-6">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 font-bold text-lg text-white shrink-0">
            <svg
              className="h-6 w-6 text-blue-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z"
              />
            </svg>
            <span className="hidden sm:block">股票分析</span>
          </Link>

          {/* Nav links */}
          <div className="hidden md:flex items-center gap-1">
            {navLinks.map(({ to, label }) => (
              <Link
                key={to}
                to={to}
                className="px-3 py-2 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700 transition-colors"
              >
                {label}
              </Link>
            ))}
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Market toggle */}
          <div className="flex items-center rounded-md border border-gray-600 overflow-hidden text-xs font-semibold shrink-0">
            {(['US', 'TW'] as Market[]).map((m) => (
              <button
                key={m}
                onClick={() => onMarketChange(m)}
                className={`px-3 py-1.5 transition-colors ${
                  market === m
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-700'
                }`}
              >
                {m}
              </button>
            ))}
          </div>

          {/* Auth button */}
          {authed ? (
            <button
              onClick={handleLogout}
              className="shrink-0 rounded-md border border-gray-600 px-3 py-1.5 text-xs font-semibold text-gray-300 hover:bg-gray-700 transition-colors"
            >
              登出
            </button>
          ) : (
            <Link
              to="/login"
              className="shrink-0 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 transition-colors"
            >
              登入
            </Link>
          )}

          {/* Search */}
          <div ref={searchRef} className="relative w-48 sm:w-64">
            <input
              type="text"
              placeholder="搜尋代號或名稱..."
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setShowDropdown(true);
              }}
              onFocus={() => query && setShowDropdown(true)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && results.length > 0) {
                  handleSelect(results[0].symbol);
                }
                if (e.key === 'Escape') setShowDropdown(false);
              }}
              className="w-full rounded-md bg-gray-700 px-3 py-1.5 text-sm text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {showDropdown && (query.length > 0) && (
              <div className="absolute left-0 top-full mt-1 w-full rounded-md bg-white shadow-xl z-50 overflow-hidden">
                {isLoading ? (
                  <div className="px-4 py-3 text-sm text-gray-500">搜尋中...</div>
                ) : results.length === 0 ? (
                  <div className="px-4 py-3 text-sm text-gray-500">無結果</div>
                ) : (
                  <ul>
                    {results.map((stock) => (
                      <li key={stock.symbol}>
                        <button
                          onClick={() => handleSelect(stock.symbol)}
                          className="w-full text-left px-4 py-2 hover:bg-blue-50 transition-colors"
                        >
                          <span className="font-semibold text-gray-900 text-sm">
                            {stock.symbol}
                          </span>
                          <span className="ml-2 text-gray-500 text-xs">{stock.name}</span>
                          <span
                            className={`ml-1 text-xs font-medium px-1 rounded ${
                              stock.market === 'US'
                                ? 'bg-blue-100 text-blue-700'
                                : 'bg-green-100 text-green-700'
                            }`}
                          >
                            {stock.market}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
