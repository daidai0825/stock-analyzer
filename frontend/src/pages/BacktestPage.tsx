import { useState } from 'react';
import { BacktestForm } from '../components/backtest/BacktestForm';
import { BacktestResults } from '../components/backtest/BacktestResults';
import { ErrorMessage } from '../components/common/ErrorMessage';
import type { BacktestConfig, BacktestResult } from '../types/stock';
import { runBacktest } from '../services/api';

export function BacktestPage() {
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [lastConfig, setLastConfig] = useState<BacktestConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(config: BacktestConfig) {
    setIsLoading(true);
    setError(null);
    setLastConfig(config);
    try {
      const r = await runBacktest(config);
      setResult(r);
    } catch {
      setError('回測失敗，請檢查設定後重試。');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">回測系統</h1>
        <p className="text-sm text-gray-500 mt-1">
          以歷史數據模擬交易策略
        </p>
      </div>

      {/* Config form */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">設定</h2>
        <BacktestForm onSubmit={(cfg) => void handleSubmit(cfg)} isLoading={isLoading} />
      </div>

      {/* Error */}
      {error && (
        <ErrorMessage
          message={error}
          onRetry={lastConfig ? () => void handleSubmit(lastConfig) : undefined}
        />
      )}

      {/* Results */}
      {result != null && lastConfig != null && !error && (
        <div>
          <h2 className="text-lg font-bold text-gray-900 mb-4">
            結果 — {lastConfig.symbol}
          </h2>
          <BacktestResults result={result} config={lastConfig} />
        </div>
      )}
    </div>
  );
}
