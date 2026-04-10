# Task Board — Phase 2 Implementation

## Legend
- **Status**: TODO | IN_PROGRESS | IN_REVIEW | DONE | BLOCKED
- **Owner**: DE=Data Engineer, QA=QA Engineer, QN=Quant Analyst, BE=Backend API, FE=Frontend

---

## Wave 1: Data Engineer + QA Engineer

| ID | Task | Owner | Status | Blocked By | Notes |
|----|------|-------|--------|------------|-------|
| DE-01 | Complete SQLAlchemy models (DailyPrice, TechnicalIndicator, BacktestResult, Alert, Portfolio) | DE | TODO | — | Extend existing Stock/Watchlist models |
| DE-02 | Alembic migration setup + initial migration | DE | TODO | DE-01 | Generate from models |
| DE-03 | data_fetcher.py — FinMind (TW) + yfinance (US) integration | DE | TODO | DE-01 | Must handle 2330.TW and AAPL |
| DE-04 | data_processor.py — cleaning, normalization, TW/US unified schema | DE | TODO | DE-03 | 除權息調整, 漲跌停 ±10% |
| DE-05 | cache.py — Redis caching layer | DE | TODO | — | Cache stock data, configurable TTL |
| DE-06 | data_tasks.py — Celery scheduled jobs (daily fetch, cleanup) | DE | TODO | DE-03, DE-05 | celery beat schedule |
| DE-07 | Unit tests: test_data_fetcher.py, test_data_processor.py, test_cache.py | DE | TODO | DE-03~06 | Coverage > 80% |
| DE-QG | **Quality Gate**: fetch & store 1 week TSMC (2330.TW) data | DE | TODO | DE-07 | Smoke test |
| QA-01 | Test framework setup (pytest fixtures, Playwright config, test utils) | QA | TODO | — | conftest.py enhancement |
| QA-02 | API contract tests skeleton (based on CLAUDE.md API conventions) | QA | TODO | — | Validate response envelope format |
| QA-03 | E2E test scaffolding (Playwright project setup) | QA | TODO | — | Page object pattern |
| QA-04 | Acceptance criteria → test mapping document | QA | TODO | — | Track coverage of P0 criteria |

## Wave 2: Quant Analyst (after DE-01 done)

| ID | Task | Owner | Status | Blocked By | Notes |
|----|------|-------|--------|------------|-------|
| QN-01 | technical_analysis.py — SMA, EMA, RSI, MACD, Bollinger Bands, KD | QN | TODO | DE-01 | Can start with mock data |
| QN-02 | screener.py — multi-condition stock screener | QN | TODO | QN-01 | Filter by indicators + fundamentals |
| QN-03 | backtester.py — strategy backtesting engine | QN | TODO | QN-01 | Buy-and-hold as baseline |
| QN-04 | valuation.py — PE, PB, dividend yield, DCF lite | QN | TODO | DE-01 | Fundamental valuation |
| QN-05 | Unit tests: test_analysis_*.py | QN | TODO | QN-01~04 | RSI(14) verification |
| QN-QG | **Quality Gate**: RSI(14) matches known values, buy-and-hold SPY benchmark | QN | TODO | QN-05 | Accuracy verification |

## Wave 3: Backend API Developer (after DE-01 + QN-01 partial)

| ID | Task | Owner | Status | Blocked By | Notes |
|----|------|-------|--------|------------|-------|
| BE-01 | deps.py — dependency injection (DB session, cache, services) | BE | TODO | DE-01 | |
| BE-02 | Implement stocks routes (list, detail, history, indicators) | BE | TODO | DE-03, QN-01 | Replace current stubs |
| BE-03 | Implement watchlist routes (CRUD with DB) | BE | TODO | DE-01 | Replace current stubs |
| BE-04 | Screener endpoint: POST /api/v1/screener | BE | TODO | QN-02 | |
| BE-05 | Backtest endpoint: POST /api/v1/backtest | BE | TODO | QN-03 | |
| BE-06 | Portfolio endpoints | BE | TODO | DE-01 | |
| BE-07 | Integration tests: test_api_*.py | BE | TODO | BE-02~06 | httpx AsyncClient |
| BE-QG | **Quality Gate**: all endpoints match CLAUDE.md response schema | BE | TODO | BE-07 | |

## Wave 4: Frontend Developer (after 3+ API endpoints working)

| ID | Task | Owner | Status | Blocked By | Notes |
|----|------|-------|--------|------------|-------|
| FE-01 | Layout components (Navbar, Sidebar, SearchBar) | FE | TODO | — | Can start immediately with mock |
| FE-02 | Stock detail page + candlestick chart (Recharts) | FE | TODO | FE-01 | |
| FE-03 | Screener page with filter UI | FE | TODO | FE-01 | |
| FE-04 | Backtest page with results visualization | FE | TODO | FE-01 | |
| FE-05 | Watchlist page (CRUD) | FE | TODO | FE-01 | |
| FE-06 | Portfolio dashboard page | FE | TODO | FE-01 | |
| FE-07 | API client update + data fetching hooks | FE | TODO | BE-02 | Switch from mock to real API |
| FE-QG | **Quality Gate**: all pages render without errors, charts work with mock data | FE | TODO | FE-07 | |

## Integration Phase (after all waves complete)

| ID | Task | Owner | Status | Blocked By | Notes |
|----|------|-------|--------|------------|-------|
| INT-01 | Full integration test suite | BE+QA | TODO | BE-QG, QN-QG | |
| INT-02 | Frontend → real API switchover | FE | TODO | BE-QG | |
| INT-03 | Full E2E test suite | QA | TODO | INT-02 | |
| INT-04 | Test reports + coverage report | QA | TODO | INT-03 | |
| INT-05 | Phase 2 handoff document | Manager | TODO | INT-04 | |
