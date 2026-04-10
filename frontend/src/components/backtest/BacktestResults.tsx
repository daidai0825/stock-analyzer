import type { BacktestConfig, BacktestResult } from '../../types/stock';
import { EquityCurveChart } from './EquityCurveChart';
import { TradesTable } from './TradesTable';

interface MetricCardProps {
  label: string;
  value: string;
  positive?: boolean | null;
  neutral?: boolean;
}

function MetricCard({ label, value, positive, neutral }: MetricCardProps) {
  const valueColor =
    neutral || positive == null
      ? 'text-gray-900'
      : positive
      ? 'text-green-600'
      : 'text-red-600';
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wider text-gray-500">{label}</p>
      <p className={`mt-1 text-xl font-bold ${valueColor}`}>{value}</p>
    </div>
  );
}

interface BacktestResultsProps {
  result: BacktestResult;
  config: BacktestConfig;
}

export function BacktestResults({ result, config }: BacktestResultsProps) {
  const pct = (v: number) => `${(v * 100).toFixed(2)}%`;
  const sign = (v: number) => (v >= 0 ? '+' : '');

  return (
    <div className="space-y-6">
      {/* Summary metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricCard
          label="總報酬率"
          value={`${sign(result.totalReturn)}${pct(result.totalReturn)}`}
          positive={result.totalReturn >= 0}
        />
        <MetricCard
          label="年化報酬率"
          value={`${sign(result.annualizedReturn)}${pct(result.annualizedReturn)}`}
          positive={result.annualizedReturn >= 0}
        />
        <MetricCard
          label="最大回撤"
          value={`-${pct(result.maxDrawdown)}`}
          positive={false}
        />
        <MetricCard
          label="夏普比率"
          value={result.sharpeRatio.toFixed(2)}
          positive={result.sharpeRatio >= 1}
        />
        <MetricCard
          label="勝率"
          value={pct(result.winRate)}
          positive={result.winRate >= 0.5}
        />
        <MetricCard
          label="最終價值"
          value={`$${result.finalValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
          neutral
        />
      </div>

      {/* Equity curve */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">權益曲線</h3>
        <EquityCurveChart
          data={result.equityCurve}
          initialCapital={config.initialCapital}
        />
      </div>

      {/* Trades table */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          交易紀錄（{result.totalTrades} 筆）
        </h3>
        <TradesTable trades={result.trades} />
      </div>
    </div>
  );
}
