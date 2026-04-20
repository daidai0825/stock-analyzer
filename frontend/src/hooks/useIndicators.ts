import { useEffect, useState } from 'react';
import type { IndicatorPoint, PricePoint } from '../types/stock';
import { fetchStockIndicators } from '../services/api';

export interface MacdPoint {
  date: string;
  macd: number;
  signal: number;
  histogram: number;
}

export interface IndicatorSet {
  sma20: IndicatorPoint[];
  sma50: IndicatorPoint[];
  rsi14: IndicatorPoint[];
  macd: MacdPoint[];
  bollingerUpper: IndicatorPoint[];
  bollingerMiddle: IndicatorPoint[];
  bollingerLower: IndicatorPoint[];
  kd_k: IndicatorPoint[];
  kd_d: IndicatorPoint[];
}

const EMPTY: IndicatorSet = {
  sma20: [],
  sma50: [],
  rsi14: [],
  macd: [],
  bollingerUpper: [],
  bollingerMiddle: [],
  bollingerLower: [],
  kd_k: [],
  kd_d: [],
};

// Backend expects underscored names
const API_INDICATOR_NAMES = 'sma_20,sma_50,rsi_14,macd,bollinger_bands,kd';

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
// Helper: convert raw MACD API response to MacdPoint[]
// ---------------------------------------------------------------------------

function parseMacdPoints(raw: Record<string, { date: string; value: number }[]>): MacdPoint[] {
  const macdLine = raw['macd_line'] ?? raw['macd'] ?? [];
  const signalLine = raw['signal_line'] ?? raw['signal'] ?? [];
  const histogram = raw['histogram'] ?? [];
  if (macdLine.length === 0) return [];
  const signalMap = Object.fromEntries(signalLine.map((p) => [p.date, p.value]));
  const histMap = Object.fromEntries(histogram.map((p) => [p.date, p.value]));
  return macdLine.map((p) => ({
    date: p.date,
    macd: p.value,
    signal: signalMap[p.date] ?? 0,
    histogram: histMap[p.date] ?? 0,
  }));
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Fetches technical indicators from the backend API.
 * Falls back to local computation for SMA/RSI if the API call fails.
 *
 * @param prices - Price history used as fallback for local computation.
 * @param symbol - The stock ticker symbol; pass empty string to skip fetching.
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

        const bollingerUpper: IndicatorPoint[] = raw['bollinger_upper'] ?? raw['upper_band'] ?? [];
        const bollingerMiddle: IndicatorPoint[] =
          raw['bollinger_middle'] ?? raw['middle_band'] ?? [];
        const bollingerLower: IndicatorPoint[] = raw['bollinger_lower'] ?? raw['lower_band'] ?? [];

        setIndicators({
          sma20: raw['sma_20'] ?? [],
          sma50: raw['sma_50'] ?? [],
          rsi14: raw['rsi_14'] ?? [],
          macd: parseMacdPoints(raw),
          bollingerUpper,
          bollingerMiddle,
          bollingerLower,
          kd_k: raw['kd_k'] ?? raw['k_value'] ?? [],
          kd_d: raw['kd_d'] ?? raw['d_value'] ?? [],
        });
      })
      .catch(() => {
        if (cancelled) return;
        // Fallback: compute SMA/RSI locally from price history
        if (prices.length >= 50) {
          setIndicators({
            ...EMPTY,
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
