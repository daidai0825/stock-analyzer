"""Fundamental valuation metrics for US and Taiwan stocks.

US data is sourced via yfinance's ``Ticker.info`` dict.
TW data is sourced via the FinMind ``TaiwanStockPER`` dataset (P/E, P/B)
and ``TaiwanStockDividend`` for dividend yield.

All methods return ``None`` for any field that cannot be resolved, so callers
can safely handle incomplete data without raising exceptions.
"""

import asyncio
import logging
from typing import Any

import httpx
import yfinance as yf

from app.core.config import settings
from app.services.data_fetcher import StockDataFetcher

logger = logging.getLogger(__name__)


def _safe_float(value: Any) -> float | None:
    """Coerce *value* to float, returning ``None`` on failure."""
    if value is None:
        return None
    try:
        f = float(value)
        return f if not (f != f) else None  # reject NaN
    except (TypeError, ValueError):
        return None


class ValuationAnalyzer:
    """Fundamental valuation metrics for US and Taiwan stocks."""

    def __init__(self, fetcher: StockDataFetcher) -> None:
        self.fetcher = fetcher

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_valuation(self, symbol: str) -> dict:
        """Get comprehensive valuation metrics for a stock.

        Auto-detects the market from the symbol (same logic as
        ``StockDataFetcher._is_tw_stock``).

        Args:
            symbol: Ticker symbol (e.g. ``"AAPL"``, ``"2330"``, ``"2330.TW"``).

        Returns:
            Dict with keys:
              ``pe_ratio``, ``pb_ratio``, ``ps_ratio``, ``dividend_yield``,
              ``market_cap``, ``eps``, ``revenue``, ``profit_margin``.
            Each value is ``float | None``.
        """
        try:
            if self.fetcher._is_tw_stock(symbol):
                return await self._get_tw_valuation(symbol)
            return await self._get_us_valuation(symbol)
        except Exception as exc:  # noqa: BLE001
            logger.error("get_valuation failed for symbol=%s: %s", symbol, exc, exc_info=True)
            return self._empty_valuation()

    # ------------------------------------------------------------------
    # US — yfinance
    # ------------------------------------------------------------------

    async def _get_us_valuation(self, symbol: str) -> dict:
        """Fetch valuation metrics from yfinance in a thread pool."""
        return await asyncio.to_thread(self._get_us_valuation_sync, symbol)

    def _get_us_valuation_sync(self, symbol: str) -> dict:
        """Synchronous yfinance fetch, intended to be run in a thread."""
        ticker = yf.Ticker(symbol)
        info: dict = ticker.info or {}

        return {
            "pe_ratio": _safe_float(info.get("trailingPE") or info.get("forwardPE")),
            "pb_ratio": _safe_float(info.get("priceToBook")),
            "ps_ratio": _safe_float(info.get("priceToSalesTrailing12Months")),
            "dividend_yield": _safe_float(info.get("dividendYield")),
            "market_cap": _safe_float(info.get("marketCap")),
            "eps": _safe_float(info.get("trailingEps") or info.get("forwardEps")),
            "revenue": _safe_float(info.get("totalRevenue")),
            "profit_margin": _safe_float(info.get("profitMargins")),
        }

    # ------------------------------------------------------------------
    # TW — FinMind
    # ------------------------------------------------------------------

    async def _get_tw_valuation(self, symbol: str) -> dict:
        """Fetch TW valuation metrics from FinMind datasets.

        Combines data from:
          - ``TaiwanStockPER`` — P/E, P/B ratios and market cap
          - ``TaiwanStockDividend`` — dividend yield
          - ``TaiwanStockFinancialStatements`` — EPS, revenue, profit margin

        Falls back to ``None`` for any metric that is unavailable.
        """
        bare = self.fetcher._tw_bare_symbol(symbol)

        # Fetch all three datasets concurrently.
        per_task = asyncio.create_task(self._finmind_latest(bare, "TaiwanStockPER"))
        div_task = asyncio.create_task(
            self._finmind_latest(bare, "TaiwanStockDividend")
        )
        fin_task = asyncio.create_task(
            self._finmind_latest(bare, "TaiwanStockFinancialStatements")
        )

        per_row, div_row, fin_row = await asyncio.gather(
            per_task, div_task, fin_task, return_exceptions=True
        )

        # Treat exceptions as empty dicts.
        if isinstance(per_row, Exception):
            logger.warning("FinMind TaiwanStockPER error for %s: %s", bare, per_row)
            per_row = {}
        if isinstance(div_row, Exception):
            logger.warning("FinMind TaiwanStockDividend error for %s: %s", bare, div_row)
            div_row = {}
        if isinstance(fin_row, Exception):
            logger.warning(
                "FinMind TaiwanStockFinancialStatements error for %s: %s", bare, fin_row
            )
            fin_row = {}

        # FinMind TaiwanStockPER fields: PER, PBR, MarketValue (億).
        pe_ratio = _safe_float(per_row.get("PER"))
        pb_ratio = _safe_float(per_row.get("PBR"))
        # MarketValue is in 億 TWD (1億 = 1e8); convert to TWD.
        market_cap_yi = _safe_float(per_row.get("MarketValue"))
        market_cap = market_cap_yi * 1e8 if market_cap_yi is not None else None

        # TaiwanStockDividend fields: CashDividend, StockDividend (per share, TWD).
        # Yield = cash dividend / close price — we use close as a rough proxy.
        # FinMind does not directly expose yield; we compute it if possible.
        cash_div = _safe_float(div_row.get("CashDividend"))
        div_yield: float | None = None
        if cash_div is not None:
            # Fetch the latest close price to approximate yield.
            try:
                prices = await self.fetcher.fetch_history(bare, period="5d")
                if prices:
                    latest_close = prices[-1]["close"]
                    if latest_close > 0:
                        div_yield = cash_div / latest_close
            except Exception as exc:  # noqa: BLE001
                logger.debug("Could not compute TW dividend yield for %s: %s", bare, exc)

        # TaiwanStockFinancialStatements relevant fields: EPS, Revenue (千元),
        # NetIncome (千元).
        eps = _safe_float(fin_row.get("EPS"))
        # Revenue in thousands TWD → convert to TWD.
        revenue_k = _safe_float(fin_row.get("Revenue"))
        revenue = revenue_k * 1_000 if revenue_k is not None else None
        # Profit margin = NetIncome / Revenue.
        net_income_k = _safe_float(fin_row.get("NetIncome"))
        profit_margin: float | None = None
        if net_income_k is not None and revenue_k and revenue_k != 0:
            profit_margin = net_income_k / revenue_k

        return {
            "pe_ratio": pe_ratio,
            "pb_ratio": pb_ratio,
            "ps_ratio": None,  # not directly available from FinMind TaiwanStockPER
            "dividend_yield": div_yield,
            "market_cap": market_cap,
            "eps": eps,
            "revenue": revenue,
            "profit_margin": profit_margin,
        }

    async def _finmind_latest(self, bare_symbol: str, dataset: str) -> dict:
        """Fetch the most recent row from a FinMind dataset for a symbol.

        Returns an empty dict if the request fails or yields no data.
        """
        from datetime import datetime, timedelta

        params: dict = {
            "dataset": dataset,
            "data_id": bare_symbol,
            "start_date": (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d"),
        }
        if settings.finmind_token:
            params["token"] = settings.finmind_token

        url = "https://api.finmindtrade.com/api/v4/data"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                payload = resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error(
                "_finmind_latest: request error dataset=%s symbol=%s: %s",
                dataset,
                bare_symbol,
                exc,
            )
            return {}

        if payload.get("status") != 200:
            logger.warning(
                "_finmind_latest: non-200 status dataset=%s symbol=%s: %s",
                dataset,
                bare_symbol,
                payload.get("msg"),
            )
            return {}

        rows = payload.get("data", [])
        if not rows:
            return {}

        # Return the last row (most recent date).
        return rows[-1]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_valuation() -> dict:
        return {
            "pe_ratio": None,
            "pb_ratio": None,
            "ps_ratio": None,
            "dividend_yield": None,
            "market_cap": None,
            "eps": None,
            "revenue": None,
            "profit_margin": None,
        }
