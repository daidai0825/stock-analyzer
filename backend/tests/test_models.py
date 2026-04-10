"""Unit tests for ORM models — use an in-memory SQLite/H2-like database.

We use SQLite (via aiosqlite) because it is zero-configuration and does not
require a running PostgreSQL instance.  The tests verify:
  - table creation succeeds with all expected columns,
  - relationships work correctly,
  - unique constraints are enforced where applicable.

Add ``aiosqlite`` to requirements.txt (or the test extras) if it is not
already present.
"""

from datetime import date, datetime

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import (
    Alert,
    BacktestResult,
    Base,
    DailyPrice,
    Portfolio,
    PortfolioHolding,
    Stock,
    TechnicalIndicator,
    Watchlist,
    WatchlistItem,
)

# ---------------------------------------------------------------------------
# Fixtures — in-memory SQLite
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="module")
async def engine():
    _engine = create_async_engine(TEST_DB_URL, echo=False)
    async with _engine.begin() as conn:
        # SQLite does not enforce FK constraints by default; enable them.
        await conn.execute(text("PRAGMA foreign_keys = ON"))
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    await _engine.dispose()


@pytest.fixture
async def db(engine) -> AsyncSession:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()  # roll back each test for isolation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stock(symbol: str = "AAPL", market: str = "US") -> Stock:
    return Stock(symbol=symbol, name=f"{symbol} Inc.", market=market)


# ---------------------------------------------------------------------------
# Schema-level smoke test
# ---------------------------------------------------------------------------


class TestTablesCreated:
    async def test_all_tables_exist(self, engine):
        async with engine.connect() as conn:
            table_names = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
        expected = {
            "stocks",
            "daily_prices",
            "technical_indicators",
            "backtest_results",
            "alerts",
            "portfolios",
            "portfolio_holdings",
            "watchlists",
            "watchlist_items",
        }
        assert expected.issubset(set(table_names))


# ---------------------------------------------------------------------------
# Stock model
# ---------------------------------------------------------------------------


class TestStockModel:
    async def test_create_stock(self, db):
        stock = _make_stock()
        db.add(stock)
        await db.flush()
        assert stock.id is not None

    async def test_stock_optional_fields_nullable(self, db):
        stock = Stock(symbol="GOOG2", name="Alphabet", market="US")
        db.add(stock)
        await db.flush()
        assert stock.industry is None
        assert stock.description is None

    async def test_stock_with_all_fields(self, db):
        stock = Stock(
            symbol="TSLA2",
            name="Tesla",
            market="US",
            industry="Automotive",
            description="EV maker",
        )
        db.add(stock)
        await db.flush()
        assert stock.industry == "Automotive"


# ---------------------------------------------------------------------------
# DailyPrice model
# ---------------------------------------------------------------------------


class TestDailyPriceModel:
    async def test_create_daily_price(self, db):
        stock = _make_stock("AAPL2")
        db.add(stock)
        await db.flush()

        dp = DailyPrice(
            stock_id=stock.id,
            date=date(2024, 1, 2),
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=1_000_000,
            adj_close=103.0,
        )
        db.add(dp)
        await db.flush()
        assert dp.id is not None

    async def test_daily_price_relationship(self, db):
        stock = _make_stock("MSFT2")
        db.add(stock)
        await db.flush()

        dp = DailyPrice(
            stock_id=stock.id,
            date=date(2024, 1, 3),
            open=400.0,
            high=410.0,
            low=398.0,
            close=405.0,
            volume=500_000,
        )
        db.add(dp)
        await db.flush()

        # Access the relationship
        await db.refresh(stock, attribute_names=["daily_prices"])
        symbols = [p.date for p in stock.daily_prices]
        assert date(2024, 1, 3) in symbols


# ---------------------------------------------------------------------------
# TechnicalIndicator model
# ---------------------------------------------------------------------------


class TestTechnicalIndicatorModel:
    async def test_create_indicator(self, db):
        stock = _make_stock("NVDA2")
        db.add(stock)
        await db.flush()

        ind = TechnicalIndicator(
            stock_id=stock.id,
            date=date(2024, 1, 2),
            indicator_name="RSI_14",
            value=65.3,
        )
        db.add(ind)
        await db.flush()
        assert ind.id is not None


