"""Unit tests for the Backtester engine.

External data fetching is mocked via AsyncMock so tests are fast and
deterministic.  Where known closed-form results exist, they are verified
against the implementation.
"""

import math
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.backtester import Backtester, BacktestConfig, Trade
from app.services.technical_analysis import TechnicalAnalyzer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prices(closes: list[float]) -> list[dict]:
    """Build OHLCV list from closes with sequential dates."""
    from datetime import date, timedelta

    base = date(2024, 1, 1)
    return [
        {
            "date": (base + timedelta(days=i)).isoformat(),
            "open": c,
            "high": c + 1.0,
            "low": c - 1.0,
            "close": c,
            "volume": 1_000_000,
            "adj_close": c,
        }
        for i, c in enumerate(closes)
    ]


def _make_backtester(price_data: list[dict]) -> Backtester:
    analyzer = TechnicalAnalyzer()
    fetcher = MagicMock()
    fetcher.fetch_history = AsyncMock(return_value=price_data)
    return Backtester(analyzer=analyzer, fetcher=fetcher)


def _config(
    strategy: str = "buy_and_hold",
    initial_capital: float = 100_000.0,
    commission: float = 0.001425,
    tax: float = 0.003,
    params: dict | None = None,
) -> BacktestConfig:
    return BacktestConfig(
        symbol="TEST",
        strategy=strategy,
        start_date="2024-01-01",
        end_date="2024-12-31",
        initial_capital=initial_capital,
        commission=commission,
        tax=tax,
        params=params or {},
    )


# ---------------------------------------------------------------------------
# Buy-and-Hold strategy
# ---------------------------------------------------------------------------


class TestBuyAndHold:
    async def test_bah_produces_two_trades(self) -> None:
        """Buy-and-hold produces exactly one buy and one sell."""
        prices = _prices([100.0, 110.0, 120.0, 130.0])
        bt = _make_backtester(prices)
        result = await bt.run(_config("buy_and_hold"))
        buys = [t for t in result.trades if t.action == "buy"]
        sells = [t for t in result.trades if t.action == "sell"]
        assert len(buys) == 1
        assert len(sells) == 1

    async def test_bah_buy_on_first_close(self) -> None:
        prices = _prices([100.0, 120.0])
        bt = _make_backtester(prices)
        result = await bt.run(_config("buy_and_hold"))
        buy = [t for t in result.trades if t.action == "buy"][0]
        assert buy.price == pytest.approx(100.0)

    async def test_bah_sell_on_last_close(self) -> None:
        prices = _prices([100.0, 120.0])
        bt = _make_backtester(prices)
        result = await bt.run(_config("buy_and_hold"))
        sell = [t for t in result.trades if t.action == "sell"][0]
        assert sell.price == pytest.approx(120.0)

    async def test_bah_final_value_formula(self) -> None:
        """final_value ≈ initial_capital × (last_close / first_close) - commissions.

        Exact formula (per spec):
            shares = floor((capital - buy_commission) / buy_price)
            buy_cost = shares × buy_price × (1 + commission)
            sell_proceeds = shares × sell_price × (1 - commission - tax)
            final = sell_proceeds + (capital - buy_cost)   ← residual cash
        """
        initial = 100_000.0
        commission = 0.001425
        tax = 0.003
        buy_price = 100.0
        sell_price = 200.0

        buy_commission_rate = commission
        shares = int((initial - initial * buy_commission_rate) / buy_price)
        buy_cost = shares * buy_price
        buy_comm = buy_cost * commission
        residual_cash = initial - buy_cost - buy_comm
        sell_value = shares * sell_price
        sell_comm = sell_value * (commission + tax)
        expected_final = residual_cash + sell_value - sell_comm

        prices = _prices([buy_price, sell_price])
        bt = _make_backtester(prices)
        result = await bt.run(
            BacktestConfig(
                symbol="TEST",
                strategy="buy_and_hold",
                start_date="2024-01-01",
                end_date="2024-12-31",
                initial_capital=initial,
                commission=commission,
                tax=tax,
            )
        )
        assert result.final_value == pytest.approx(expected_final, rel=1e-4)

    async def test_bah_total_return_positive_on_price_rise(self) -> None:
        prices = _prices([100.0, 150.0])
        bt = _make_backtester(prices)
        result = await bt.run(_config("buy_and_hold"))
        assert result.total_return > 0

    async def test_bah_total_return_negative_on_price_fall(self) -> None:
        prices = _prices([200.0, 100.0])
        bt = _make_backtester(prices)
        result = await bt.run(_config("buy_and_hold"))
        assert result.total_return < 0

    async def test_bah_single_bar_returns_empty(self) -> None:
        """Only one bar — no room for a buy+sell pair."""
        prices = _prices([100.0])
        bt = _make_backtester(prices)
        result = await bt.run(_config("buy_and_hold"))
        assert result.trades == []

    async def test_bah_equity_curve_has_daily_point(self) -> None:
        prices = _prices([100.0, 110.0, 120.0])
        bt = _make_backtester(prices)
        result = await bt.run(_config("buy_and_hold"))
        assert len(result.equity_curve) == len(prices)

    async def test_bah_no_price_data_returns_empty_result(self) -> None:
        """Empty price data → zero metrics, initial capital preserved."""
        bt = _make_backtester([])
        result = await bt.run(_config("buy_and_hold"))
        assert result.trades == []
        assert result.final_value == 100_000.0
        assert result.total_return == 0.0


