import { useEffect, useRef, useState } from 'react';
import type { Stock } from '../types/stock';
import { searchStocks } from '../services/api';

/**
 * Debounced stock search hook.
 * Calls the real search API; falls back to empty results on error.
 */
export function useStockSearch(query: string, market: string, debounceMs = 300) {
  const [results, setResults] = useState<Stock[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (abortRef.current) abortRef.current.abort();

    if (!query.trim()) {
      setResults([]);
      setError(null);
      return;
    }

    timerRef.current = setTimeout(async () => {
      abortRef.current = new AbortController();
      setIsLoading(true);
      setError(null);
      try {
        const apiMarket = market === 'ALL' ? 'US' : market;
        const data = await searchStocks(query, apiMarket);
        const filtered =
          market === 'ALL' ? data : data.filter((s) => s.market === market);
        setResults(filtered.slice(0, 10));
      } catch (err: unknown) {
        // Ignore aborted requests
        if (err instanceof Error && err.name === 'CanceledError') return;
        setError('Search failed');
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    }, debounceMs);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (abortRef.current) abortRef.current.abort();
    };
  }, [query, market, debounceMs]);

  return { results, isLoading, error };
}
