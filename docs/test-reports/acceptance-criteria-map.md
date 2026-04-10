# Acceptance Criteria → Test Mapping

Last updated: 2026-04-09
Owner: QA Engineer

## Legend

| Status | Meaning |
|--------|---------|
| PASS | Test exists and currently passes |
| PENDING | Test exists, marked xfail/skip — will pass once feature is implemented |
| MISSING | No test yet — needs to be written |

---

## P0 Features

### Stock Data Pipeline (F001)

| Criteria | Test File | Test ID | Status |
|----------|-----------|---------|--------|
| GET /stocks list returns envelope | tests/contract/test_response_envelope.py | TestListEnvelope::test_stocks_list_envelope | PASS |
| meta.total/page/limit are integers | tests/contract/test_response_envelope.py | TestListEnvelope::test_stocks_list_meta_* | PASS |
| Fetch US stock detail | tests/contract/test_stocks_contract.py | TestStockDetailContract::test_known_us_symbol_returns_data | PENDING |
| Fetch TW stock detail (台積電 2330) | tests/contract/test_stocks_contract.py | TestStockDetailContract::test_known_tw_symbol_returns_data | PENDING |
| GET /stocks/{symbol} returns data envelope | tests/contract/test_stocks_contract.py | TestStockDetailContract::test_200_response_has_data_key | PASS |
| Stock detail has symbol/name/market fields | tests/contract/test_stocks_contract.py | TestStockDetailContract::test_stock_detail_required_fields | PENDING |
| US stock OHLCV history returned | tests/contract/test_stocks_contract.py | TestStockHistoryContract::test_us_stock_history_returns_ohlcv | PENDING |
| TW stock OHLCV history returned | tests/contract/test_stocks_contract.py | TestStockHistoryContract::test_tw_stock_history_returns_ohlcv | PENDING |
| History is chronologically ordered | tests/contract/test_stocks_contract.py | TestStockHistoryContract::test_history_dates_are_chronological | PENDING |
| OHLCV numeric types are correct | tests/contract/test_stocks_contract.py | TestStockHistoryContract::test_history_numeric_fields_are_numbers | PENDING |
| Data cached in Redis | tests/unit/test_cache.py (DE owns) | — | MISSING |
| Daily scheduled data fetch | tests/unit/test_data_tasks.py (DE owns) | — | MISSING |

### Technical Indicators (F002)

| Criteria | Test File | Test ID | Status |
|----------|-----------|---------|--------|
| GET /indicators returns data dict | tests/contract/test_stocks_contract.py | TestStockIndicatorsContract::test_data_is_dict | PASS |
| SMA returned when requested | tests/contract/test_stocks_contract.py | TestStockIndicatorsContract::test_sma_key_present_when_requested | PENDING |
| RSI returned when requested | tests/contract/test_stocks_contract.py | TestStockIndicatorsContract::test_rsi_key_present_when_requested | PENDING |
| MACD returned when requested | tests/contract/test_stocks_contract.py | TestStockIndicatorsContract::test_macd_key_present_when_requested | PENDING |
| Multiple indicators all returned | tests/contract/test_stocks_contract.py | TestStockIndicatorsContract::test_multiple_indicators_all_present | PENDING |
| Indicator values are lists | tests/contract/test_stocks_contract.py | TestStockIndicatorsContract::test_indicator_values_are_lists | PENDING |
| Calculate EMA | tests/unit/test_indicators.py (DE owns) | — | MISSING |
| Indicator unit tests (SMA/RSI/MACD) | tests/unit/test_indicators.py (DE owns) | — | MISSING |

### Stock Screener (F003)

| Criteria | Test File | Test ID | Status |
|----------|-----------|---------|--------|
| Multi-condition filter API | tests/contract/test_screener_contract.py | — | MISSING |
| Market filter (US/TW) | tests/contract/test_stocks_contract.py | TestListStocksContract::test_market_tw_filters_to_tw_stocks | PENDING |
| Text search (?q=) | tests/contract/test_stocks_contract.py | TestListStocksContract::test_search_returns_matching_symbols | PENDING |
| TW text search | tests/contract/test_stocks_contract.py | TestListStocksContract::test_tw_search_returns_matching_stocks | PENDING |
| Pagination (page/limit respected) | tests/contract/test_response_envelope.py | TestListEnvelope::test_stocks_pagination_* | PENDING |
| Screener UI — search input present | tests/e2e/specs/stock-search.spec.ts | "search input element is present" | PENDING |
| Screener UI — typing shows suggestions | tests/e2e/specs/stock-search.spec.ts | "typing AAPL shows Apple in suggestions" | PENDING |

### Backtesting (F004)

| Criteria | Test File | Test ID | Status |
|----------|-----------|---------|--------|
| Run backtest endpoint exists | tests/contract/test_backtest_contract.py | — | MISSING |
| Backtest returns P&L metrics | tests/contract/test_backtest_contract.py | — | MISSING |
| Compare to benchmark (e.g. SPY) | tests/contract/test_backtest_contract.py | — | MISSING |
| Backtest service unit tests | tests/unit/test_backtest_service.py (DE owns) | — | MISSING |

### Watchlist (F007)

