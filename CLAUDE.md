# Stock Analyzer

## Project Overview

股票分析系統，支援台股 (TWSE) 與美股 (US) 的即時報價、歷史數據、技術指標分析與視覺化圖表。

## Architecture

```
stock-analyzer/
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── api/routes/      # API route handlers
│   │   ├── core/            # Config, security, dependencies
│   │   ├── db/              # Database session, migrations
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic layer
│   │   └── utils/           # Shared utilities
│   ├── tests/               # pytest tests
│   └── requirements.txt
├── frontend/                # React + TypeScript frontend
│   ├── src/
│   │   ├── components/      # React components (charts/, common/, layout/)
│   │   ├── hooks/           # Custom React hooks
│   │   ├── pages/           # Page-level components
│   │   ├── services/        # API client layer
│   │   ├── types/           # TypeScript type definitions
│   │   └── utils/           # Frontend utilities
│   └── package.json
└── docker-compose.yml
```

## Tech Stack

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.x, Alembic
- **Frontend**: React 18, TypeScript 5, TailwindCSS 3, Recharts
- **Database**: PostgreSQL 16 (primary), Redis 7 (cache)
- **Data Sources**: yfinance (US stocks), FinMind (TWSE)

## Build / Run / Test Commands

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run dev server
uvicorn app.main:app --reload --port 8000

# Run tests
pytest
pytest --cov=app          # with coverage

# Lint & format
black app tests
ruff check app tests
ruff check app tests --fix
```

### Frontend

```bash
cd frontend
npm install

# Run dev server
npm run dev

# Run tests
npm test

# Lint & format
npm run lint
npm run format

# Build
npm run build
```

### Full Stack (Docker)

```bash
docker compose up -d          # start all services
docker compose down           # stop all services
```

## Code Style

### Python (backend)

- Formatter: **black** (line-length 88)
- Linter: **ruff** (rules: E, F, W, I, UP, B, SIM)
- Type hints required on all public functions
- Async preferred for I/O-bound operations
- Use `snake_case` for functions, variables; `PascalCase` for classes

### TypeScript (frontend)

- Linter: **ESLint** (with typescript-eslint)
- Formatter: **Prettier** (printWidth 100, singleQuote, trailingComma all)
- Use `camelCase` for functions, variables; `PascalCase` for components and types
- Prefer named exports over default exports
- Use functional components with hooks

## API Conventions

RESTful naming with consistent patterns:

```
GET    /api/v1/stocks                  # List stocks
GET    /api/v1/stocks/{symbol}         # Get stock detail
GET    /api/v1/stocks/{symbol}/history # Get price history
GET    /api/v1/stocks/{symbol}/indicators # Get technical indicators
POST   /api/v1/watchlists              # Create watchlist
GET    /api/v1/watchlists/{id}         # Get watchlist
PUT    /api/v1/watchlists/{id}         # Update watchlist
DELETE /api/v1/watchlists/{id}         # Delete watchlist
```

- Use plural nouns for resources
- Nest sub-resources under parent (e.g., `/stocks/{symbol}/history`)
- Use query params for filtering/pagination: `?period=1y&interval=1d&page=1&limit=50`
- Response envelope: `{ "data": ..., "meta": { "total", "page", "limit" } }`
- Error format: `{ "detail": "message", "code": "ERROR_CODE" }`

## Git Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`

Scopes: `backend`, `frontend`, `db`, `docker`, `deps`

Examples:
```
feat(backend): add stock price history endpoint
fix(frontend): resolve chart rendering on empty data
chore(deps): upgrade fastapi to 0.111
```

## Testing

### Backend (pytest)

- Test files: `tests/test_*.py`
- Use `pytest-asyncio` for async tests
- Use `httpx.AsyncClient` for API integration tests
- Fixtures in `tests/conftest.py`
- Aim for ≥80% coverage on services layer

### Frontend (vitest)

- Test files: `*.test.ts` / `*.test.tsx` colocated with source
- Use `@testing-library/react` for component tests
- Mock API calls with `msw` (Mock Service Worker)
