import { useMemo } from 'react';
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { IndicatorPoint, PricePoint } from '../../types/stock';

interface PriceChartProps {
  prices: PricePoint[];
  sma20?: IndicatorPoint[];
  sma50?: IndicatorPoint[];
  showSMA20?: boolean;
  showSMA50?: boolean;
  height?: number;
}

interface ChartRow {
  date: string;
  close: number;
  volume: number;
  sma20?: number;
  sma50?: number;
  min: number;
  max: number;
}

function formatVolume(v: number) {
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return String(v);
}

function formatDate(date: string, total: number) {
  if (total <= 30) return date.slice(5); // MM-DD
  if (total <= 365) return date.slice(5); // MM-DD
  return date.slice(0, 7); // YYYY-MM
}

// Custom tooltip
interface TooltipPayloadItem {
  payload: ChartRow;
}
interface TooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
}
function CustomTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const row: ChartRow = payload[0]?.payload;
  if (!row) return null;

  return (
    <div className="rounded-lg bg-gray-900 border border-gray-700 px-3 py-2 text-xs text-white shadow-lg">
      <p className="font-semibold mb-1">{row.date}</p>
      <p>收盤：<span className="text-blue-300">${row.close.toFixed(2)}</span></p>
      {row.sma20 != null && (
        <p>SMA20：<span className="text-orange-300">${row.sma20.toFixed(2)}</span></p>
      )}
      {row.sma50 != null && (
        <p>SMA50：<span className="text-purple-300">${row.sma50.toFixed(2)}</span></p>
      )}
      <p>成交量：<span className="text-gray-300">{formatVolume(row.volume)}</span></p>
    </div>
  );
}

export function PriceChart({
  prices,
  sma20 = [],
  sma50 = [],
  showSMA20 = false,
  showSMA50 = false,
  height = 420,
}: PriceChartProps) {
  const chartData = useMemo<ChartRow[]>(() => {
    const sma20Map = Object.fromEntries(sma20.map((p) => [p.date, p.value]));
    const sma50Map = Object.fromEntries(sma50.map((p) => [p.date, p.value]));

    return prices.map((p) => ({
      date: p.date,
      close: p.close,
      volume: p.volume,
      min: p.low,
      max: p.high,
      ...(showSMA20 && sma20Map[p.date] != null ? { sma20: sma20Map[p.date] } : {}),
      ...(showSMA50 && sma50Map[p.date] != null ? { sma50: sma50Map[p.date] } : {}),
    }));
  }, [prices, sma20, sma50, showSMA20, showSMA50]);

  if (prices.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-gray-400 text-sm"
        style={{ height }}
      >
        無資料可顯示
      </div>
    );
  }

  const total = chartData.length;
  const priceMin = Math.min(...prices.map((p) => p.low)) * 0.98;
  const priceMax = Math.max(...prices.map((p) => p.high)) * 1.02;
  const volumeMax = Math.max(...prices.map((p) => p.volume));

  // Tick reduction
  const tickInterval = Math.max(1, Math.floor(total / 6));

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="70%">
        <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: '#6b7280' }}
            tickFormatter={(v) => formatDate(v, total)}
            interval={tickInterval}
          />
          <YAxis
            domain={[priceMin, priceMax]}
            tick={{ fontSize: 10, fill: '#6b7280' }}
            tickFormatter={(v) => `$${v.toFixed(0)}`}
            width={60}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="close"
            stroke="#3b82f6"
            fill="#eff6ff"
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 3 }}
          />
          {showSMA20 && (
            <Line
              type="monotone"
              dataKey="sma20"
              stroke="#f97316"
              strokeWidth={1.5}
              dot={false}
              connectNulls
            />
          )}
          {showSMA50 && (
            <Line
              type="monotone"
              dataKey="sma50"
              stroke="#a855f7"
              strokeWidth={1.5}
              dot={false}
              connectNulls
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Volume chart */}
      <ResponsiveContainer width="100%" height="28%">
        <ComposedChart data={chartData} margin={{ top: 2, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="date"
            tick={false}
            height={0}
          />
          <YAxis
            tickFormatter={formatVolume}
            tick={{ fontSize: 9, fill: '#9ca3af' }}
            width={60}
            domain={[0, volumeMax * 1.2]}
          />
          <Bar dataKey="volume" fill="#93c5fd" opacity={0.7} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
