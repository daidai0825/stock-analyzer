"""Strategy backtesting engine for stock price data.

Supports built-in strategies:
  - buy_and_hold     — buy on the first available bar, sell on the last.
  - sma_crossover    — buy on golden cross (short SMA > long SMA),
                       sell on death cross.
  - rsi_oversold     — buy when RSI < oversold threshold, sell when > overbought.

Taiwan stock cost model:
  買進: 成交金額 × 手續費率 (0.1425 %, min 20 TWD — not enforced here)
  賣出: 成交金額 × 手續費率 (0.1425 %) + 成交金額 × 交易稅率 (0.3 %)

US default cost model:
  Both sides: commission only (no transaction tax).
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from app.services.data_fetcher import StockDataFetcher
from app.services.technical_analysis import TechnicalAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Configuration for a single backtest run."""

    symbol: str
    strategy: str  # "buy_and_hold" | "sma_crossover" | "rsi_oversold" | "custom"
    start_date: str  # ISO-8601 "YYYY-MM-DD"
    end_date: str  # ISO-8601 "YYYY-MM-DD"
    initial_capital: float = 100_000.0
    commission: float = 0.001425  # 0.1425 %
    tax: float = 0.003  # 0.3 % (applied on sell for TW; set 0 for US)
    params: dict = field(default_factory=dict)


@dataclass
class Trade:
    """A single executed trade (buy or sell)."""

    date: str
    action: str  # "buy" | "sell"
    price: float
    shares: int
    commission: float
    value: float  # gross transaction value = price × shares


@dataclass
class BacktestResult:
    """Full backtest output including all performance metrics."""

    config: BacktestConfig
    trades: list[Trade]
    equity_curve: list[dict]  # [{"date": str, "value": float}, …]
    total_return: float  # percentage, e.g. 15.3 means +15.3 %
    annualized_return: float  # CAGR as a percentage
    max_drawdown: float  # negative percentage, e.g. -12.5
    sharpe_ratio: float
    win_rate: float  # percentage of profitable round-trips
    total_trades: int  # number of completed buy+sell round-trips
    final_value: float  # portfolio value at end of simulation


