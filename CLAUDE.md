# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

股票分析系統，支援台股 (TWSE) 與美股 (US) 的即時報價、歷史數據、技術指標分析與視覺化圖表。

## Tech Stack

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.x (async), Alembic, Celery
- **Frontend**: React 18, TypeScript 5, TailwindCSS 3, Recharts, React Router, Vite
- **Database**: PostgreSQL 16 (async via asyncpg), Redis 7 (cache + Celery broker)
- **Data Sources**: yfinance (US stocks), FinMind API (TWSE)

## Build / Run / Test Commands

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000     # dev server
pytest                                         # all tests
pytest tests/test_technical_analysis.py        # single test file
pytest -k "test_sma"                           # single test by name
pytest --cov=app                               # with coverage

black app tests                                # format
ruff check app tests --fix                     # lint + autofix
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # dev server (port 5173)
npm test             # vitest
npm run lint         # eslint
npm run format       # prettier
npm run build        # production build
```

### Full Stack (Docker)

```bash
docker compose up -d          # start all (db, redis, backend, frontend, worker, beat)
docker compose down           # stop all
```

### Database Migrations

```bash
cd backend
alembic upgrade head          # apply migrations
alembic revision --autogenerate -m "description"  # generate migration
```

## Architecture

### Backend Request Flow

```
HTTP Request → FastAPI Router (app/api/routes/) → Service Layer (app/services/) → Data Source / DB
```

- **Routes** (`app/api/routes/`): Thin handlers that validate input, call services via DI, return envelope responses.
- **Services** (`app/services/`): All business logic. Key services:
  - `StockDataFetcher` — unified fetcher that auto-detects US vs TW stocks (by symbol format) and dispatches to yfinance or FinMind accordingly. US calls run in thread pool via `asyncio.to_thread`.
  - `TechnicalAnalyzer` — computes SMA, RSI, MACD, Bollinger Bands etc.
  - `StockScreener` — filters stocks by technical conditions.
  - `Backtester` — runs strategy backtests with equity curve and trade log output.
  - `ValuationAnalyzer` — PE, PB, PS ratios and dividend yield.
  - `AlertEvaluator` — checks price/indicator alerts against current data.
- **Dependencies** (`app/api/deps.py`): Singleton service instances created at module load. Provides `get_fetcher()`, `get_analyzer()`, etc. via `Depends()`. Also handles JWT auth via `get_current_user()` / `get_current_active_user()`.
- **DB Session** (`app/db/session.py`): Async SQLAlchemy with `async_sessionmaker`. Use `get_db()` as a FastAPI dependency.

### Background Tasks (Celery)

- Broker + backend: Redis
- Worker tasks in `app/tasks/` — `data_tasks.py` (daily price fetch, cache cleanup) and `alert_tasks.py` (periodic alert checks)
- Beat schedule: daily price fetch at 18:00 Taipei time, cache cleanup every 6h, alert checks every 15m
- Celery tasks wrap async code via `asyncio.get_event_loop().run_until_complete()`

### Frontend Architecture

- React Router with code-split pages via `lazy()` imports
- Pages: Dashboard, StockDetail, Screener, Backtest, Watchlist, Alerts, Login
- API client (`src/services/api.ts`): Axios instance at `/api/v1` with JWT interceptor. Handles snake_case ↔ camelCase conversion inline.
- Auth: JWT stored in `localStorage`, attached via Axios request interceptor
- Charts: Recharts (`PriceChart`, `IndicatorChart`, `EquityCurveChart`)

### TW Stock Detection

Symbols are auto-classified as Taiwan stocks when they end with `.TW`/`.TWO` or consist entirely of digits (e.g., `"2330"`). This logic lives in `StockDataFetcher._is_tw_stock()`.

## Code Style

### Python

- **black** (line-length 88), **ruff** (rules: E, F, W, I, UP, B, SIM)
- Type hints on all public functions. Async preferred for I/O.
- `snake_case` for functions/variables, `PascalCase` for classes

### TypeScript

- **ESLint** (typescript-eslint), **Prettier** (printWidth 100, singleQuote, trailingComma all)
- `camelCase` for functions/variables, `PascalCase` for components/types
- Named exports preferred. Functional components with hooks.

## API Conventions

- All routes under `/api/v1/`
- Response envelope: `{ "data": ..., "meta": { "total", "page", "limit" } }`
- Error format: `{ "detail": "message", "code": "ERROR_CODE" }`
- Query params for filtering/pagination: `?period=1y&interval=1d&page=1&limit=50`
- API docs at `/api/docs`, OpenAPI spec at `/api/openapi.json`
- Health check: `GET /api/health`

## Git Conventions

Conventional Commits: `<type>(<scope>): <description>`

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`
Scopes: `backend`, `frontend`, `db`, `docker`, `deps`

## Testing

### Backend (pytest)

- Async tests with `pytest-asyncio`
- API tests use `httpx.AsyncClient` with `ASGITransport` (no real server needed)
- Shared fixtures in `tests/conftest.py` (`client`, `sample_stock_data`, `sample_price_history`, etc.)
- Contract tests in `tests/contract/` verify response envelope shape
- Integration tests in `tests/integration/` test full route → service flow

### Frontend (vitest)

- Test files colocated: `*.test.ts` / `*.test.tsx`
- `@testing-library/react` for components, `msw` for API mocking
