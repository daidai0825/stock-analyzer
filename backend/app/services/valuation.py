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
            # Core valuation
            "pe_ratio": _safe_float(info.get("trailingPE") or info.get("forwardPE")),
            "pb_ratio": _safe_float(info.get("priceToBook")),
            "ps_ratio": _safe_float(info.get("priceToSalesTrailing12Months")),
            "dividend_yield": _safe_float(info.get("dividendYield")),
            "market_cap": _safe_float(info.get("marketCap")),
            "eps": _safe_float(info.get("trailingEps") or info.get("forwardEps")),
            "revenue": _safe_float(info.get("totalRevenue")),
            "profit_margin": _safe_float(info.get("profitMargins")),
            # 風險指標
            "beta": _safe_float(info.get("beta")),
            "fifty_two_week_high": _safe_float(info.get("fiftyTwoWeekHigh")),
            "fifty_two_week_low": _safe_float(info.get("fiftyTwoWeekLow")),
            # 財務健康
            "debt_to_equity": _safe_float(info.get("debtToEquity")),
            "current_ratio": _safe_float(info.get("currentRatio")),
            "quick_ratio": _safe_float(info.get("quickRatio")),
            # 獲利能力
            "roe": _safe_float(info.get("returnOnEquity")),
            "roa": _safe_float(info.get("returnOnAssets")),
            "operating_margin": _safe_float(info.get("operatingMargins")),
            "gross_margin": _safe_float(info.get("grossMargins")),
            "free_cash_flow": _safe_float(info.get("freeCashflow")),
            # 成長指標
            "revenue_growth": _safe_float(info.get("revenueGrowth")),
            "earnings_growth": _safe_float(info.get("earningsGrowth")),
            # 進階估值
            "peg_ratio": _safe_float(info.get("pegRatio")),
            "ev_to_ebitda": _safe_float(info.get("enterpriseToEbitda")),
            "forward_pe": _safe_float(info.get("forwardPE")),
            # 分析師
            "target_mean_price": _safe_float(info.get("targetMeanPrice")),
            "recommendation_key": info.get("recommendationKey"),
            "number_of_analysts": _safe_float(info.get("numberOfAnalystOpinions")),
            # 持股結構
            "insider_holding": _safe_float(info.get("heldPercentInsiders")),
            "institutional_holding": _safe_float(info.get("heldPercentInstitutions")),
            # 做空資料
            "short_ratio": _safe_float(info.get("shortRatio")),
            "short_percent_of_float": _safe_float(info.get("shortPercentOfFloat")),
            # 股息詳情
            "payout_ratio": _safe_float(info.get("payoutRatio")),
            "dividend_rate": _safe_float(info.get("dividendRate")),
            "five_year_avg_dividend_yield": _safe_float(
                info.get("fiveYearAvgDividendYield")
            ),
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

        # Use yfinance (via {bare}.TW) to supplement metrics that FinMind
        # does not provide.  yfinance covers TW stocks with the .TW suffix.
        yf_symbol = self.fetcher._tw_yf_symbol(symbol)
        yf_data = await asyncio.to_thread(self._get_yf_supplement_sync, yf_symbol)

        return {
            # Prefer FinMind for PE/PB (more accurate for TW), fallback to yfinance
            "pe_ratio": pe_ratio or yf_data.get("pe_ratio"),
            "pb_ratio": pb_ratio or yf_data.get("pb_ratio"),
            "ps_ratio": yf_data.get("ps_ratio"),
            "dividend_yield": div_yield or yf_data.get("dividend_yield"),
            "market_cap": market_cap or yf_data.get("market_cap"),
            "eps": eps or yf_data.get("eps"),
            "revenue": revenue or yf_data.get("revenue"),
            "profit_margin": profit_margin or yf_data.get("profit_margin"),
            # 以下全部從 yfinance 取得
            "beta": yf_data.get("beta"),
            "fifty_two_week_high": yf_data.get("fifty_two_week_high"),
            "fifty_two_week_low": yf_data.get("fifty_two_week_low"),
            "debt_to_equity": yf_data.get("debt_to_equity"),
            "current_ratio": yf_data.get("current_ratio"),
            "quick_ratio": yf_data.get("quick_ratio"),
            "roe": yf_data.get("roe"),
            "roa": yf_data.get("roa"),
            "operating_margin": yf_data.get("operating_margin"),
            "gross_margin": yf_data.get("gross_margin"),
            "free_cash_flow": yf_data.get("free_cash_flow"),
            "revenue_growth": yf_data.get("revenue_growth"),
            "earnings_growth": yf_data.get("earnings_growth"),
            "peg_ratio": yf_data.get("peg_ratio"),
            "ev_to_ebitda": yf_data.get("ev_to_ebitda"),
            "forward_pe": yf_data.get("forward_pe"),
            "target_mean_price": yf_data.get("target_mean_price"),
            "recommendation_key": yf_data.get("recommendation_key"),
            "number_of_analysts": yf_data.get("number_of_analysts"),
            "insider_holding": yf_data.get("insider_holding"),
            "institutional_holding": yf_data.get("institutional_holding"),
            "short_ratio": yf_data.get("short_ratio"),
            "short_percent_of_float": yf_data.get("short_percent_of_float"),
            "payout_ratio": yf_data.get("payout_ratio"),
            "dividend_rate": yf_data.get("dividend_rate"),
            "five_year_avg_dividend_yield": yf_data.get("five_year_avg_dividend_yield"),
        }

    def _get_yf_supplement_sync(self, yf_symbol: str) -> dict:
        """Fetch supplementary metrics from yfinance for a TW stock.

        Uses the same field mapping as ``_get_us_valuation_sync`` but is
        only called as a fallback for Taiwan stocks to fill gaps that
        FinMind does not cover (ROE, ROA, beta, analyst data, etc.).
        """
        try:
            ticker = yf.Ticker(yf_symbol)
            info: dict = ticker.info or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("yfinance supplement failed for %s: %s", yf_symbol, exc)
            return {}

        return {
            "pe_ratio": _safe_float(info.get("trailingPE") or info.get("forwardPE")),
            "pb_ratio": _safe_float(info.get("priceToBook")),
            "ps_ratio": _safe_float(info.get("priceToSalesTrailing12Months")),
            "dividend_yield": _safe_float(info.get("dividendYield")),
            "market_cap": _safe_float(info.get("marketCap")),
            "eps": _safe_float(info.get("trailingEps") or info.get("forwardEps")),
            "revenue": _safe_float(info.get("totalRevenue")),
            "profit_margin": _safe_float(info.get("profitMargins")),
            "beta": _safe_float(info.get("beta")),
            "fifty_two_week_high": _safe_float(info.get("fiftyTwoWeekHigh")),
            "fifty_two_week_low": _safe_float(info.get("fiftyTwoWeekLow")),
            "debt_to_equity": _safe_float(info.get("debtToEquity")),
            "current_ratio": _safe_float(info.get("currentRatio")),
            "quick_ratio": _safe_float(info.get("quickRatio")),
            "roe": _safe_float(info.get("returnOnEquity")),
            "roa": _safe_float(info.get("returnOnAssets")),
            "operating_margin": _safe_float(info.get("operatingMargins")),
            "gross_margin": _safe_float(info.get("grossMargins")),
            "free_cash_flow": _safe_float(info.get("freeCashflow")),
            "revenue_growth": _safe_float(info.get("revenueGrowth")),
            "earnings_growth": _safe_float(info.get("earningsGrowth")),
            "peg_ratio": _safe_float(info.get("pegRatio")),
            "ev_to_ebitda": _safe_float(info.get("enterpriseToEbitda")),
            "forward_pe": _safe_float(info.get("forwardPE")),
            "target_mean_price": _safe_float(info.get("targetMeanPrice")),
            "recommendation_key": info.get("recommendationKey"),
            "number_of_analysts": _safe_float(info.get("numberOfAnalystOpinions")),
            "insider_holding": _safe_float(info.get("heldPercentInsiders")),
            "institutional_holding": _safe_float(info.get("heldPercentInstitutions")),
            "short_ratio": _safe_float(info.get("shortRatio")),
            "short_percent_of_float": _safe_float(info.get("shortPercentOfFloat")),
            "payout_ratio": _safe_float(info.get("payoutRatio")),
            "dividend_rate": _safe_float(info.get("dividendRate")),
            "five_year_avg_dividend_yield": _safe_float(
                info.get("fiveYearAvgDividendYield")
            ),
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
            # 風險指標
            "beta": None,
            "fifty_two_week_high": None,
            "fifty_two_week_low": None,
            # 財務健康
            "debt_to_equity": None,
            "current_ratio": None,
            "quick_ratio": None,
            # 獲利能力
            "roe": None,
            "roa": None,
            "operating_margin": None,
            "gross_margin": None,
            "free_cash_flow": None,
            # 成長指標
            "revenue_growth": None,
            "earnings_growth": None,
            # 進階估值
            "peg_ratio": None,
            "ev_to_ebitda": None,
            "forward_pe": None,
            # 分析師
            "target_mean_price": None,
            "recommendation_key": None,
            "number_of_analysts": None,
            # 持股結構
            "insider_holding": None,
            "institutional_holding": None,
            # 做空資料
            "short_ratio": None,
            "short_percent_of_float": None,
            # 股息詳情
            "payout_ratio": None,
            "dividend_rate": None,
            "five_year_avg_dividend_yield": None,
        }