class Backtester:
    """Strategy backtesting engine."""

    def __init__(self, analyzer: TechnicalAnalyzer, fetcher: StockDataFetcher) -> None:
        self.analyzer = analyzer
        self.fetcher = fetcher

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, config: BacktestConfig) -> BacktestResult:
        """Fetch price data and execute the configured strategy.

        Args:
            config: BacktestConfig specifying the symbol, strategy, and dates.

        Returns:
            A BacktestResult with full trade history and performance metrics.
        """
        # Fetch price data for the exact date range.
        prices = await self.fetcher.fetch_history(
            config.symbol,
            start_date=config.start_date,
            end_date=config.end_date,
        )

        if not prices:
            logger.warning(
                "run(): no price data for %s in [%s, %s]",
                config.symbol,
                config.start_date,
                config.end_date,
            )
            return self._empty_result(config)

        # Dispatch to the correct strategy.
        strategy_fn = {
            "buy_and_hold": self._strategy_buy_and_hold,
            "sma_crossover": self._strategy_sma_crossover,
            "rsi_oversold": self._strategy_rsi_oversold,
        }.get(config.strategy)

        if strategy_fn is None:
            logger.error("run(): unknown strategy %r", config.strategy)
            return self._empty_result(config)

        trades = strategy_fn(prices, config)
        equity_curve = self._build_equity_curve(prices, trades, config)
        metrics = self._calculate_metrics(trades, equity_curve, config)

        return BacktestResult(
            config=config,
            trades=trades,
            equity_curve=equity_curve,
            **metrics,
        )

    # ------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------

    def _strategy_buy_and_hold(
        self, prices: list[dict], config: BacktestConfig
    ) -> list[Trade]:
        """Buy on the first bar, sell on the last bar."""
        if len(prices) < 2:
            return []

        capital = config.initial_capital
        buy_price = prices[0]["close"]
        buy_date = prices[0]["date"]
        buy_value = capital  # spend all capital
        buy_commission = buy_value * config.commission
        shares = int((buy_value - buy_commission) / buy_price)

        if shares <= 0:
            return []

        actual_buy_value = shares * buy_price
        actual_buy_commission = actual_buy_value * config.commission

        sell_price = prices[-1]["close"]
        sell_date = prices[-1]["date"]
        sell_value = shares * sell_price
        sell_commission = sell_value * (config.commission + config.tax)

        return [
            Trade(
                date=buy_date,
                action="buy",
                price=buy_price,
                shares=shares,
                commission=actual_buy_commission,
                value=actual_buy_value,
            ),
            Trade(
                date=sell_date,
                action="sell",
                price=sell_price,
                shares=shares,
                commission=sell_commission,
                value=sell_value,
            ),
        ]

    def _strategy_sma_crossover(
        self, prices: list[dict], config: BacktestConfig
    ) -> list[Trade]:
        """Golden/Death cross strategy.

        Buy when short SMA crosses above long SMA (golden cross).
        Sell when short SMA crosses below long SMA (death cross).

        Default params: short_period=10, long_period=50.
        """
        params = config.params or {}
        short_period = int(params.get("short_period", 10))
        long_period = int(params.get("long_period", 50))

        short_sma = self.analyzer.sma(prices, period=short_period)
        long_sma = self.analyzer.sma(prices, period=long_period)

        if not short_sma or not long_sma:
            return []

        # Build aligned date→value maps.
        short_map = {r["date"]: r["value"] for r in short_sma}
        long_map = {r["date"]: r["value"] for r in long_sma}

        # Dates where BOTH SMAs are defined.
        common_dates = sorted(set(short_map) & set(long_map))
        if len(common_dates) < 2:
            return []

        trades: list[Trade] = []
        position = 0  # shares held
        cash = config.initial_capital

        for i in range(1, len(common_dates)):
            d = common_dates[i]
            d_prev = common_dates[i - 1]
            price = self._price_on_date(prices, d)
            if price is None:
                continue

            s_curr = short_map[d]
            l_curr = long_map[d]
            s_prev = short_map[d_prev]
            l_prev = long_map[d_prev]

            # Golden cross: buy signal.
            if s_prev <= l_prev and s_curr > l_curr and position == 0:
                buy_value = cash
                buy_commission = buy_value * config.commission
                shares = int((buy_value - buy_commission) / price)
                if shares > 0:
                    cost = shares * price
                    commission = cost * config.commission
                    cash -= cost + commission
                    position = shares
                    trades.append(
                        Trade(
                            date=d,
                            action="buy",
                            price=price,
                            shares=shares,
                            commission=commission,
                            value=cost,
                        )
                    )

            # Death cross: sell signal.
            elif s_prev >= l_prev and s_curr < l_curr and position > 0:
                sell_value = position * price
                sell_commission = sell_value * (config.commission + config.tax)
                cash += sell_value - sell_commission
                trades.append(
                    Trade(
                        date=d,
                        action="sell",
                        price=price,
                        shares=position,
                        commission=sell_commission,
                        value=sell_value,
                    )
                )
                position = 0

        # Force-close any open position on the last date.
        if position > 0 and prices:
            last = prices[-1]
            sell_value = position * last["close"]
            sell_commission = sell_value * (config.commission + config.tax)
            trades.append(
                Trade(
                    date=last["date"],
                    action="sell",
                    price=last["close"],
                    shares=position,
                    commission=sell_commission,
                    value=sell_value,
                )
            )

        return trades

    def _strategy_rsi_oversold(
        self, prices: list[dict], config: BacktestConfig
    ) -> list[Trade]:
        """Buy when RSI drops below ``oversold``, sell when it rises above ``overbought``.

        Default params: oversold=30, overbought=70, period=14.
        """
        params = config.params or {}
        oversold = float(params.get("oversold", 30))
        overbought = float(params.get("overbought", 70))
        rsi_period = int(params.get("period", 14))

        rsi_series = self.analyzer.rsi(prices, period=rsi_period)
        if not rsi_series:
            return []

        rsi_map = {r["date"]: r["value"] for r in rsi_series}

        trades: list[Trade] = []
        position = 0
        cash = config.initial_capital

        for i, bar in enumerate(prices):
            d = bar["date"]
            rsi_val = rsi_map.get(d)
            if rsi_val is None:
                continue

            price = bar["close"]

            # Buy signal: RSI crosses below oversold threshold.
            if rsi_val < oversold and position == 0:
                buy_value = cash
                commission = buy_value * config.commission
                shares = int((buy_value - commission) / price)
                if shares > 0:
                    cost = shares * price
                    commission = cost * config.commission
                    cash -= cost + commission
                    position = shares
                    trades.append(
                        Trade(
                            date=d,
                            action="buy",
                            price=price,
                            shares=shares,
                            commission=commission,
                            value=cost,
                        )
                    )

            # Sell signal: RSI crosses above overbought threshold.
            elif rsi_val > overbought and position > 0:
                sell_value = position * price
                sell_commission = sell_value * (config.commission + config.tax)
                cash += sell_value - sell_commission
                trades.append(
                    Trade(
                        date=d,
                        action="sell",
                        price=price,
                        shares=position,
                        commission=sell_commission,
                        value=sell_value,
                    )
                )
                position = 0

        # Force-close on the last bar.
        if position > 0 and prices:
            last = prices[-1]
            sell_value = position * last["close"]
            sell_commission = sell_value * (config.commission + config.tax)
            trades.append(
                Trade(
                    date=last["date"],
                    action="sell",
                    price=last["close"],
                    shares=position,
                    commission=sell_commission,
                    value=sell_value,
                )
            )

        return trades

    # ------------------------------------------------------------------
    # Equity curve
    # ------------------------------------------------------------------

    def _build_equity_curve(
        self,
        prices: list[dict],
        trades: list[Trade],
        config: BacktestConfig,
    ) -> list[dict]:
        """Build a daily equity curve from the trade list.

        For each day, equity = cash + (shares_held × current_close).

        Args:
            prices: Filtered OHLCV list for the backtest window.
            trades: Trade list produced by a strategy method.
            config: BacktestConfig (used for initial_capital).

        Returns:
            List of ``{"date": str, "value": float}`` dicts.
        """
        cash = config.initial_capital
        position = 0

        # Build a lookup: date → list of trades on that date.
        trade_by_date: dict[str, list[Trade]] = {}
        for t in trades:
            trade_by_date.setdefault(t.date, []).append(t)

        curve: list[dict] = []
        for bar in prices:
            d = bar["date"]
            # Apply all trades on this day before snapshotting equity.
            for t in trade_by_date.get(d, []):
                if t.action == "buy":
                    cash -= t.value + t.commission
                    position += t.shares
                else:  # sell
                    cash += t.value - t.commission
                    position -= t.shares

            equity = cash + position * bar["close"]
            curve.append({"date": d, "value": float(equity)})

        return curve

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def _calculate_metrics(
        self,
        trades: list[Trade],
        equity_curve: list[dict],
        config: BacktestConfig,
    ) -> dict:
        """Calculate performance metrics from trades and equity curve.

        Returns a dict compatible with ``BacktestResult`` field names
        (excluding ``config``, ``trades``, ``equity_curve``).
        """
        if not equity_curve:
            return self._zero_metrics(config.initial_capital)

        initial = config.initial_capital
        final = equity_curve[-1]["value"]

        total_return = (final - initial) / initial * 100.0

        # CAGR
        years = self._years_between(config.start_date, config.end_date)
        if years > 0 and final > 0:
            annualized_return = ((final / initial) ** (1.0 / years) - 1.0) * 100.0
        else:
            annualized_return = 0.0

        max_drawdown = self._calculate_max_drawdown(equity_curve)
        sharpe_ratio = self._calculate_sharpe(equity_curve)

        # Win rate: count completed round-trips (consecutive buy+sell pairs).
        win_rate, total_round_trips = self._win_rate(trades)

        return {
            "total_return": round(total_return, 4),
            "annualized_return": round(annualized_return, 4),
            "max_drawdown": round(max_drawdown, 4),
            "sharpe_ratio": round(sharpe_ratio, 4),
            "win_rate": round(win_rate, 4),
            "total_trades": total_round_trips,
            "final_value": round(final, 2),
        }

    def _calculate_sharpe(
        self,
        equity_curve: list[dict],
        risk_free_rate: float = 0.02,
    ) -> float:
        """Annualised Sharpe ratio.

        Daily returns are computed from the equity curve.  The risk-free rate
        is converted to a daily rate (÷ 252).  Annualisation uses √252.

        Returns 0.0 if there are fewer than two data points or zero variance.
        """
        if len(equity_curve) < 2:
            return 0.0

        values = np.array([e["value"] for e in equity_curve], dtype=np.float64)
        daily_returns = np.diff(values) / values[:-1]

        if len(daily_returns) == 0:
            return 0.0

        daily_rf = risk_free_rate / 252.0
        excess = daily_returns - daily_rf
        std = excess.std(ddof=1)

        if std == 0.0:
            return 0.0

        return float(excess.mean() / std * math.sqrt(252))

    def _calculate_max_drawdown(self, equity_curve: list[dict]) -> float:
        """Maximum peak-to-trough drawdown as a negative percentage.

        Returns 0.0 for an empty or single-point curve.
        """
        if len(equity_curve) < 2:
            return 0.0

        values = np.array([e["value"] for e in equity_curve], dtype=np.float64)
        peak = np.maximum.accumulate(values)
        drawdown = (values - peak) / peak * 100.0
        return float(drawdown.min())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _price_on_date(prices: list[dict], date: str) -> float | None:
        """Binary-search (or linear scan) for the close price on a given date."""
        for p in prices:
            if p["date"] == date:
                return p["close"]
        return None

    @staticmethod
    def _date_range_to_period(start_date: str, end_date: str) -> str:
        """Convert a date range to the nearest yfinance period string."""
        try:
            delta = datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)
            days = delta.days
        except ValueError:
            return "5y"

        if days <= 30:
            return "1mo"
        if days <= 90:
            return "3mo"
        if days <= 180:
            return "6mo"
        if days <= 365:
            return "1y"
        if days <= 730:
            return "2y"
        if days <= 1825:
            return "5y"
        return "10y"

    @staticmethod
    def _years_between(start_date: str, end_date: str) -> float:
        """Return fractional years between two ISO-8601 date strings."""
        try:
            delta = datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)
            return max(delta.days / 365.25, 1e-9)
        except ValueError:
            return 1.0

    @staticmethod
    def _win_rate(trades: list[Trade]) -> tuple[float, int]:
        """Calculate win rate from paired buy/sell trades.

        Returns ``(win_rate_pct, num_round_trips)``.  A round-trip is
        profitable when the net proceeds of the sell exceed the cost of the buy
        (after commissions on both sides).
        """
        buys: list[Trade] = [t for t in trades if t.action == "buy"]
        sells: list[Trade] = [t for t in trades if t.action == "sell"]
        pairs = min(len(buys), len(sells))
        if pairs == 0:
            return 0.0, 0

        wins = 0
        for buy, sell in zip(buys[:pairs], sells[:pairs]):
            buy_cost = buy.value + buy.commission
            sell_proceeds = sell.value - sell.commission
            if sell_proceeds > buy_cost:
                wins += 1

        return wins / pairs * 100.0, pairs

    @staticmethod
    def _zero_metrics(initial_capital: float) -> dict:
        return {
            "total_return": 0.0,
            "annualized_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "win_rate": 0.0,
            "total_trades": 0,
            "final_value": initial_capital,
        }

    @staticmethod
    def _empty_result(config: BacktestConfig) -> BacktestResult:
        return BacktestResult(
            config=config,
            trades=[],
            equity_curve=[],
            total_return=0.0,
            annualized_return=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            win_rate=0.0,
            total_trades=0,
            final_value=config.initial_capital,
        )
