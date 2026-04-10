import type { ScreenerCondition } from '../../types/stock';

export const INDICATOR_OPTIONS = [
  { value: 'price', label: '股價' },
  { value: 'volume', label: '成交量' },
  { value: 'rsi', label: 'RSI (14)' },
  { value: 'sma_20', label: 'SMA 20' },
  { value: 'sma_50', label: 'SMA 50' },
  { value: 'sma_200', label: 'SMA 200' },
  { value: 'pe_ratio', label: '本益比' },
  { value: 'pb_ratio', label: '股價淨值比' },
  { value: 'market_cap', label: '市值' },
  { value: 'dividend_yield', label: '股息殖利率 (%)' },
  { value: 'change_percent', label: '漲跌幅 (%)' },
];

export const OPERATOR_OPTIONS: { value: ScreenerCondition['operator']; label: string }[] = [
  { value: 'gt', label: '>' },
  { value: 'gte', label: '>=' },
  { value: 'lt', label: '<' },
  { value: 'lte', label: '<=' },
  { value: 'eq', label: '=' },
];

interface ConditionBuilderProps {
  condition: ScreenerCondition;
  index: number;
  onChange: (index: number, condition: ScreenerCondition) => void;
  onRemove: (index: number) => void;
}

export function ConditionBuilder({ condition, index, onChange, onRemove }: ConditionBuilderProps) {
  function update(partial: Partial<ScreenerCondition>) {
    onChange(index, { ...condition, ...partial });
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {/* Index badge */}
      <span className="text-xs font-bold text-gray-400 w-5 text-right shrink-0">{index + 1}.</span>

      {/* Indicator select */}
      <select
        value={condition.indicator}
        onChange={(e) => update({ indicator: e.target.value })}
        className="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
      >
        {INDICATOR_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      {/* Operator select */}
      <select
        value={condition.operator}
        onChange={(e) => update({ operator: e.target.value as ScreenerCondition['operator'] })}
        className="rounded-md border border-gray-300 px-2 py-1.5 text-sm w-16 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
      >
        {OPERATOR_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      {/* Value input */}
      <input
        type="number"
        value={String(condition.value)}
        onChange={(e) => update({ value: e.target.value === '' ? '' : Number(e.target.value) })}
        placeholder="數值"
        className="rounded-md border border-gray-300 px-2 py-1.5 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />

      {/* Remove */}
      <button
        onClick={() => onRemove(index)}
        className="rounded-md px-2 py-1.5 text-sm text-red-500 hover:bg-red-50 transition-colors"
        title="移除條件"
      >
        移除
      </button>
    </div>
  );
}