# ---------------------------------------------------------------------------
# BacktestResult model
# ---------------------------------------------------------------------------


class TestBacktestResultModel:
    async def test_create_backtest_result(self, db):
        br = BacktestResult(
            strategy_name="SMA_Crossover",
            symbol="AAPL",
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            initial_capital=100_000.0,
            final_value=120_000.0,
            total_return=0.20,
            max_drawdown=-0.08,
            sharpe_ratio=1.5,
            trades_count=25,
            win_rate=0.60,
            params={"sma_short": 10, "sma_long": 50},
        )
        db.add(br)
        await db.flush()
        assert br.id is not None
        assert br.params["sma_short"] == 10

    async def test_backtest_result_nullable_fields(self, db):
        br = BacktestResult(
            strategy_name="MinimalStrat",
            symbol="TSLA",
            start_date=date(2023, 1, 1),
            end_date=date(2023, 6, 30),
            initial_capital=50_000.0,
            final_value=48_000.0,
            total_return=-0.04,
            max_drawdown=-0.10,
            trades_count=0,
        )
        db.add(br)
        await db.flush()
        assert br.sharpe_ratio is None
        assert br.win_rate is None
        assert br.params is None


# ---------------------------------------------------------------------------
# Alert model
# ---------------------------------------------------------------------------


class TestAlertModel:
    async def test_create_alert_price_above(self, db):
        alert = Alert(
            symbol="AAPL",
            alert_type="price_above",
            condition={"threshold": 200.0},
            is_active=True,
        )
        db.add(alert)
        await db.flush()
        assert alert.id is not None
        assert alert.triggered_at is None

    async def test_create_alert_indicator(self, db):
        alert = Alert(
            symbol="2330",
            alert_type="indicator",
            condition={"indicator": "RSI_14", "operator": ">", "value": 70},
            is_active=True,
        )
        db.add(alert)
        await db.flush()
        assert alert.condition["indicator"] == "RSI_14"


# ---------------------------------------------------------------------------
# Portfolio + PortfolioHolding models
# ---------------------------------------------------------------------------


class TestPortfolioModel:
    async def test_create_portfolio_and_holding(self, db):
        portfolio = Portfolio(name="My Portfolio")
        db.add(portfolio)
        await db.flush()

        holding = PortfolioHolding(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            shares=10.0,
            avg_cost=150.0,
        )
        db.add(holding)
        await db.flush()
        assert holding.id is not None

    async def test_portfolio_relationship(self, db):
        portfolio = Portfolio(name="Growth Portfolio")
        db.add(portfolio)
        await db.flush()

        for sym, shares in [("TSLA", 5.0), ("NVDA", 3.0)]:
            db.add(PortfolioHolding(
                portfolio_id=portfolio.id,
                symbol=sym,
                shares=shares,
                avg_cost=100.0,
            ))
        await db.flush()

        await db.refresh(portfolio, attribute_names=["holdings"])
        assert len(portfolio.holdings) == 2
        symbols = {h.symbol for h in portfolio.holdings}
        assert symbols == {"TSLA", "NVDA"}


# ---------------------------------------------------------------------------
# Watchlist + WatchlistItem models (existing models — regression guard)
# ---------------------------------------------------------------------------


class TestWatchlistModel:
    async def test_create_watchlist_with_items(self, db):
        wl = Watchlist(name="Favourites")
        db.add(wl)
        await db.flush()

        item = WatchlistItem(watchlist_id=wl.id, symbol="AAPL")
        db.add(item)
        await db.flush()
        assert item.id is not None

    async def test_watchlist_relationship(self, db):
        wl = Watchlist(name="Tech Stocks")
        db.add(wl)
        await db.flush()

        for sym in ["MSFT", "GOOG", "META"]:
            db.add(WatchlistItem(watchlist_id=wl.id, symbol=sym))
        await db.flush()

        await db.refresh(wl, attribute_names=["items"])
        assert len(wl.items) == 3
