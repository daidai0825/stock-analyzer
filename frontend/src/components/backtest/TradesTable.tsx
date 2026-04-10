import { useState } from 'react';
import type { BacktestResult } from '../../types/stock';

interface TradesTableProps {
  trades: BacktestResult['trades'];
}

const PAGE_SIZE = 10;

export function TradesTable({ trades }: TradesTableProps) {
  const [page, setPage] = useState(1);

  const total = trades.length;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const slice = trades.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div>
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {['Date', 'Action', 'Price', 'Shares', 'Value'].map((h) => (
                <th
                  key={h}
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {slice.map((trade, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 text-gray-700 font-mono">{trade.date}</td>
                <td className="px-4 py-2.5">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                      trade.action === 'BUY'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-red-100 text-red-700'
                    }`}
                  >
                    {trade.action}
                  </span>
                </td>
                <td className="px-4 py-2.5 font-mono text-gray-900">${trade.price.toFixed(2)}</td>
                <td className="px-4 py-2.5 font-mono text-gray-700">{trade.shares}</td>
                <td className="px-4 py-2.5 font-mono text-gray-700">
                  ${(trade.price * trade.shares).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </td>
              </tr>
            ))}
            {slice.length === 0 && (
              <tr>
                <td colSpan={5} className="py-8 text-center text-gray-400">
                  No trades
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="mt-3 flex items-center justify-between">
          <span className="text-xs text-gray-500">
            Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}
          </span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="rounded border border-gray-300 px-2.5 py-1 text-xs disabled:opacity-40 hover:bg-gray-50"
            >
              Prev
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="rounded border border-gray-300 px-2.5 py-1 text-xs disabled:opacity-40 hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
