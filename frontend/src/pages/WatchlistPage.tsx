import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useWatchlists } from '../hooks/useWatchlists';
import { FullPageSpinner } from '../components/common/Spinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import type { Watchlist } from '../types/stock';

interface WatchlistCardProps {
  watchlist: Watchlist;
  selected: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onRemoveSymbol: (itemId: number) => void;
  onAddSymbol: (symbol: string) => void;
  onRename: (name: string) => void;
}

function WatchlistCard({
  watchlist,
  selected,
  onSelect,
  onDelete,
  onRemoveSymbol,
  onAddSymbol,
  onRename,
}: WatchlistCardProps) {
  const [addInput, setAddInput] = useState('');
  const [renaming, setRenaming] = useState(false);
  const [renameInput, setRenameInput] = useState(watchlist.name);

  function handleAdd() {
    const s = addInput.trim().toUpperCase();
    if (s) {
      onAddSymbol(s);
      setAddInput('');
    }
  }

  function handleRename() {
    const n = renameInput.trim();
    if (n) onRename(n);
    setRenaming(false);
  }

  return (
    <div
      className={`rounded-xl border bg-white p-4 shadow-sm transition-all ${
        selected ? 'border-blue-400 ring-1 ring-blue-200' : 'border-gray-200 hover:border-gray-300'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        {renaming ? (
          <div className="flex items-center gap-2 flex-1 mr-2">
            <input
              autoFocus
              value={renameInput}
              onChange={(e) => setRenameInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleRename(); if (e.key === 'Escape') setRenaming(false); }}
              className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button onClick={handleRename} className="text-xs text-blue-600 font-semibold hover:underline">儲存</button>
          </div>
        ) : (
          <button
            onClick={onSelect}
            className="font-semibold text-gray-900 text-left flex-1 hover:text-blue-700 transition-colors"
          >
            {watchlist.name}
            <span className="ml-1.5 text-xs font-normal text-gray-400">({watchlist.items.length})</span>
          </button>
        )}
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => setRenaming((v) => !v)}
            className="rounded p-1 text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors text-xs"
            title="重新命名"
          >
            編輯
          </button>
          <button
            onClick={onDelete}
            className="rounded p-1 text-red-400 hover:text-red-600 hover:bg-red-50 transition-colors text-xs"
            title="刪除觀察列表"
          >
            刪除
          </button>
        </div>
      </div>

      {/* Items */}
      {selected && (
        <div className="space-y-1 mb-3">
          {watchlist.items.length === 0 ? (
            <p className="text-xs text-gray-400 py-2">尚無股票代號。</p>
          ) : (
            watchlist.items.map((item) => (
              <div key={item.id} className="flex items-center gap-2 py-1">
                <Link
                  to={`/stocks/${item.symbol}`}
                  className="text-sm font-semibold text-blue-600 hover:underline flex-1"
                >
                  {item.symbol}
                </Link>
                <button
                  onClick={() => onRemoveSymbol(item.id)}
                  className="text-xs text-red-400 hover:text-red-600 shrink-0"
                  title="移除"
                >
                  ✕
                </button>
              </div>
            ))
          )}
        </div>
      )}

      {/* Add symbol */}
      {selected && (
        <div className="flex items-center gap-2 mt-2">
          <input
            type="text"
            value={addInput}
            onChange={(e) => setAddInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleAdd(); }}
            placeholder="新增代號..."
            className="flex-1 rounded-md border border-gray-300 px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleAdd}
            disabled={!addInput.trim()}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-40 transition-colors"
          >
            新增
          </button>
        </div>
      )}

      {/* Preview when not selected */}
      {!selected && watchlist.items.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1">
          {watchlist.items.slice(0, 6).map((item) => (
            <span
              key={item.id}
              className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
            >
              {item.symbol}
            </span>
          ))}
          {watchlist.items.length > 6 && (
            <span className="text-xs text-gray-400">+{watchlist.items.length - 6} 更多</span>
          )}
        </div>
      )}
    </div>
  );
}

export function WatchlistPage() {
  const {
    watchlists,
    isLoading,
    error,
    createWatchlist,
    deleteWatchlist,
    addSymbol,
    removeSymbol,
    renameWatchlist,
  } = useWatchlists();

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [actionError, setActionError] = useState<string | null>(null);

  async function handleCreate() {
    const name = newName.trim();
    if (!name) return;
    setActionError(null);
    try {
      const wl = await createWatchlist(name, []);
      setSelectedId(wl.id);
      setNewName('');
      setShowCreate(false);
    } catch {
      setActionError('建立觀察列表失敗，請先登入。');
    }
  }

  if (isLoading) return <FullPageSpinner />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">觀察列表</h1>
          <p className="text-sm text-gray-500 mt-1">管理你追蹤的股票</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
        >
          + 新增觀察列表
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 flex items-center gap-3">
          <input
            autoFocus
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') void handleCreate(); if (e.key === 'Escape') setShowCreate(false); }}
            placeholder="觀察列表名稱..."
            className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={() => void handleCreate()}
            disabled={!newName.trim()}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-40 transition-colors"
          >
            建立
          </button>
          <button
            onClick={() => setShowCreate(false)}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            取消
          </button>
        </div>
      )}

      {/* Action error */}
      {actionError && (
        <div className="rounded-md bg-red-100 px-4 py-3 text-sm text-red-700">{actionError}</div>
      )}

      {/* List */}
      {watchlists.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-400 text-sm">尚無觀察列表，建立一個開始使用。</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {watchlists.map((wl) => (
            <WatchlistCard
              key={wl.id}
              watchlist={wl}
              selected={selectedId === wl.id}
              onSelect={() => setSelectedId((id) => (id === wl.id ? null : wl.id))}
              onDelete={() => {
                void deleteWatchlist(wl.id);
                if (selectedId === wl.id) setSelectedId(null);
              }}
              onAddSymbol={(s) => void addSymbol(wl.id, s)}
              onRemoveSymbol={(itemId) => void removeSymbol(wl.id, itemId)}
              onRename={(name) => void renameWatchlist(wl.id, name)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
