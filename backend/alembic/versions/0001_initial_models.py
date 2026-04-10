"""initial models

Revision ID: 0001
Revises:
Create Date: 2026-04-09 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- stocks -----------------------------------------------------------
    op.create_table(
        "stocks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stocks_symbol"), "stocks", ["symbol"], unique=True)

    # --- daily_prices -----------------------------------------------------
    op.create_table(
        "daily_prices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stock_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("adj_close", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stock_id", "date", name="uq_daily_prices_stock_date"),
    )
    op.create_index(
        "ix_daily_prices_stock_date", "daily_prices", ["stock_id", "date"]
    )

    # --- technical_indicators ---------------------------------------------
    op.create_table(
        "technical_indicators",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stock_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("indicator_name", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "stock_id",
            "date",
            "indicator_name",
            name="uq_technical_indicators_stock_date_name",
        ),
    )
    op.create_index(
        "ix_technical_indicators_stock_date",
        "technical_indicators",
        ["stock_id", "date"],
    )

    # --- backtest_results -------------------------------------------------
    op.create_table(
        "backtest_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("strategy_name", sa.String(length=100), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("initial_capital", sa.Float(), nullable=False),
        sa.Column("final_value", sa.Float(), nullable=False),
        sa.Column("total_return", sa.Float(), nullable=False),
        sa.Column("max_drawdown", sa.Float(), nullable=False),
        sa.Column("sharpe_ratio", sa.Float(), nullable=True),
        sa.Column("trades_count", sa.Integer(), nullable=False),
        sa.Column("win_rate", sa.Float(), nullable=True),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_backtest_results_strategy_name"),
        "backtest_results",
        ["strategy_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_backtest_results_symbol"),
        "backtest_results",
        ["symbol"],
        unique=False,
    )

    # --- alerts -----------------------------------------------------------
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("alert_type", sa.String(length=30), nullable=False),
        sa.Column("condition", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("triggered_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_alerts_symbol"), "alerts", ["symbol"], unique=False
    )

    # --- portfolios -------------------------------------------------------
    op.create_table(
        "portfolios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- portfolio_holdings -----------------------------------------------
    op.create_table(
        "portfolio_holdings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("shares", sa.Float(), nullable=False),
        sa.Column("avg_cost", sa.Float(), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- watchlists -------------------------------------------------------
    op.create_table(
        "watchlists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- watchlist_items --------------------------------------------------
    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("watchlist_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(
            ["watchlist_id"], ["watchlists.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("watchlist_items")
    op.drop_table("watchlists")
    op.drop_table("portfolio_holdings")
    op.drop_table("portfolios")
    op.drop_index(op.f("ix_alerts_symbol"), table_name="alerts")
    op.drop_table("alerts")
    op.drop_index(
        op.f("ix_backtest_results_symbol"), table_name="backtest_results"
    )
    op.drop_index(
        op.f("ix_backtest_results_strategy_name"), table_name="backtest_results"
    )
    op.drop_table("backtest_results")
    op.drop_index(
        "ix_technical_indicators_stock_date", table_name="technical_indicators"
    )
    op.drop_table("technical_indicators")
    op.drop_index("ix_daily_prices_stock_date", table_name="daily_prices")
    op.drop_table("daily_prices")
    op.drop_index(op.f("ix_stocks_symbol"), table_name="stocks")
    op.drop_table("stocks")
