"""Data cleaning and bulk-persistence for stock price records."""

import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_price import DailyPrice
from app.models.stock import Stock

logger = logging.getLogger(__name__)

# Taiwan stock exchange daily price limits: ±10% from previous close.
_TW_LIMIT_UP_RATIO = 1.10
_TW_LIMIT_DOWN_RATIO = 0.90


class DataProcessor:
    """Clean and normalize stock price data, then bulk-upsert to DailyPrice.

    Typical usage::

        processor = DataProcessor()
        cleaned   = processor.clean(raw_records)
        saved     = await processor.process_and_store(symbol, raw_records, db)
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def process_and_store(
        self,
        symbol: str,
        raw_data: list[dict],
        db: AsyncSession,
    ) -> int:
        """Clean *raw_data* and bulk-upsert into the DailyPrice table.

        Args:
            symbol:   Ticker symbol used to look up (or create) the Stock row.
            raw_data: List of raw OHLCV dicts from StockDataFetcher.
            db:       Active async SQLAlchemy session.

        Returns:
            Number of rows inserted/updated.
        """
        if not raw_data:
            return 0

        is_tw = symbol.upper().endswith(".TW") or symbol.isdigit()
        cleaned = self.clean(raw_data)
        if is_tw:
            cleaned = self.normalize_tw(cleaned)

        if not cleaned:
            logger.warning("No valid records after cleaning for symbol=%s", symbol)
            return 0

        # Resolve or create the Stock row to get its primary key.
        stock_id = await self._get_or_create_stock_id(symbol, is_tw, db)

        # Build rows for bulk insert.
        rows = []
        for record in cleaned:
            raw_date = record["date"]
            if isinstance(raw_date, str):
                parsed_date = date.fromisoformat(raw_date)
            elif isinstance(raw_date, datetime):
                parsed_date = raw_date.date()
            elif isinstance(raw_date, date):
                parsed_date = raw_date
            else:
                logger.debug("Unrecognised date type %s, skipping", type(raw_date))
                continue

            rows.append(
                {
                    "stock_id": stock_id,
                    "date": parsed_date,
                    "open": record["open"],
                    "high": record["high"],
                    "low": record["low"],
                    "close": record["close"],
                    "volume": record["volume"],
                    "adj_close": record.get("adj_close"),
                }
            )

        if not rows:
            return 0

        # PostgreSQL ON CONFLICT DO UPDATE (upsert on the composite unique key).
        stmt = pg_insert(DailyPrice).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_daily_prices_stock_date",
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "adj_close": stmt.excluded.adj_close,
            },
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    # ------------------------------------------------------------------
    # Cleaning
    # ------------------------------------------------------------------

    def clean(self, data: list[dict]) -> list[dict]:
        """Remove invalid rows and validate OHLC consistency.

        Rules applied:
        - Skip rows where any of open/high/low/close is None or <= 0.
        - Skip rows where volume is negative.
        - Skip rows where high < low (clearly corrupt).
        - Skip rows where high < close or low > close (impossible OHLC).
        - Skip rows where high < open or low > open.
        - Deduplicate on date, keeping the last occurrence.
        """
        seen_dates: dict[str, dict] = {}
        skipped = 0

        for row in data:
            try:
                o = float(row["open"])
                h = float(row["high"])
                l = float(row["low"])
                c = float(row["close"])
                v = int(row["volume"])
                date_key = str(row["date"])
            except (KeyError, TypeError, ValueError):
                skipped += 1
                continue

            # Value sanity checks
            if any(val is None or val <= 0 for val in (o, h, l, c)):
                skipped += 1
                continue
            if v < 0:
                skipped += 1
                continue

            # OHLC consistency
            if h < l:
                skipped += 1
                continue
            if h < c or l > c:
                skipped += 1
                continue
            if h < o or l > o:
                skipped += 1
                continue

            seen_dates[date_key] = {
                "date": row["date"],
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": v,
                "adj_close": float(row["adj_close"]) if row.get("adj_close") else c,
            }

        if skipped:
            logger.debug("clean(): skipped %d invalid rows", skipped)

        return sorted(seen_dates.values(), key=lambda r: str(r["date"]))

    def normalize_tw(self, data: list[dict]) -> list[dict]:
        """Apply Taiwan-specific normalisations.

        - 漲跌停 ±10% validation: if a row's daily range exceeds ±10% relative
          to the *previous* close (or own open on the first row), flag it with a
          warning but keep the record — the exchange can grant intraday expansion
          on certain securities, so we log rather than drop.
        - This method is idempotent; data is assumed already cleaned.
        """
        if not data:
            return data

        normalised = []
        prev_close: float | None = None

        for row in data:
            o = row["open"]
            h = row["high"]
            l = row["low"]
            c = row["close"]

            if prev_close is not None:
                limit_up = round(prev_close * _TW_LIMIT_UP_RATIO, 2)
                limit_down = round(prev_close * _TW_LIMIT_DOWN_RATIO, 2)

                if h > limit_up * 1.01 or l < limit_down * 0.99:
                    # Allow 1% tolerance for floating-point rounding in source data.
                    logger.warning(
                        "normalize_tw: date=%s open=%.2f high=%.2f low=%.2f close=%.2f "
                        "exceeds ±10%% limit (prev_close=%.2f, up=%.2f, down=%.2f)",
                        row["date"],
                        o,
                        h,
                        l,
                        c,
                        prev_close,
                        limit_up,
                        limit_down,
                    )
                    # Keep the row but cap extremes to protect downstream calculations.
                    row = {
                        **row,
                        "high": min(h, limit_up * 1.01),
                        "low": max(l, limit_down * 0.99),
                    }

            prev_close = c
            normalised.append(row)

        return normalised

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_or_create_stock_id(
        self, symbol: str, is_tw: bool, db: AsyncSession
    ) -> int:
        """Return the Stock.id for *symbol*, inserting a stub row if absent."""
        # Normalise symbol for DB lookup
        bare = symbol.upper().replace(".TWO", "").replace(".TW", "")
        canonical = bare if is_tw else symbol.upper()

        result = await db.execute(
            select(Stock.id).where(Stock.symbol == canonical)
        )
        stock_id = result.scalar_one_or_none()

        if stock_id is None:
            stock = Stock(
                symbol=canonical,
                name=canonical,  # placeholder; fetch_stock_info can update later
                market="TW" if is_tw else "US",
            )
            db.add(stock)
            await db.flush()  # populate stock.id without committing yet
            stock_id = stock.id
            logger.info("Created stub Stock row for symbol=%s id=%d", canonical, stock_id)

        return stock_id
