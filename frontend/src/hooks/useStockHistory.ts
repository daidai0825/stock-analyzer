import { useEffect, useState } from 'react';
import type { PricePoint } from '../types/stock';
import { fetchStockHistory } from '../services/api';

/** Maps UI period labels to the API's period parameter. */
function toApiPeriod(period: string): string {
  switch (period) {
    case '1W': return '5d';
    case '1M': return '1mo';
    case '3M': return '3mo';
    case '6M': return '6mo';
    case '1Y': return '1y';
    case '5Y': return '5y';
    default:   return '1y';
  }
}

/**
 * Fetches OHLCV price history for a symbol via the backend API.
 */
export function useStockHistory(symbol: string, period = '1Y') {
  const [data, setData] = useState<PricePoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!symbol) return;

    let cancelled = false;
    setIsLoading(true);
    setError(null);

    fetchStockHistory(symbol, toApiPeriod(period))
      .then((prices) => {
        if (!cancelled) setData(prices);
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load price history');
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [symbol, period]);

  return { data, isLoading, error };
}
