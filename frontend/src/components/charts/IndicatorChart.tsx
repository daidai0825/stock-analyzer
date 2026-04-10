import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { IndicatorPoint } from '../../types/stock';

interface IndicatorChartProps {
  data: IndicatorPoint[];
  label: string;
  color?: string;
  height?: number;
  domain?: [number, number];
  referenceLines?: { value: number; color: string; label: string }[];
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
      <p className="font-semibold">{label}</p>
      <p>
        {payload[0]?.name}:{' '}
        <span style={{ color: payload[0]?.color }}>{payload[0]?.value?.toFixed(2)}</span>
      </p>
    </div>
  );
}

export function IndicatorChart({
  data,
  label,
  color = '#6366f1',
  height = 140,
  domain,
  referenceLines = [],
}: IndicatorChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center text-gray-400 text-xs" style={{ height }}>
        無指標資料
      </div>
    );
  }

  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 2, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="date" tick={false} height={0} />
          <YAxis
            domain={domain ?? ['auto', 'auto']}
            tick={{ fontSize: 9, fill: '#9ca3af' }}
            width={40}
          />
          <Tooltip content={<CustomTooltip />} />
          {referenceLines.map((rl) => (
            <ReferenceLine
              key={rl.value}
              y={rl.value}
              stroke={rl.color}
              strokeDasharray="4 2"
              label={{ value: rl.label, fill: rl.color, fontSize: 9, position: 'insideRight' }}
            />
          ))}
          <Line
            type="monotone"
            dataKey="value"
            name={label}
            stroke={color}
            strokeWidth={1.5}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
