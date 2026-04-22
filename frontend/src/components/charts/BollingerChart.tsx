import { useMemo } from 'react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { IndicatorPoint, PricePoint } from '../../types/stock';

interface BollingerChartProps {
  prices: PricePoint[];
  upper: IndicatorPoint[];
  middle: IndicatorPoint[];
  lower: IndicatorPoint[];
  height?: number;
}

interface ChartRow {
  date: string;
  close: number;
  upper?: number;
  middle?: number;
  lower?: number;
  bandRange?: [number, number];
}

interface TooltipPayloadItem {
  name: string;
  value: number | number[];
  color: string;
}
interface TooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const closeItem = payload.find((p) => p.name === '收盤價');
  const upperItem = payload.find((p) => p.name === '上軌');
  const middleItem = payload.find((p) => p.name === '中軌');
  const lowerItem = payload.find((p) => p.name === '下軌');
  return (
    <div className="rounded-lg bg-gray-900 border border-gray-700 px-3 py-2 text-xs text-white shadow-lg">
      <p className="font-semibold mb-1">{label}</p>
      {closeItem && (
        <p>
          收盤價：<span className="text-blue-300">${(closeItem.value as number).toFixed(2)}</span>
        </p>
      )}
      {upperItem && (
        <p>
          上軌：<span className="text-gray-300">${(upperItem.value as number).toFixed(2)}</span>
        </p>
      )}
      {middleItem && (
        <p>
          中軌：<span className="text-yellow-300">${(middleItem.value as number).toFixed(2)}</span>
        </p>
      )}
      {lowerItem && (
        <p>
          下軌：<span className="text-gray-300">${(lowerItem.value as number).toFixed(2)}</span>
        </p>
      )}
    </div>
  );
}

export function BollingerChart({ prices, upper, middle, lower, height = 200 }: BollingerChartProps) {
  const chartData = useMemo<ChartRow[]>(() => {
    if (prices.length === 0) return [];
    const upperMap = Object.fromEntries(upper.map((p) => [p.date, p.value]));
    const middleMap = Object.fromEntries(middle.map((p) => [p.date, p.value]));
    const lowerMap = Object.fromEntries(lower.map((p) => [p.date, p.value]));

    return prices.map((p) => {
      const u = upperMap[p.date];
      const l = lowerMap[p.date];
      return {
        date: p.date,
        close: p.close,
        upper: u,
        middle: middleMap[p.date],
        lower: l,
        // Area range for band fill: [lower, upper]
        bandRange: u != null && l != null ? [l, u] : undefined,
      };
    });
  }, [prices, upper, middle, lower]);

  if (chartData.length === 0 || (upper.length === 0 && middle.length === 0 && lower.length === 0)) {
    return (
      <div className="flex items-center justify-center text-gray-400 text-xs" style={{ height }}>
        無布林通道資料
      </div>
    );
  }

  const total = chartData.length;
  const tickInterval = Math.max(1, Math.floor(total / 6));
  const allPrices = prices.map((p) => p.close);
  const allUpper = upper.map((p) => p.value);
  const allLower = lower.map((p) => p.value);
  const allValues = [...allPrices, ...allUpper, ...allLower].filter((v) => v != null);
  const yMin = Math.min(...allValues) * 0.98;
  const yMax = Math.max(...allValues) * 1.02;

  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">布林通道</p>
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={chartData} margin={{ top: 2, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: '#6b7280' }}
            interval={tickInterval}
          />
          <YAxis
            domain={[yMin, yMax]}
            tick={{ fontSize: 9, fill: '#9ca3af' }}
            width={60}
            tickFormatter={(v) => `$${v.toFixed(0)}`}
          />
          <Tooltip content={<CustomTooltip />} />
          {/* Band fill area using upper as value and lower as baseline */}
          <Area
            type="monotone"
            dataKey="upper"
            name="上軌"
            stroke="#9ca3af"
            strokeWidth={1}
            fill="#f3f4f6"
            fillOpacity={0.6}
            dot={false}
            activeDot={false}
          />
          <Area
            type="monotone"
            dataKey="lower"
            name="下軌"
            stroke="#9ca3af"
            strokeWidth={1}
            fill="#ffffff"
            fillOpacity={1}
            dot={false}
            activeDot={false}
          />
          <Line
            type="monotone"
            dataKey="middle"
            name="中軌"
            stroke="#eab308"
            strokeWidth={1.5}
            strokeDasharray="4 2"
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="close"
            name="收盤價"
            stroke="#3b82f6"
            strokeWidth={1.5}
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
