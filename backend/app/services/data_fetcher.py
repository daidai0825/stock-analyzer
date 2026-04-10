"""Unified data fetcher for US (yfinance) and TW (FinMind) markets."""

import asyncio
import logging
from datetime import datetime, timedelta

import httpx
import yfinance as yf
from FinMind.data import DataLoader

from app.core.config import settings

logger = logging.getLogger(__name__)

# Canonical return shape shared between US and TW fetchers.
# All price fields are plain Python floats; volume is int.
_PRICE_RECORD = dict  # {"date", "open", "high", "low", "close", "volume", "adj_close"}

# Map human-readable period strings to timedelta so we can compute start_date
# for FinMind (which uses date ranges rather than a "period" shorthand).
_PERIOD_TO_DAYS: dict[str, int] = {
    "1d": 1,
    "5d": 5,
    "1mo": 30,
    "3mo": 90,
    "6mo": 180,
    "1y": 365,
    "2y": 730,
    "5y": 1825,
    "10y": 3650,
    "ytd": 365,  # approximate; exact YTD handled separately
    "max": 365 * 30,
}


class StockDataFetcher:
    """Unified data fetcher for US (yfinance) and TW (FinMind) markets.

    Usage::

        fetcher = StockDataFetcher()
        records = await fetcher.fetch_history("AAPL", period="1y")
        records = await fetcher.fetch_history("2330", period="1y")  # TW stock
        info    = await fetcher.fetch_stock_info("AAPL")
    """

    def _is_tw_stock(self, symbol: str) -> bool:
        """Return True when *symbol* should be fetched from FinMind (Taiwan).

        A symbol is considered a TW stock when:
        - it ends with ".TW" or ".TWO" (explicit suffix), OR
        - it consists entirely of digits (純數字代號, e.g. "2330", "0050").
        """
        upper = symbol.upper()
        if upper.endswith(".TW") or upper.endswith(".TWO"):
            return True
        # Strip any explicit ".TW" variants before the digit check
        bare = upper.replace(".TWO", "").replace(".TW", "")
        return bare.isdigit()

    def _tw_bare_symbol(self, symbol: str) -> str:
        """Strip .TW / .TWO suffix to get the raw numeric code for FinMind."""
        return symbol.upper().replace(".TWO", "").replace(".TW", "")

    def _tw_yf_symbol(self, symbol: str) -> str:
        """Return the yfinance-compatible symbol for a TW stock (e.g. '2330.TW')."""
        bare = self._tw_bare_symbol(symbol)
        return f"{bare}.TW"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch_history(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[_PRICE_RECORD]:
        """Fetch historical OHLCV data.

        Auto-detects whether to use yfinance (US) or FinMind (TW) based on
        the symbol.  Returns an empty list on error rather than raising, so
        callers can decide how to handle missing data.

        Args:
            symbol:     Ticker symbol.  TW stocks can be bare digits ("2330")
                        or carry the ".TW" suffix ("2330.TW").
            period:     yfinance-style period string: "1d", "5d", "1mo", "3mo",
                        "6mo", "1y", "2y", "5y", "10y", "ytd", "max".
                        Ignored when start_date/end_date are provided.
            interval:   Data interval — only "1d" is fully supported for TW data
                        via FinMind's OHLCV endpoint.
            start_date: ISO-8601 start date ("YYYY-MM-DD").  When provided
                        together with end_date, fetches by date range instead
                        of the relative ``period``.
            end_date:   ISO-8601 end date ("YYYY-MM-DD").

        Returns:
            List of dicts with keys: date, open, high, low, close, volume,
            adj_close.  Dates are ISO-8601 strings ("YYYY-MM-DD").
        """
        try:
            if self._is_tw_stock(symbol):
                return await self._fetch_tw(symbol, period, interval, start_date, end_date)
            return await self._fetch_us(symbol, period, interval, start_date, end_date)
        except Exception as exc:
            logger.error(
                "fetch_history failed for symbol=%s period=%s: %s",
                symbol,
                period,
                exc,
                exc_info=True,
            )
            return []

    async def fetch_stock_info(self, symbol: str) -> dict:
        """Fetch stock metadata (name, industry, description).

        Returns a dict with keys: symbol, name, industry, description, market.
        Returns an empty dict on error.
        """
        try:
            if self._is_tw_stock(symbol):
                return await self._fetch_tw_info(symbol)
            return await self._fetch_us_info(symbol)
        except Exception as exc:
            logger.error(
                "fetch_stock_info failed for symbol=%s: %s", symbol, exc, exc_info=True
            )
            return {}

    # ------------------------------------------------------------------
    # US — yfinance (synchronous library, run in thread pool)
    # ------------------------------------------------------------------

    async def _fetch_us(
        self, symbol: str, period: str, interval: str,
        start_date: str | None = None, end_date: str | None = None,
    ) -> list[_PRICE_RECORD]:
        """Fetch OHLCV from yfinance, running the sync call in a thread."""
        return await asyncio.to_thread(
            self._fetch_us_sync, symbol, period, interval, start_date, end_date
        )

    def _fetch_us_sync(
        self, symbol: str, period: str, interval: str,
        start_date: str | None = None, end_date: str | None = None,
    ) -> list[_PRICE_RECORD]:
        ticker = yf.Ticker(symbol)
        if start_date and end_date:
            df = ticker.history(start=start_date, end=end_date, interval=interval, auto_adjust=False)
        else:
            df = ticker.history(period=period, interval=interval, auto_adjust=False)

        if df is None or df.empty:
            logger.warning("yfinance returned empty data for symbol=%s", symbol)
            return []

        records: list[_PRICE_RECORD] = []
        for ts, row in df.iterrows():
            # yfinance index is a DatetimeIndex; normalise to date string.
            date_str = ts.date().isoformat() if hasattr(ts, "date") else str(ts)[:10]
            records.append(
                {
                    "date": date_str,
                    "open": float(row.get("Open", 0) or 0),
                    "high": float(row.get("High", 0) or 0),
                    "low": float(row.get("Low", 0) or 0),
                    "close": float(row.get("Close", 0) or 0),
                    "volume": int(row.get("Volume", 0) or 0),
                    "adj_close": float(row.get("Adj Close", row.get("Close", 0)) or 0),
                }
            )
        return records

    async def _fetch_us_info(self, symbol: str) -> dict:
        """Fetch metadata from yfinance in a thread pool."""
        return await asyncio.to_thread(self._fetch_us_info_sync, symbol)

    def _fetch_us_info_sync(self, symbol: str) -> dict:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        return {
            "symbol": symbol.upper(),
            "name": info.get("longName") or info.get("shortName") or "",
            "industry": info.get("industry") or info.get("sector") or "",
            "description": info.get("longBusinessSummary") or "",
            "market": "US",
        }

    # ------------------------------------------------------------------
    # TW — FinMind (async HTTP via httpx)
    # ------------------------------------------------------------------

    async def _fetch_tw(
        self, symbol: str, period: str, interval: str,
        start_date: str | None = None, end_date: str | None = None,
    ) -> list[_PRICE_RECORD]:
        """Fetch OHLCV from FinMind's TaiwanStockPrice dataset.

        FinMind uses start_date / end_date rather than yfinance-style period
        strings, so we convert the period to a start date.
        """
        bare = self._tw_bare_symbol(symbol)
        if not start_date or not end_date:
            days = _PERIOD_TO_DAYS.get(period, 365)
            start_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
            end_date = datetime.today().strftime("%Y-%m-%d")

        params: dict = {
            "dataset": "TaiwanStockPrice",
            "data_id": bare,
            "start_date": start_date,
            "end_date": end_date,
        }
        if settings.finmind_token:
            params["token"] = settings.finmind_token

        url = "https://api.finmindtrade.com/api/v4/data"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "FinMind HTTP error for symbol=%s: %s %s",
                bare,
                exc.response.status_code,
                exc.response.text,
            )
            return []
        except httpx.RequestError as exc:
            logger.error("FinMind request error for symbol=%s: %s", bare, exc)
            return []

        if payload.get("status") != 200:
            logger.warning(
                "FinMind returned non-200 status for symbol=%s: %s",
                bare,
                payload.get("msg"),
            )
            return []

        rows = payload.get("data", [])
        records: list[_PRICE_RECORD] = []
        for row in rows:
            try:
                records.append(
                    {
                        "date": row["date"],
                        "open": float(row.get("open", 0) or 0),
                        "high": float(row.get("max", 0) or 0),
                        "low": float(row.get("min", 0) or 0),
                        "close": float(row.get("close", 0) or 0),
                        "volume": int(row.get("Trading_Volume", 0) or 0),
                        # FinMind's TaiwanStockPrice does not provide a
                        # separate adj_close; fall back to close.
                        "adj_close": float(row.get("close", 0) or 0),
                    }
                )
            except (KeyError, ValueError, TypeError) as exc:
                logger.debug("Skipping malformed FinMind row: %s — %s", row, exc)
        return records

    async def _fetch_tw_info(self, symbol: str) -> dict:
        """Fetch TW stock metadata from FinMind's StockInfo dataset."""
        bare = self._tw_bare_symbol(symbol)
        params: dict = {
            "dataset": "TaiwanStockInfo",
            "data_id": bare,
        }
        if settings.finmind_token:
            params["token"] = settings.finmind_token

        url = "https://api.finmindtrade.com/api/v4/data"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error("FinMind info fetch error for symbol=%s: %s", bare, exc)
            return {}

        rows = payload.get("data", [])
        if not rows:
            return {"symbol": bare, "name": "", "industry": "", "description": "", "market": "TW"}

        row = rows[0]
        return {
            "symbol": bare,
            "name": row.get("stock_name") or row.get("company_name") or "",
            "industry": row.get("industry_category") or "",
            "description": row.get("business_scope") or "",
            "market": "TW",
        }
