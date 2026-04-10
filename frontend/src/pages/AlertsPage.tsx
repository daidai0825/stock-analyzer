import { useEffect, useState } from 'react';
import {
  checkAlertNow,
  createAlert,
  deleteAlert,
  fetchAlerts,
  updateAlert,
} from '../services/api';
import type { Alert, AlertType } from '../types/stock';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ALERT_TYPES: { value: AlertType; label: string }[] = [
  { value: 'price_above', label: '股價高於' },
  { value: 'price_below', label: '股價低於' },
  { value: 'rsi_above', label: 'RSI 高於' },
  { value: 'rsi_below', label: 'RSI 低於' },
  { value: 'sma_cross', label: '均線交叉（黃金交叉）' },
  { value: 'volume_above', label: '成交量高於' },
];

/** Human-readable description of the primary condition key per alert type. */
function conditionLabel(alertType: AlertType): string {
  switch (alertType) {
    case 'price_above':
    case 'price_below':
      return '目標價格';
    case 'rsi_above':
    case 'rsi_below':
      return 'RSI 門檻';
    case 'volume_above':
      return '成交量門檻';
    case 'sma_cross':
      return '快/慢均線週期';
  }
}

/** Primary numeric value shown in the card summary. */
function conditionSummary(alert: Alert): string {
  const c = alert.condition;
  switch (alert.alert_type) {
    case 'price_above':
    case 'price_below':
      return `$${c['target_price'] ?? '—'}`;
    case 'rsi_above':
    case 'rsi_below':
      return `RSI ${c['threshold'] ?? '—'} (period ${c['period'] ?? 14})`;
    case 'volume_above':
      return `Vol > ${(c['threshold'] ?? 0).toLocaleString()}`;
    case 'sma_cross':
      return `SMA(${c['fast_period'] ?? 20}) / SMA(${c['slow_period'] ?? 50})`;
    default:
      return JSON.stringify(c);
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface AlertCardProps {
  alert: Alert;
  onToggle: (id: number, active: boolean) => void;
  onDelete: (id: number) => void;
  onCheck: (id: number) => void;
  checkResult?: { triggered: boolean; current_value: number } | null;
  isChecking?: boolean;
}

function AlertCard({ alert, onToggle, onDelete, onCheck, checkResult, isChecking }: AlertCardProps) {
  return (
    <div
      className={`rounded-xl border bg-white p-4 shadow-sm transition-all ${
        alert.triggered_at
          ? 'border-yellow-400 bg-yellow-50'
          : alert.is_active
            ? 'border-green-300'
            : 'border-gray-200 opacity-60'
      }`}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="font-bold text-gray-900 text-sm">{alert.symbol}</span>
          <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
            {alert.alert_type.replace(/_/g, ' ')}
          </span>
          {alert.triggered_at && (
            <span className="ml-2 rounded-full bg-yellow-200 px-2 py-0.5 text-xs font-medium text-yellow-800">
              已觸發
            </span>
          )}
        </div>

        {/* Status toggle */}
        <button
          onClick={() => onToggle(alert.id, !alert.is_active)}
          className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold transition-colors ${
            alert.is_active
              ? 'bg-green-100 text-green-700 hover:bg-green-200'
              : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
          }`}
          title={alert.is_active ? '點擊停用' : '點擊啟用'}
        >
          {alert.is_active ? '啟用中' : '已停用'}
        </button>
      </div>

      {/* Condition summary */}
      <p className="mt-1.5 text-sm text-gray-600">{conditionSummary(alert)}</p>

      {/* Triggered info */}
      {alert.triggered_at && (
        <p className="mt-1 text-xs text-yellow-700">
          觸發時間：{new Date(alert.triggered_at).toLocaleString()}
        </p>
      )}

      {/* Check result banner */}
      {checkResult !== null && checkResult !== undefined && (
        <div
          className={`mt-2 rounded-md px-3 py-1.5 text-xs font-medium ${
            checkResult.triggered
              ? 'bg-green-100 text-green-800'
              : 'bg-gray-100 text-gray-600'
          }`}
        >
          {checkResult.triggered ? '目前會觸發' : '目前未觸發'} — 當前數值：{checkResult.current_value.toFixed(4)}
        </div>
      )}

      {/* Action buttons */}
      <div className="mt-3 flex items-center gap-2">
        <button
          onClick={() => onCheck(alert.id)}
          disabled={isChecking}
          className="rounded-md bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-100 disabled:opacity-40 transition-colors"
        >
          {isChecking ? '檢查中…' : '立即檢查'}
        </button>
        <button
          onClick={() => onDelete(alert.id)}
          className="rounded-md bg-red-50 px-3 py-1 text-xs font-semibold text-red-600 hover:bg-red-100 transition-colors"
        >
          刪除
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Create Alert form
// ---------------------------------------------------------------------------

interface CreateAlertFormProps {
  onCreated: (alert: Alert) => void;
  onCancel: () => void;
}

function CreateAlertForm({ onCreated, onCancel }: CreateAlertFormProps) {
  const [symbol, setSymbol] = useState('');
  const [alertType, setAlertType] = useState<AlertType>('price_above');
  const [primaryValue, setPrimaryValue] = useState('');
  const [periodValue, setPeriodValue] = useState('14');
  const [fastPeriod, setFastPeriod] = useState('20');
  const [slowPeriod, setSlowPeriod] = useState('50');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function buildCondition(): Record<string, number> {
    switch (alertType) {
      case 'price_above':
      case 'price_below':
        return { target_price: parseFloat(primaryValue) };
      case 'rsi_above':
      case 'rsi_below':
        return { threshold: parseFloat(primaryValue), period: parseInt(periodValue, 10) };
      case 'volume_above':
        return { threshold: parseFloat(primaryValue) };
      case 'sma_cross':
        return { fast_period: parseInt(fastPeriod, 10), slow_period: parseInt(slowPeriod, 10) };
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!symbol.trim()) {
      setError('請輸入股票代號。');
      return;
    }
    setSubmitting(true);
    try {
      const alert = await createAlert({
        symbol: symbol.trim().toUpperCase(),
        alert_type: alertType,
        condition: buildCondition(),
      });
      onCreated(alert);
    } catch {
      setError('建立警報失敗，請檢查輸入內容。');
    } finally {
      setSubmitting(false);
    }
  }

  const showSmaFields = alertType === 'sma_cross';
  const showPeriodField = alertType === 'rsi_above' || alertType === 'rsi_below';
  const showPrimaryValue = alertType !== 'sma_cross';

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-blue-200 bg-blue-50 p-5 space-y-4"
    >
      <h3 className="font-semibold text-gray-800 text-sm">新增警報</h3>

      {error && (
        <p className="rounded-md bg-red-100 px-3 py-2 text-xs text-red-700">{error}</p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Symbol */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">股票代號</label>
          <input
            type="text"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="例如 AAPL 或 2330"
            className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>

        {/* Alert type */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">警報類型</label>
          <select
            value={alertType}
            onChange={(e) => setAlertType(e.target.value as AlertType)}
            className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {ALERT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>

        {/* Primary value (price / rsi / volume threshold) */}
        {showPrimaryValue && (
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              {conditionLabel(alertType)}
            </label>
            <input
              type="number"
              step="any"
              value={primaryValue}
              onChange={(e) => setPrimaryValue(e.target.value)}
              placeholder="輸入數值"
              className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
        )}

        {/* RSI period */}
        {showPeriodField && (
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">RSI 週期</label>
            <input
              type="number"
              min={2}
              max={100}
              value={periodValue}
              onChange={(e) => setPeriodValue(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        )}

        {/* SMA periods */}
        {showSmaFields && (
          <>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                快均線週期
              </label>
              <input
                type="number"
                min={2}
                value={fastPeriod}
                onChange={(e) => setFastPeriod(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                慢均線週期
              </label>
              <input
                type="number"
                min={2}
                value={slowPeriod}
                onChange={(e) => setSlowPeriod(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </>
        )}
      </div>

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-40 transition-colors"
        >
          {submitting ? '建立中…' : '建立警報'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          取消
        </button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [filterActive, setFilterActive] = useState<boolean | undefined>(undefined);
  const [checkResults, setCheckResults] = useState<
    Record<number, { triggered: boolean; current_value: number } | null>
  >({});
  const [checkingIds, setCheckingIds] = useState<Set<number>>(new Set());

  async function loadAlerts() {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await fetchAlerts({ is_active: filterActive });
      setAlerts(resp.data);
      setTotal(resp.meta?.total ?? resp.data.length);
    } catch {
      setError('無法載入警報。');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadAlerts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterActive]);

  async function handleToggle(id: number, active: boolean) {
    try {
      const updated = await updateAlert(id, { is_active: active });
      setAlerts((prev) => prev.map((a) => (a.id === id ? updated : a)));
    } catch {
      setError('更新警報失敗。');
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteAlert(id);
      setAlerts((prev) => prev.filter((a) => a.id !== id));
      setTotal((t) => t - 1);
    } catch {
      setError('刪除警報失敗。');
    }
  }

  async function handleCheck(id: number) {
    setCheckingIds((s) => new Set(s).add(id));
    try {
      const result = await checkAlertNow(id);
      setCheckResults((prev) => ({ ...prev, [id]: result }));
    } catch {
      setCheckResults((prev) => ({ ...prev, [id]: null }));
    } finally {
      setCheckingIds((s) => {
        const next = new Set(s);
        next.delete(id);
        return next;
      });
    }
  }

  function handleCreated(alert: Alert) {
    setAlerts((prev) => [alert, ...prev]);
    setTotal((t) => t + 1);
    setShowCreate(false);
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">警報</h1>
          <p className="text-sm text-gray-500 mt-1">
            {total} 個警報 — 每 15 分鐘檢查一次
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
        >
          + 新增警報
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <CreateAlertForm
          onCreated={handleCreated}
          onCancel={() => setShowCreate(false)}
        />
      )}

      {/* Filter bar */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-gray-500">篩選：</span>
        {([undefined, true, false] as const).map((val) => (
          <button
            key={String(val)}
            onClick={() => setFilterActive(val)}
            className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
              filterActive === val
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {val === undefined ? '全部' : val ? '啟用中' : '已停用'}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-md bg-red-100 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20 text-gray-400 text-sm">
          載入警報中…
        </div>
      ) : alerts.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-400 text-sm">尚無警報，建立一個開始使用。</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {alerts.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              onToggle={handleToggle}
              onDelete={handleDelete}
              onCheck={handleCheck}
              checkResult={checkResults[alert.id]}
              isChecking={checkingIds.has(alert.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
