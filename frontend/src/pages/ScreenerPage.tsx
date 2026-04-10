import { useState } from 'react';
import { ConditionList } from '../components/screener/ConditionList';
import { ResultsTable } from '../components/screener/ResultsTable';
import { Spinner } from '../components/common/Spinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import type { Market, ScreenerCondition, Stock } from '../types/stock';
import { runScreener } from '../services/api';

const PAGE_LIMIT = 20;

export function ScreenerPage() {
  const [conditions, setConditions] = useState<ScreenerCondition[]>([]);
  const [market, setMarket] = useState<Market>('US');
  const [results, setResults] = useState<Stock[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  async function handleRun() {
    setIsLoading(true);
    setError(null);
    setPage(1);
    try {
      const data = await runScreener({
        conditions,
        market: market === 'ALL' ? undefined : market,
        limit: 200,
      });
      setResults(data);
    } catch {
      setError('Screener failed. Please check your conditions and try again.');
      setResults(null);
    } finally {
      setIsLoading(false);
    }
  }

  const pagedResults = results?.slice((page - 1) * PAGE_LIMIT, page * PAGE_LIMIT) ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Stock Screener</h1>
        <p className="text-sm text-gray-500 mt-1">Filter stocks using technical and fundamental criteria</p>
      </div>

      {/* Filter panel */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm space-y-5">
        {/* Market selector */}
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-700">Market:</span>
          <div className="flex rounded-md border border-gray-300 overflow-hidden text-sm">
            {(['US', 'TW', 'ALL'] as Market[]).map((m) => (
              <button
                key={m}
                onClick={() => setMarket(m)}
                className={`px-3 py-1.5 font-medium transition-colors ${
                  market === m
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        {/* Conditions */}
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Conditions</h3>
          <ConditionList conditions={conditions} onChange={setConditions} />
        </div>

        {/* Run */}
        <button
          onClick={() => void handleRun()}
          disabled={isLoading}
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60 transition-colors flex items-center gap-2"
        >
          {isLoading ? (
            <>
              <Spinner size="sm" className="border-white border-t-blue-300" />
              Running...
            </>
          ) : (
            'Run Screen'
          )}
        </button>
      </div>

      {/* Error */}
      {error && <ErrorMessage message={error} onRetry={() => void handleRun()} />}

      {/* Results */}
      {results !== null && !error && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">
            Results{' '}
            <span className="font-normal text-gray-400">({results.length} stocks)</span>
          </h2>
          <ResultsTable
            results={pagedResults}
            page={page}
            limit={PAGE_LIMIT}
            total={results.length}
            onPageChange={setPage}
          />
        </div>
      )}
    </div>
  );
}
