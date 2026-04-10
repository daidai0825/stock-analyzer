"""Backtesting API route.

Endpoints
---------
POST /api/v1/backtest  — run a strategy backtest and return results
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_backtester
from app.db.session import get_db
from app.models.backtest_result import BacktestResult as BacktestResultModel
from app.schemas.backtest import (
    BacktestRequest,
    BacktestResponse,
    BacktestResultResponse,
    EquityPointResponse,
    TradeResponse,
)
from app.services.backtester import BacktestConfig, Backtester

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=BacktestResponse, status_code=200)
async def run_backtest(
    body: BacktestRequest,
    save: bool = False,
    db: AsyncSession = Depends(get_db),
    backtester: Backtester = Depends(get_backtester),
) -> BacktestResponse:
    """Run a strategy backtest and return performance metrics.

    Supported strategies:
    - ``buy_and_hold``  — buy on first bar, sell on last bar
    - ``sma_crossover`` — golden/death cross (params: short_period, long_period)
    - ``rsi_oversold``  — RSI mean-reversion (params: oversold, overbought, period)

    Set ``?save=true`` to persist the result to the ``backtest_results`` table.

    Example request body::

        {
            "symbol": "AAPL",
            "strategy": "sma_crossover",
            "start_date": "2022-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 100000,
            "commission": 0.001425,
            "tax": 0.0,
            "params": {"short_period": 10, "long_period": 50}
        }
    """
    config = BacktestConfig(
        symbol=body.symbol.upper(),
        strategy=body.strategy,
        start_date=body.start_date,
        end_date=body.end_date,
        initial_capital=body.initial_capital,
        commission=body.commission,
        tax=body.tax,
        params=body.params,
    )

    result = await backtester.run(config)

    # Optionally persist to the database
    if save:
        db_record = BacktestResultModel(
            strategy_name=result.config.strategy,
            symbol=result.config.symbol,
            start_date=result.config.start_date,
            end_date=result.config.end_date,
            initial_capital=result.config.initial_capital,
            final_value=result.final_value,
            total_return=result.total_return,
            max_drawdown=result.max_drawdown,
            sharpe_ratio=result.sharpe_ratio,
            trades_count=result.total_trades,
            win_rate=result.win_rate,
            params=result.config.params or None,
        )
        db.add(db_record)
        await db.commit()
        logger.info(
            "Saved backtest result id=%d symbol=%s strategy=%s",
            db_record.id,
            db_record.symbol,
            db_record.strategy_name,
        )

    response_data = BacktestResultResponse(
        symbol=result.config.symbol,
        strategy=result.config.strategy,
        start_date=result.config.start_date,
        end_date=result.config.end_date,
        initial_capital=result.config.initial_capital,
        final_value=result.final_value,
        total_return=result.total_return,
        annualized_return=result.annualized_return,
        max_drawdown=result.max_drawdown,
        sharpe_ratio=result.sharpe_ratio,
        win_rate=result.win_rate,
        total_trades=result.total_trades,
        trades=[
            TradeResponse(
                date=t.date,
                action=t.action,
                price=t.price,
                shares=t.shares,
                commission=t.commission,
                value=t.value,
            )
            for t in result.trades
        ],
        equity_curve=[
            EquityPointResponse(date=p["date"], value=p["value"])
            for p in result.equity_curve
        ],
    )

    return BacktestResponse(data=response_data)
