import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import { PageLayout } from './components/layout/PageLayout';
import { FullPageSpinner } from './components/common/Spinner';

// Code-split pages
const DashboardPage = lazy(() =>
  import('./pages/DashboardPage').then((m) => ({ default: m.DashboardPage })),
);
const StockDetailPage = lazy(() =>
  import('./pages/StockDetailPage').then((m) => ({ default: m.StockDetailPage })),
);
const ScreenerPage = lazy(() =>
  import('./pages/ScreenerPage').then((m) => ({ default: m.ScreenerPage })),
);
const BacktestPage = lazy(() =>
  import('./pages/BacktestPage').then((m) => ({ default: m.BacktestPage })),
);
const WatchlistPage = lazy(() =>
  import('./pages/WatchlistPage').then((m) => ({ default: m.WatchlistPage })),
);
const AlertsPage = lazy(() =>
  import('./pages/AlertsPage').then((m) => ({ default: m.AlertsPage })),
);
const LoginPage = lazy(() =>
  import('./pages/LoginPage').then((m) => ({ default: m.LoginPage })),
);

export function App() {
  return (
    <PageLayout>
      <Suspense fallback={<FullPageSpinner />}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/stocks/:symbol" element={<StockDetailPage />} />
          <Route path="/screener" element={<ScreenerPage />} />
          <Route path="/backtest" element={<BacktestPage />} />
          <Route path="/watchlists" element={<WatchlistPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="*"
            element={
              <div className="flex flex-col items-center justify-center py-24 text-center">
                <h2 className="text-4xl font-bold text-gray-300 mb-3">404</h2>
                <p className="text-gray-500">找不到頁面。</p>
              </div>
            }
          />
        </Routes>
      </Suspense>
    </PageLayout>
  );
}
