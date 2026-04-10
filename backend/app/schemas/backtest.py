"""Pydantic schemas for the backtesting endpoint."""

from pydantic import BaseModel


class BacktestRequest(BaseModel):
    """Request body for running a backtest."""

    symbol: str
    strategy: str  # "buy_and_hold" | "sma_crossover" | "rsi_oversold"
    start_date: str  # ISO-8601 "YYYY-MM-DD"
    end_date: str  # ISO-8601 "YYYY-MM-DD"
    initial_capital: float = 100_000.0
    commission: float = 0.001425
    tax: float = 0.003
    params: dict = {}


class TradeResponse(BaseModel):
    """A single executed trade."""

    date: str
    action: str  # "buy" | "sell"
    price: float
    shares: int
    commission: float
    value: float


class EquityPointResponse(BaseModel):
    """A single point on the equity curve."""

    date: str
    value: float


class BacktestResultResponse(BaseModel):
    """Full backtest result including metrics, trade log and equity curve."""

    symbol: str
    strategy: str
    start_date: str
    end_date: str
    initial_capital: float
    final_value: float
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    trades: list[TradeResponse]
    equity_curve: list[EquityPointResponse]


class BacktestResponse(BaseModel):
    """Backtest endpoint envelope."""

    data: BacktestResultResponse
