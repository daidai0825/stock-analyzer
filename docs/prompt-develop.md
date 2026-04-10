Phase 1 is approved. Proceed to Phase 2: Implementation.

You are still the PROJECT MANAGER. Continue using your management
framework (task board, status log, quality gates, decisions log).

## Pre-Implementation Checklist
Before spawning any teammate, do these yourself:
1. Read docs/architecture/implementation-plan.md
2. Create a detailed task breakdown in docs/management/task-board.md
   based on the implementation plan
3. Identify the critical path (which tasks block everything else)
4. Plan the spawn order (not all teammates need to start at once)

## Team Structure (5 teammates):

### Teammate: Data Engineer name: Charlie
Read first: F001 spec, data-model.md, infrastructure.md
Use skill: tw-stock-analyzer
Tasks assigned by you from task-board.md, expected deliverables:
- backend/app/models/ — all SQLAlchemy models matching data-model.md
- backend/app/services/data_fetcher.py — FinMind + yfinance
- backend/app/services/data_processor.py — cleaning, normalization
- backend/app/core/cache.py — Redis caching layer
- backend/app/tasks/data_tasks.py — Celery scheduled jobs
- tests/unit/test_data_*.py — coverage > 80%
  Quality gate: models match ERD exactly, tests pass,
  can fetch and store 1 week of TSMC (2330.TW) data

### Teammate: Quant Analyst name: Dana
Read first: F002, F003, F004, F008 specs, tech-decisions.md
Use skills: equity-research, backtest-expert, tw-stock-analyzer
Depends on: Data Engineer completing models (can start indicators
with mock data, switch to real models later)
Tasks:
- backend/app/services/technical_analysis.py
- backend/app/services/screener.py
- backend/app/services/backtester.py
- backend/app/services/valuation.py
- tests/unit/test_analysis_*.py
  Quality gate: RSI(14) of known data matches expected values,
  backtest of buy-and-hold SPY matches known benchmark returns

### Teammate: Backend API Developer name: Eve
Read first: api-design.md, infrastructure.md
Depends on: Data Engineer (models), Quant (services)
Start with: routes that only need models (stock list, price history)
Tasks:
- backend/app/api/routes/ — all endpoints from api-design.md
- backend/app/api/deps.py — dependency injection
- backend/app/core/config.py — settings management
- backend/app/main.py — app factory
- tests/integration/test_api_*.py
  Quality gate: every endpoint returns exactly the response
  schema defined in api-design.md

### Teammate: Frontend Developer name: Frank
Read first: F005, F006, F007 specs, api-design.md
Depends on: Backend API (use mock data initially)
Tasks:
- frontend/src/pages/ — all pages from spec
- frontend/src/components/charts/ — candlestick + indicators
- frontend/src/components/screener/ — filter UI
- frontend/src/components/backtest/ — results visualization
- frontend/src/services/api.ts — API client matching api-design.md
- frontend/src/hooks/ — data fetching hooks
  Quality gate: all pages render without errors,
  charts display correctly with mock data

### Teammate: QA Engineer name: Grace
Read first: ALL feature specs (Acceptance Criteria sections)
Starts immediately, works in parallel with everyone
Tasks:
- tests/e2e/ — Playwright tests based on Given/When/Then
- tests/contract/ — API contract tests vs api-design.md
- tests/validation/ — backtest accuracy verification
- docs/test-reports/coverage-report.md
- If any teammate's output violates its spec,
  message that teammate AND message you (Manager)
  Quality gate: all P0 acceptance criteria have corresponding tests

---

## Your Management Protocol for Phase 2:

### Spawn Order:
1. First: Data Engineer + QA Engineer (QA starts writing tests
   from specs immediately, doesn't need code yet)
2. When Data Engineer completes models: spawn Quant Analyst
3. When Data Engineer completes models + at least 2 API services
   exist: spawn Backend API Developer
4. When at least 3 API endpoints are working: spawn Frontend Developer

### Progress Tracking:
- Update task-board.md after every task completion
- Write status-log.md entry every time a teammate completes
  a major deliverable
- Track blockers proactively: if Teammate A hasn't messaged
  in a while, check in

### Quality Enforcement:
- When any teammate marks a task complete, verify:
  - File exists and is non-trivial
  - Tests exist and you can confirm they were written
  - Output matches the architecture docs
- If quality gate fails, do NOT mark done.
  Send specific feedback: "Line X of api-design.md specifies
  the response includes a 'metadata' field, but your endpoint
  at routes/stocks.py doesn't include it. Please fix."

### Conflict Resolution:
- If Backend says API design is impractical → check with
  Architect's docs, make a call, log in decisions-log.md
- If Frontend needs an endpoint changed → route through you,
  verify it doesn't break other consumers, then approve
- If QA finds a bug → assign to the responsible teammate
  as a new task with BLOCKED status on the original

### Integration Phase (after all teammates complete):
1. Ask Backend to run all integration tests
2. Ask Frontend to switch from mock data to real API
3. Ask QA to run full E2E suite
4. Collect all test results into docs/test-reports/
5. Create docs/management/phase2-handoff.md:
  - What works
  - What has known issues
  - Remaining P1/P2 features not yet implemented
  - Recommendations for next iteration
6. Message me: "Phase 2 complete. Review phase2-handoff.md."