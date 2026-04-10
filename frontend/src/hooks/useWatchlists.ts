import { useCallback, useEffect, useState } from 'react';
import type { Watchlist } from '../types/stock';
import {
  fetchWatchlists,
  createWatchlist as apiCreateWatchlist,
  updateWatchlist as apiUpdateWatchlist,
  deleteWatchlist as apiDeleteWatchlist,
} from '../services/api';

/**
 * CRUD hook for watchlists backed by the real REST API.
 * Optimistic updates keep the UI responsive; errors roll back local state.
 */
export function useWatchlists() {
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // Load
  // ---------------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    fetchWatchlists()
      .then((data) => {
        if (!cancelled) setWatchlists(data);
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load watchlists');
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // ---------------------------------------------------------------------------
  // Create
  // ---------------------------------------------------------------------------
  const createWatchlist = useCallback(async (name: string, symbols: string[]) => {
    const created = await apiCreateWatchlist({ name, symbols });
    setWatchlists((prev) => [...prev, created]);
    return created;
  }, []);

  // ---------------------------------------------------------------------------
  // Delete
  // ---------------------------------------------------------------------------
  const deleteWatchlist = useCallback(async (id: number) => {
    // Optimistic remove
    setWatchlists((prev) => prev.filter((w) => w.id !== id));
    try {
      await apiDeleteWatchlist(id);
    } catch {
      // Rollback: re-fetch to restore consistent state
      fetchWatchlists()
        .then(setWatchlists)
        .catch(() => setError('Failed to delete watchlist'));
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Add symbol to a watchlist
  // ---------------------------------------------------------------------------
  const addSymbol = useCallback(async (watchlistId: number, symbol: string) => {
    const target = watchlists.find((w) => w.id === watchlistId);
    if (!target) return;

    const newSymbols = [
      ...new Set([...target.items.map((i) => i.symbol), symbol]),
    ];

    // Optimistic update
    setWatchlists((prev) =>
      prev.map((w) =>
        w.id === watchlistId
          ? {
              ...w,
              items: [
                ...w.items,
                // Temporary id until server responds
                { id: Date.now(), symbol },
              ],
            }
          : w,
      ),
    );

    try {
      const updated = await apiUpdateWatchlist(watchlistId, { symbols: newSymbols });
      setWatchlists((prev) => prev.map((w) => (w.id === watchlistId ? updated : w)));
    } catch {
      // Rollback
      fetchWatchlists()
        .then(setWatchlists)
        .catch(() => setError('Failed to add symbol'));
    }
  }, [watchlists]);

  // ---------------------------------------------------------------------------
  // Remove symbol from a watchlist (by item id)
  // ---------------------------------------------------------------------------
  const removeSymbol = useCallback(async (watchlistId: number, itemId: number) => {
    const target = watchlists.find((w) => w.id === watchlistId);
    if (!target) return;

    const remainingSymbols = target.items
      .filter((i) => i.id !== itemId)
      .map((i) => i.symbol);

    // Optimistic update
    setWatchlists((prev) =>
      prev.map((w) =>
        w.id === watchlistId
          ? { ...w, items: w.items.filter((i) => i.id !== itemId) }
          : w,
      ),
    );

    try {
      const updated = await apiUpdateWatchlist(watchlistId, { symbols: remainingSymbols });
      setWatchlists((prev) => prev.map((w) => (w.id === watchlistId ? updated : w)));
    } catch {
      // Rollback
      fetchWatchlists()
        .then(setWatchlists)
        .catch(() => setError('Failed to remove symbol'));
    }
  }, [watchlists]);

  // ---------------------------------------------------------------------------
  // Rename a watchlist
  // ---------------------------------------------------------------------------
  const renameWatchlist = useCallback(async (id: number, name: string) => {
    // Optimistic update
    setWatchlists((prev) => prev.map((w) => (w.id === id ? { ...w, name } : w)));

    try {
      const updated = await apiUpdateWatchlist(id, { name });
      setWatchlists((prev) => prev.map((w) => (w.id === id ? updated : w)));
    } catch {
      // Rollback
      fetchWatchlists()
        .then(setWatchlists)
        .catch(() => setError('Failed to rename watchlist'));
    }
  }, []);

  return {
    watchlists,
    isLoading,
    error,
    createWatchlist,
    deleteWatchlist,
    addSymbol,
    removeSymbol,
    renameWatchlist,
  };
}
