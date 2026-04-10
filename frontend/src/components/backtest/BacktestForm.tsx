import { useState } from 'react';
import { format, subYears } from 'date-fns';
import type { BacktestConfig } from '../../types/stock';

const STRATEGIES = [
  { value: 'buy_and_hold', label: '買入持有' },
  { value: 'sma_crossover', label: '均線交叉' },
  { value: 'rsi_oversold', label: 'RSI 超賣' },
];

const STRATEGY_PARAMS: Record<string, { key: string; label: string; default: number }[]> = {
  sma_crossover: [
    { key: 'fast_period', label: '快均線週期', default: 20 },
    { key: 'slow_period', label: '慢均線週期', default: 50 },
  ],
  rsi_oversold: [
    { key: 'rsi_period', label: 'RSI 週期', default: 14 },
    { key: 'oversold_level', label: '超賣水位', default: 30 },
    { key: 'overbought_level', label: '超買水位', default: 70 },
  ],
};

interface BacktestFormProps {
  onSubmit: (config: BacktestConfig) => void;
  isLoading: boolean;
}

export function BacktestForm({ onSubmit, isLoading }: BacktestFormProps) {
  const [symbol, setSymbol] = useState('AAPL');
  const [strategy, setStrategy] = useState('buy_and_hold');
  const [startDate, setStartDate] = useState(format(subYears(new Date(), 2), 'yyyy-MM-dd'));
  const [endDate, setEndDate] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [initialCapital, setInitialCapital] = useState(100000);
  const [commission, setCommission] = useState(0.001425);
  const [tax, setTax] = useState(0.003);
  const [params, setParams] = useState<Record<string, number>>({});

  const strategyParamDefs = STRATEGY_PARAMS[strategy] ?? [];

  function handleParamChange(key: string, value: number) {
    setParams((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const resolvedParams: Record<string, number> = {};
    for (const def of strategyParamDefs) {
      resolvedParams[def.key] = params[def.key] ?? def.default;
    }
    onSubmit({
      symbol: symbol.toUpperCase().trim(),
      strategy,
      startDate,
      endDate,
      initialCapital,
      commission,
      tax,
      params: Object.keys(resolvedParams).length > 0 ? resolvedParams : undefined,
    });
  }

  const labelClass = 'block text-sm font-medium text-gray-700 mb-1';
  const inputClass =
    'w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500';

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Symbol */}
        <div>
          <label className={labelClass}>股票代號</label>
          <input
            type="text"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="例如 AAPL、2330"
            required
            className={inputClass}
          />
        </div>

        {/* Strategy */}
        <div>
          <label className={labelClass}>策略</label>
          <select
            value={strategy}
            onChange={(e) => { setStrategy(e.target.value); setParams({}); }}
            className={inputClass}
          >
            {STRATEGIES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        {/* Start date */}
        <div>
          <label className={labelClass}>開始日期</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            required
            className={inputClass}
          />
        </div>

        {/* End date */}
        <div>
          <label className={labelClass}>結束日期</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            required
            className={inputClass}
          />
        </div>

        {/* Initial capital */}
        <div>
          <label className={labelClass}>初始資金 ($)</label>
          <input
            type="number"
            value={initialCapital}
            onChange={(e) => setInitialCapital(Number(e.target.value))}
            min={1000}
            step={1000}
            required
            className={inputClass}
          />
        </div>

        {/* Commission */}
        <div>
          <label className={labelClass}>
            手續費率
            <span className="ml-1 text-xs text-gray-400">（台股 0.1425%）</span>
          </label>
          <input
            type="number"
            value={commission}
            onChange={(e) => setCommission(Number(e.target.value))}
            min={0}
            max={0.05}
            step={0.0001}
            className={inputClass}
          />
        </div>

        {/* Tax */}
        <div>
          <label className={labelClass}>
            稅率（賣出）
            <span className="ml-1 text-xs text-gray-400">（台股 0.3%）</span>
          </label>
          <input
            type="number"
            value={tax}
            onChange={(e) => setTax(Number(e.target.value))}
            min={0}
            max={0.05}
            step={0.001}
            className={inputClass}
          />
        </div>
      </div>

      {/* Strategy-specific params */}
      {strategyParamDefs.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-3">策略參數</h4>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {strategyParamDefs.map((def) => (
              <div key={def.key}>
                <label className={labelClass}>{def.label}</label>
                <input
                  type="number"
                  value={params[def.key] ?? def.default}
                  onChange={(e) => handleParamChange(def.key, Number(e.target.value))}
                  min={1}
                  className={inputClass}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      <button
        type="submit"
        disabled={isLoading}
        className="w-full rounded-md bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60 transition-colors"
      >
        {isLoading ? '回測執行中...' : '執行回測'}
      </button>
    </form>
  );
}