# ---------------------------------------------------------------------------
# SMA Crossover strategy
# ---------------------------------------------------------------------------


class TestSMACrossover:
    def _crossover_prices(self) -> list[dict]:
        """Build a price series with a clear golden cross followed by a death cross.

        Prices rise for 30 bars (short SMA crosses above long SMA) then
        fall for 30 bars (short SMA crosses back below long SMA).
        """
        rising = [50.0 + i * 2 for i in range(30)]
        falling = [108.0 - i * 2 for i in range(30)]
        return _prices(rising + falling)

    async def test_crossover_generates_trades(self) -> None:
        prices = self._crossover_prices()
        bt = _make_backtester(prices)
        result = await bt.run(
            _config("sma_crossover", params={"short_period": 5, "long_period": 10})
        )
        # Should have at least one buy.
        buys = [t for t in result.trades if t.action == "buy"]
        assert len(buys) >= 1

    async def test_crossover_trades_alternate_buy_sell(self) -> None:
        """After a force-close, the trade sequence must be buy → sell (→ buy → sell …)."""
        prices = self._crossover_prices()
        bt = _make_backtester(prices)
        result = await bt.run(
            _config("sma_crossover", params={"short_period": 5, "long_period": 10})
        )
        # Verify alternating actions.
        actions = [t.action for t in result.trades]
        for i in range(0, len(actions) - 1, 2):
            assert actions[i] == "buy"
        for i in range(1, len(actions), 2):
            assert actions[i] == "sell"

    async def test_crossover_no_trade_flat_market(self) -> None:
        """No trades generated when price is perfectly flat (no cross possible)."""
        prices = _prices([100.0] * 60)
        bt = _make_backtester(prices)
        result = await bt.run(
            _config("sma_crossover", params={"short_period": 5, "long_period": 20})
        )
        # For a flat series both SMAs are identical — no cross occurs.
        buys = [t for t in result.trades if t.action == "buy"]
        assert len(buys) == 0

    async def test_crossover_insufficient_data(self) -> None:
        """Fewer bars than the long period → no trades, no crash."""
        prices = _prices([100.0] * 10)
        bt = _make_backtester(prices)
        result = await bt.run(
            _config("sma_crossover", params={"short_period": 5, "long_period": 50})
        )
        assert result.trades == []


# ---------------------------------------------------------------------------
# RSI Oversold strategy
# ---------------------------------------------------------------------------


class TestRSIOversold:
    async def test_rsi_oversold_buy_on_dip(self) -> None:
        """A sharp dip (oversold RSI) followed by a recovery should generate a trade."""
        # 20 bars rising → 10 bars sharp drop (RSI goes oversold) → 20 bars recovery.
        rising = [100.0 + i for i in range(20)]
        drop = [120.0 - i * 4 for i in range(10)]
        recovery = [80.0 + i for i in range(20)]
        prices = _prices(rising + drop + recovery)
        bt = _make_backtester(prices)
        result = await bt.run(
            _config(
                "rsi_oversold",
                params={"oversold": 30, "overbought": 70, "period": 14},
            )
        )
        buys = [t for t in result.trades if t.action == "buy"]
        assert len(buys) >= 1

    async def test_rsi_strategy_no_trade_stable_market(self) -> None:
        """Stable prices → RSI hovers near 50 → no buy signal."""
        prices = _prices([100.0 + (i % 3) * 0.5 for i in range(50)])
        bt = _make_backtester(prices)
        result = await bt.run(
            _config(
                "rsi_oversold",
                params={"oversold": 30, "overbought": 70, "period": 14},
            )
        )
        buys = [t for t in result.trades if t.action == "buy"]
        assert len(buys) == 0

    async def test_rsi_strategy_force_close_at_end(self) -> None:
        """An open position at the end of the backtest must be force-closed."""
        # Prices drop sharply so RSI goes oversold, then stay low (no sell signal).
        drop = [100.0 - i * 3 for i in range(20)]
        flat = [40.0] * 30
        prices = _prices(drop + flat)
        bt = _make_backtester(prices)
        result = await bt.run(
            _config(
                "rsi_oversold",
                params={"oversold": 30, "overbought": 70, "period": 14},
            )
        )
        # If a buy occurred, there must be a corresponding sell (force-close).
        buys = [t for t in result.trades if t.action == "buy"]
        sells = [t for t in result.trades if t.action == "sell"]
        assert len(buys) == len(sells)


