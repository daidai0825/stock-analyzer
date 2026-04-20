import {
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface MacdDataPoint {
  date: string;
  macd: number;
  signal: number;
  histogram: number;
}

interface MacdChartProps {
  data: MacdDataPoint[];
  height?: number;
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
  const macd = payload.find((p) => p.name === 'MACD');
  const signal = payload.find((p) => p.name === 'Signal');
  const histogram = payload.find((p) => p.name === '柱狀');
  return (
    <div className="rounded-lg bg-gray-900 border border-gray-700 px-3 py-2 text-xs text-white shadow-lg">
      <p className="font-semibold mb-1">{label}</p>
      {macd && (
        <p>
          MACD：<span className="text-blue-300">{macd.value.toFixed(4)}</span>
        </p>
      )}
      {signal && (
        <p>
          Signal：<span className="text-orange-300">{signal.value.toFixed(4)}</span>
        </p>
      )}
      {histogram && (
        <p>
          柱狀：
          <span className={histogram.value >= 0 ? 'text-green-300' : 'text-red-300'}>
            {histogram.value.toFixed(4)}
          </span>
        </p>
      )}
    </div>
  );
}

export function MacdChart({ data, height = 160 }: MacdChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center text-gray-400 text-xs" style={{ height }}>
        無 MACD 資料
      </div>
    );
  }

  const total = data.length;
  const tickInterval = Math.max(1, Math.floor(total / 6));

  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">MACD</p>
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={data} margin={{ top: 2, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: '#6b7280' }}
            interval={tickInterval}
          />
          <YAxis tick={{ fontSize: 9, fill: '#9ca3af' }} width={50} />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={0} stroke="#d1d5db" />
          <Bar dataKey="histogram" name="柱狀" maxBarSize={6}>
            {data.map((entry, index) => (
              <Cell key={index} fill={entry.histogram >= 0 ? '#22c55e' : '#ef4444'} opacity={0.7} />
            ))}
          </Bar>
          <Line
            type="monotone"
            dataKey="macd"
            name="MACD"
            stroke="#3b82f6"
            strokeWidth={1.5}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="signal"
            name="Signal"
            stroke="#f97316"
            strokeWidth={1.5}
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
