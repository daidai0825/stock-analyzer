import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface EquityCurveProps {
  data: { date: string; value: number }[];
  initialCapital: number;
  height?: number;
}

function formatCurrency(v: number) {
  if (v >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
  if (v >= 1e3) return `$${(v / 1e3).toFixed(1)}K`;
  return `$${v.toFixed(0)}`;
}

interface TooltipPayloadItem {
  value: number;
}
interface TooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
}
function CustomTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg bg-gray-900 border border-gray-700 px-3 py-2 text-xs text-white shadow-lg">
      <p className="font-semibold mb-0.5">{label}</p>
      <p>Value: <span className="text-blue-300">{formatCurrency(payload[0]?.value ?? 0)}</span></p>
    </div>
  );
}

export function EquityCurveChart({ data, initialCapital, height = 280 }: EquityCurveProps) {
  if (data.length === 0) return null;

  const values = data.map((d) => d.value);
  const minV = Math.min(...values) * 0.97;
  const maxV = Math.max(...values) * 1.03;
  const total = data.length;
  const tickInterval = Math.max(1, Math.floor(total / 6));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: '#6b7280' }}
          interval={tickInterval}
          tickFormatter={(d) => d.slice(0, 7)}
        />
        <YAxis
          domain={[minV, maxV]}
          tick={{ fontSize: 10, fill: '#6b7280' }}
          tickFormatter={formatCurrency}
          width={64}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine
          y={initialCapital}
          stroke="#9ca3af"
          strokeDasharray="4 2"
          label={{ value: 'Initial', fill: '#9ca3af', fontSize: 10, position: 'insideTopRight' }}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke="#3b82f6"
          fill="url(#equityGradient)"
          strokeWidth={2}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