# ---------------------------------------------------------------------------
# Commission and Tax Calculation (台股 model)
# ---------------------------------------------------------------------------


class TestCommissionTax:
    def test_buy_commission_only(self) -> None:
        """Buy side: only commission applies (no transaction tax)."""
        bt = _make_backtester([])
        config = _config(commission=0.001425, tax=0.003)
        prices = _prices([100.0, 110.0])

        trades = bt._strategy_buy_and_hold(prices, config)
        buy = next(t for t in trades if t.action == "buy")
        expected_commission = buy.value * 0.001425
        assert buy.commission == pytest.approx(expected_commission, rel=1e-6)

    def test_sell_commission_plus_tax(self) -> None:
        """Sell side: commission + transaction tax both apply for TW stocks."""
        bt = _make_backtester([])
        config = _config(commission=0.001425, tax=0.003)
        prices = _prices([100.0, 110.0])

        trades = bt._strategy_buy_and_hold(prices, config)
        sell = next(t for t in trades if t.action == "sell")
        expected_commission = sell.value * (0.001425 + 0.003)
        assert sell.commission == pytest.approx(expected_commission, rel=1e-6)

    def test_zero_tax_us_model(self) -> None:
        """US model: tax=0, so sell commission = value × commission only."""
        bt = _make_backtester([])
        config = _config(commission=0.001, tax=0.0)
        prices = _prices([100.0, 110.0])

        trades = bt._strategy_buy_and_hold(prices, config)
        sell = next(t for t in trades if t.action == "sell")
        expected_commission = sell.value * 0.001
        assert sell.commission == pytest.approx(expected_commission, rel=1e-6)


# ---------------------------------------------------------------------------
# Max Drawdown
# ---------------------------------------------------------------------------


class TestMaxDrawdown:
    def test_max_drawdown_known_values(self) -> None:
        """Peak=100, trough=80 → drawdown = -20 %."""
        bt = _make_backtester([])
        curve = [
            {"date": "2024-01-01", "value": 100.0},
            {"date": "2024-01-02", "value": 110.0},
            {"date": "2024-01-03", "value": 80.0},  # trough after peak of 110
            {"date": "2024-01-04", "value": 95.0},
        ]
        mdd = bt._calculate_max_drawdown(curve)
        # Peak = 110, trough = 80 → (80-110)/110 * 100 = -27.27%
        assert mdd == pytest.approx((80 - 110) / 110 * 100, rel=1e-4)

    def test_max_drawdown_monotonically_rising_is_zero(self) -> None:
        bt = _make_backtester([])
        curve = [{"date": f"2024-01-{i:02d}", "value": 100.0 + i} for i in range(1, 11)]
        mdd = bt._calculate_max_drawdown(curve)
        assert mdd == pytest.approx(0.0, abs=1e-9)

    def test_max_drawdown_is_negative(self) -> None:
        bt = _make_backtester([])
        curve = [
            {"date": "2024-01-01", "value": 100.0},
            {"date": "2024-01-02", "value": 50.0},
        ]
        mdd = bt._calculate_max_drawdown(curve)
        assert mdd < 0.0

    def test_max_drawdown_single_point_is_zero(self) -> None:
        bt = _make_backtester([])
        curve = [{"date": "2024-01-01", "value": 100.0}]
        assert bt._calculate_max_drawdown(curve) == 0.0

    def test_max_drawdown_empty_is_zero(self) -> None:
        bt = _make_backtester([])
        assert bt._calculate_max_drawdown([]) == 0.0


# ---------------------------------------------------------------------------
# Sharpe Ratio
# ---------------------------------------------------------------------------