| Criteria | Test File | Test ID | Status |
|----------|-----------|---------|--------|
| GET /watchlists returns list envelope | tests/contract/test_response_envelope.py | TestListEnvelope::test_watchlists_list_envelope | PASS |
| POST /watchlists accepted (200/201) | tests/contract/test_watchlists_contract.py | TestCreateWatchlistContract::test_create_returns_200_or_201 | PASS |
| Created watchlist has id/name/symbols | tests/contract/test_watchlists_contract.py | TestCreateWatchlistContract::test_created_watchlist_has_required_fields | PENDING |
| Created watchlist name matches payload | tests/contract/test_watchlists_contract.py | TestCreateWatchlistContract::test_created_watchlist_name_matches_payload | PENDING |
| Created watchlist symbols match payload | tests/contract/test_watchlists_contract.py | TestCreateWatchlistContract::test_created_watchlist_symbols_match_payload | PENDING |
| GET /watchlists/{id} returns correct item | tests/contract/test_watchlists_contract.py | TestGetWatchlistContract::test_existing_id_returns_watchlist | PENDING |
| GET /watchlists/999 returns 404 | tests/contract/test_watchlists_contract.py | TestGetWatchlistContract::test_nonexistent_id_returns_404 | PENDING |
| PUT /watchlists/{id} updates name | tests/contract/test_watchlists_contract.py | TestUpdateWatchlistContract::test_update_changes_watchlist_name | PENDING |
| DELETE /watchlists/{id} confirmed | tests/contract/test_watchlists_contract.py | TestDeleteWatchlistContract::test_returns_200_or_204_or_404 | PASS |
| After delete, GET returns 404 | tests/contract/test_watchlists_contract.py | TestDeleteWatchlistContract::test_delete_then_get_returns_404 | PENDING |

---

## P1 Features

### Health Check

| Criteria | Test File | Test ID | Status |
|----------|-----------|---------|--------|
| GET /api/health returns 200 | tests/contract/test_health_contract.py | TestHealthContract::test_health_returns_200 | PASS |
| GET /api/health returns {"status": "ok"} | tests/contract/test_health_contract.py | TestHealthContract::test_health_response_shape | PASS |
| Response is application/json | tests/contract/test_health_contract.py | TestHealthContract::test_health_content_type_is_json | PASS |

### E2E Smoke Tests

| Criteria | Test File | Test ID | Status |
|----------|-----------|---------|--------|
| App loads without console errors | tests/e2e/specs/health.spec.ts | "home page loads without errors" | PASS |
| Header visible | tests/e2e/specs/health.spec.ts | "application header is visible" | PASS |
| Title reads "Stock Analyzer" | tests/e2e/specs/health.spec.ts | "application title reads Stock Analyzer" | PASS |
| Root route renders | tests/e2e/specs/navigation.spec.ts | "root route / renders without a 404 page" | PASS |
| SPA unknown route falls back | tests/e2e/specs/navigation.spec.ts | "unknown route falls back to app shell" | PASS |
| /stocks route renders | tests/e2e/specs/navigation.spec.ts | "navigating to /stocks renders the stock list page" | PENDING |
| /stocks/AAPL renders detail | tests/e2e/specs/navigation.spec.ts | "navigating to /stocks/AAPL renders stock detail page" | PENDING |

---

## Error Envelope Contract

| Criteria | Test File | Test ID | Status |
|----------|-----------|---------|--------|
| Unknown stock symbol → 404 | tests/contract/test_response_envelope.py | TestErrorEnvelope::test_unknown_stock_returns_404 | PENDING |
| 404 body has "detail" key | tests/contract/test_response_envelope.py | TestErrorEnvelope::test_unknown_stock_error_envelope | PENDING |
| Unknown watchlist ID → 404 | tests/contract/test_response_envelope.py | TestErrorEnvelope::test_unknown_watchlist_returns_404 | PENDING |

---

## Test Coverage Summary

| Category | Total Criteria | PASS | PENDING | MISSING |
|----------|---------------|------|---------|---------|
| F001 Stock Data Pipeline | 12 | 4 | 8 | 2 (DE) |
| F002 Technical Indicators | 8 | 1 | 5 | 3 (DE) |
| F003 Screener | 7 | 0 | 5 | 2 |
| F004 Backtesting | 4 | 0 | 0 | 4 (DE) |
| F007 Watchlist | 10 | 3 | 7 | 0 |
| Health / Smoke | 8 | 7 | 1 | 0 |
| Error Envelopes | 3 | 0 | 3 | 0 |
| **Total** | **52** | **15** | **29** | **11** |

---

## Notes for Data Engineer

Tests marked PENDING will automatically turn green once you implement:
1. Real database persistence for watchlist CRUD
2. Stock data fetch from yfinance (US) and FinMind (TW)
3. OHLCV history storage and retrieval
4. Technical indicator calculation (SMA, RSI, MACD, EMA)
5. Proper 404 responses for unknown symbols / IDs
6. Error envelope format: `{"detail": "...", "code": "..."}`

Tests marked MISSING (DE owns) are unit tests for services you will build.
QA will write contract-level tests; DE owns unit tests for internal logic.
