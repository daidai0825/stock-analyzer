import { useEffect, useState } from 'react';
import type { IndicatorPoint, PricePoint } from '../types/stock';
import { fetchStockIndicators } from '../services/api';

export interface IndicatorSet {
  sma20: IndicatorPoint[];
  sma50: IndicatorPoint[];
  rsi14: IndicatorPoint[];
}

const EMPTY: IndicatorSet = { sma20: [], sma50: [], rsi14: [] };

// Backend expects underscored names: sma_20, sma_50, rsi_14
const API_INDICATOR_NAMES = 'sma_20,sma_50,rsi_14';

// ---------------------------------------------------------------------------
// Local fallback computations (used when the API is unavailable)
// ---------------------------------------------------------------------------

function computeSMA(prices: PricePoint[], period: number): IndicatorPoint[] {
  return prices.slice(period - 1).map((_, i) => {
    const slice = prices.slice(i, i + period);
    const avg = slice.reduce((s, p) => s + p.close, 0) / period;
    return { date: prices[i + period - 1].date, value: +avg.toFixed(2) };
  });
}

function computeRSI(prices: PricePoint[], period = 14): IndicatorPoint[] {
  const result: IndicatorPoint[] = [];
  for (let i = period; i < prices.length; i++) {
    let gains = 0;
    let losses = 0;
    for (let j = i - period + 1; j <= i; j++) {
      const diff = prices[j].close - prices[j - 1].close;
      if (diff > 0) gains += diff;
      else losses -= diff;
    }
    const avgGain = gains / period;
    const avgLoss = losses / period;
    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    const rsi = 100 - 100 / (1 + rs);
    result.push({ date: prices[i].date, value: +rsi.toFixed(2) });
  }
  return result;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Fetches technical indicators from the backend API.
 * Falls back to local computation if the API call fails.
 *
 * @param symbol - The stock ticker symbol; pass empty string to skip fetching.
 * @param prices - Price history used as fallback for local computation.
 */
export function useIndicators(prices: PricePoint[], symbol?: string): IndicatorSet {
  const [indicators, setIndicators] = useState<IndicatorSet>(EMPTY);

  useEffect(() => {
    if (!symbol || prices.length === 0) {
      setIndicators(EMPTY);
      return;
    }

    let cancelled = false;

    fetchStockIndicators(symbol, API_INDICATOR_NAMES)
      .then((raw) => {
        if (cancelled) return;
        setIndicators({
          sma20: raw['sma_20'] ?? [],
          sma50: raw['sma_50'] ?? [],
          rsi14: raw['rsi_14'] ?? [],
        });
      })
      .catch(() => {
        if (cancelled) return;
        // Fallback: compute locally from price history
        if (prices.length >= 50) {
          setIndicators({
            sma20: computeSMA(prices, 20),
            sma50: computeSMA(prices, 50),
            rsi14: computeRSI(prices, 14),
          });
        } else {
          setIndicators(EMPTY);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [symbol, prices]);

  return indicators;
}