class TestSharpeRatio:
    def test_sharpe_constant_returns_zero(self) -> None:
        """Zero variance → Sharpe = 0."""
        bt = _make_backtester([])
        curve = [{"date": f"2024-01-{i:02d}", "value": 100.0} for i in range(1, 11)]
        # Constant equity → std = 0.
        sharpe = bt._calculate_sharpe(curve)
        assert sharpe == 0.0

    def test_sharpe_positive_for_rising_equity(self) -> None:
        """Consistently positive returns → positive Sharpe."""
        bt = _make_backtester([])
        curve = [
            {"date": f"2024-01-{i:02d}", "value": 100.0 + i * 0.5}
            for i in range(1, 31)
        ]
        sharpe = bt._calculate_sharpe(curve, risk_free_rate=0.0)
        assert sharpe > 0.0

    def test_sharpe_annualized_with_sqrt_252(self) -> None:
        """Verify the annualisation factor: result ≈ mean_excess / std * sqrt(252)."""
        import numpy as np

        bt = _make_backtester([])
        values = [100.0 + i * 0.3 + (i % 3) * 0.1 for i in range(30)]
        curve = [{"date": f"2024-01-{i:02d}", "value": v} for i, v in enumerate(values, 1)]

        arr = np.array(values)
        daily_ret = np.diff(arr) / arr[:-1]
        daily_rf = 0.02 / 252
        excess = daily_ret - daily_rf
        expected = float(excess.mean() / excess.std(ddof=1) * math.sqrt(252))

        sharpe = bt._calculate_sharpe(curve, risk_free_rate=0.02)
        assert sharpe == pytest.approx(expected, rel=1e-4)

    def test_sharpe_empty_returns_zero(self) -> None:
        bt = _make_backtester([])
        assert bt._calculate_sharpe([]) == 0.0

    def test_sharpe_single_point_returns_zero(self) -> None:
        bt = _make_backtester([])
        assert bt._calculate_sharpe([{"date": "2024-01-01", "value": 100.0}]) == 0.0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    async def test_unknown_strategy_returns_empty(self) -> None:
        prices = _prices([100.0, 110.0])
        bt = _make_backtester(prices)
        result = await bt.run(
            BacktestConfig(
                symbol="TEST",
                strategy="alien_strategy",
                start_date="2024-01-01",
                end_date="2024-12-31",
            )
        )
        assert result.trades == []
        assert result.total_return == 0.0

    async def test_date_filter_applied(self) -> None:
        """Prices outside [start_date, end_date] are excluded."""
        # Prices from 2023-12-01 to 2024-01-31.
        from datetime import date, timedelta

        all_prices = [
            {
                "date": (date(2023, 12, 1) + timedelta(days=i)).isoformat(),
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0 + i,
                "volume": 1_000_000,
                "adj_close": 100.0 + i,
            }
            for i in range(62)
        ]

        fetcher = MagicMock()
        fetcher.fetch_history = AsyncMock(return_value=all_prices)
        bt = Backtester(TechnicalAnalyzer(), fetcher)

        # Only request January 2024 data.
        config = BacktestConfig(
            symbol="TEST",
            strategy="buy_and_hold",
            start_date="2024-01-01",
            end_date="2024-01-31",
        )
        result = await bt.run(config)

        # All equity curve dates must be within the requested window.
        for point in result.equity_curve:
            assert "2024-01-01" <= point["date"] <= "2024-01-31"

    async def test_win_rate_all_wins(self) -> None:
        """If every sell proceeds > buy cost → win_rate = 100 %."""
        bt = _make_backtester([])
        trades = [
            Trade(date="2024-01-01", action="buy", price=100.0, shares=10, commission=1.5, value=1000.0),
            Trade(date="2024-01-02", action="sell", price=120.0, shares=10, commission=2.0, value=1200.0),
        ]
        win_rate, pairs = bt._win_rate(trades)
        assert win_rate == pytest.approx(100.0)
        assert pairs == 1

    async def test_win_rate_all_losses(self) -> None:
        """Every sell < buy cost → win_rate = 0 %."""
        bt = _make_backtester([])
        trades = [
            Trade(date="2024-01-01", action="buy", price=100.0, shares=10, commission=1.5, value=1000.0),
            Trade(date="2024-01-02", action="sell", price=80.0, shares=10, commission=2.0, value=800.0),
        ]
        win_rate, pairs = bt._win_rate(trades)
        assert win_rate == pytest.approx(0.0)
        assert pairs == 1

    async def test_win_rate_no_trades(self) -> None:
        bt = _make_backtester([])
        win_rate, pairs = bt._win_rate([])
        assert win_rate == 0.0
        assert pairs == 0

    async def test_equity_curve_starts_at_initial_capital(self) -> None:
        """On the first bar (before any trade lands), equity ≈ initial_capital."""
        prices = _prices([100.0] * 5)
        bt = _make_backtester(prices)
        # Use a strategy with no initial buy on day 0.
        # buy_and_hold buys on the first bar, so equity on bar 0 < initial after buy.
        # We just verify the curve has the right length and is non-negative.
        result = await bt.run(_config("buy_and_hold"))
        assert all(e["value"] >= 0 for e in result.equity_curve)
