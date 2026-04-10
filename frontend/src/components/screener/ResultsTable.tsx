import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { Stock } from '../../types/stock';

type SortKey = 'symbol' | 'name' | 'price' | 'change' | 'changePercent' | 'volume';

interface ResultsTableProps {
  results: Stock[];
  page: number;
  limit: number;
  total: number;
  onPageChange: (page: number) => void;
}

function formatVolume(v?: number) {
  if (v == null) return '—';
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return String(v);
}

export function ResultsTable({ results, page, limit, total, onPageChange }: ResultsTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('symbol');
  const [sortAsc, setSortAsc] = useState(true);

  function toggleSort(key: SortKey) {
    if (key === sortKey) setSortAsc((v) => !v);
    else { setSortKey(key); setSortAsc(true); }
  }

  const sorted = [...results].sort((a, b) => {
    let av: string | number = a[sortKey] ?? '';
    let bv: string | number = b[sortKey] ?? '';
    if (typeof av === 'string') av = av.toLowerCase();
    if (typeof bv === 'string') bv = bv.toLowerCase();
    if (av < bv) return sortAsc ? -1 : 1;
    if (av > bv) return sortAsc ? 1 : -1;
    return 0;
  });

  const totalPages = Math.max(1, Math.ceil(total / limit));

  function SortIcon({ col }: { col: SortKey }) {
    if (sortKey !== col) return <span className="text-gray-300 ml-1">↕</span>;
    return <span className="text-blue-500 ml-1">{sortAsc ? '↑' : '↓'}</span>;
  }

  const thClass =
    'cursor-pointer select-none px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 hover:text-gray-900 whitespace-nowrap';

  return (
    <div>
      <div className="mb-2 text-sm text-gray-500">
        {total} result{total !== 1 ? 's' : ''}
      </div>
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className={thClass} onClick={() => toggleSort('symbol')}>
                Symbol <SortIcon col="symbol" />
              </th>
              <th className={thClass} onClick={() => toggleSort('name')}>
                Name <SortIcon col="name" />
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
                Market
              </th>
              <th className={thClass} onClick={() => toggleSort('price')}>
                Price <SortIcon col="price" />
              </th>
              <th className={thClass} onClick={() => toggleSort('changePercent')}>
                Change% <SortIcon col="changePercent" />
              </th>
              <th className={thClass} onClick={() => toggleSort('volume')}>
                Volume <SortIcon col="volume" />
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
                Industry
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-gray-400">
                  No results match your criteria
                </td>
              </tr>
            ) : (
              sorted.map((stock) => (
                <tr key={stock.symbol} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-semibold text-blue-600">
                    <Link to={`/stocks/${stock.symbol}`} className="hover:underline">
                      {stock.symbol}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-gray-900">{stock.name}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        stock.market === 'US'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-green-100 text-green-700'
                      }`}
                    >
                      {stock.market}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-900">
                    {stock.price != null ? `$${stock.price.toFixed(2)}` : '—'}
                  </td>
                  <td className="px-4 py-3 font-mono">
                    {stock.changePercent != null ? (
                      <span
                        className={stock.changePercent >= 0 ? 'text-green-600' : 'text-red-600'}
                      >
                        {stock.changePercent >= 0 ? '+' : ''}
                        {stock.changePercent.toFixed(2)}%
                      </span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-700">{formatVolume(stock.volume)}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{stock.industry ?? '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <span className="text-sm text-gray-500">
            Page {page} of {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-40 hover:bg-gray-50 transition-colors"
            >
              Previous
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-40 hover:bg-gray-50 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
