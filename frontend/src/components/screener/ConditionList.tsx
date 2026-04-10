import type { ScreenerCondition } from '../../types/stock';
import { ConditionBuilder } from './ConditionBuilder';

interface ConditionListProps {
  conditions: ScreenerCondition[];
  onChange: (conditions: ScreenerCondition[]) => void;
}

const DEFAULT_CONDITION: ScreenerCondition = {
  indicator: 'rsi',
  operator: 'lt',
  value: 30,
};

export function ConditionList({ conditions, onChange }: ConditionListProps) {
  function handleChange(index: number, updated: ScreenerCondition) {
    const next = [...conditions];
    next[index] = updated;
    onChange(next);
  }

  function handleRemove(index: number) {
    onChange(conditions.filter((_, i) => i !== index));
  }

  function handleAdd() {
    onChange([...conditions, { ...DEFAULT_CONDITION }]);
  }

  return (
    <div className="space-y-3">
      {conditions.length === 0 && (
        <p className="text-sm text-gray-400 italic">No conditions added. Click "Add Condition" to start.</p>
      )}
      {conditions.map((c, i) => (
        <ConditionBuilder
          key={i}
          condition={c}
          index={i}
          onChange={handleChange}
          onRemove={handleRemove}
        />
      ))}
      <button
        onClick={handleAdd}
        className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-blue-500 px-3 py-1.5 text-sm font-medium text-blue-600 hover:bg-blue-50 transition-colors"
      >
        + Add Condition
      </button>
    </div>
  );
}
