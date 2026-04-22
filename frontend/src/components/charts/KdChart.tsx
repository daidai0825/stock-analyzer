import {
  CartesianGrid,
  Legend,
  LineChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useMemo } from 'react';
import type { IndicatorPoint } from '../../types/stock';

interface KdChartProps {
  kData: IndicatorPoint[];
  dData: IndicatorPoint[];
  height?: number;
}

interface ChartRow {
  date: string;
  k?: number;
  d?: number;
}

interface TooltipPayloadItem {
  name: string;
  value: number;
  color: string;
}
interface TooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded-lg bg-gray-900 border border-gray-700 px-3 py-2 text-xs text-white shadow-lg">
      <p className="font-semibold mb-1">{label}</p>
      {payload.map((item) => (
        <p key={item.name}>
          {item.name}：<span style={{ color: item.color }}>{item.value?.toFixed(2)}</span>
        </p>
      ))}
    </div>
  );
}

export function KdChart({ kData, dData, height = 160 }: KdChartProps) {
  const chartData = useMemo<ChartRow[]>(() => {
    const dMap = Object.fromEntries(dData.map((p) => [p.date, p.value]));
    return kData.map((p) => ({
      date: p.date,
      k: p.value,
      d: dMap[p.date],
    }));
  }, [kData, dData]);

  if (kData.length === 0 && dData.length === 0) {
    return (
      <div className="flex items-center justify-center text-gray-400 text-xs" style={{ height }}>
        無 KD 資料
      </div>
    );
  }

  const total = chartData.length;
  const tickInterval = Math.max(1, Math.floor(total / 6));

  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">KD 指標</p>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 2, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: '#6b7280' }}
            interval={tickInterval}
          />
          <YAxis domain={[0, 100]} tick={{ fontSize: 9, fill: '#9ca3af' }} width={40} />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            iconSize={10}
            wrapperStyle={{ fontSize: '11px' }}
            formatter={(value) => (value === 'k' ? 'K 值' : 'D 值')}
          />
          <ReferenceLine
            y={80}
            stroke="#ef4444"
            strokeDasharray="4 2"
            label={{ value: '超買 80', fill: '#ef4444', fontSize: 9, position: 'insideRight' }}
          />
          <ReferenceLine
            y={20}
            stroke="#22c55e"
            strokeDasharray="4 2"
            label={{ value: '超賣 20', fill: '#22c55e', fontSize: 9, position: 'insideRight' }}
          />
          <Line
            type="monotone"
            dataKey="k"
            name="k"
            stroke="#3b82f6"
            strokeWidth={1.5}
            dot={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="d"
            name="d"
            stroke="#f97316"
            strokeWidth={1.5}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
