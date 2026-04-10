"""Tests for DataProcessor — DB interactions use mock AsyncSession."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.data_processor import DataProcessor, _TW_LIMIT_DOWN_RATIO, _TW_LIMIT_UP_RATIO


@pytest.fixture
def processor() -> DataProcessor:
    return DataProcessor()


def _good_record(
    date_str: str = "2024-01-02",
    o: float = 100.0,
    h: float = 105.0,
    l: float = 99.0,
    c: float = 103.0,
    v: int = 1_000_000,
    adj: float = 103.0,
) -> dict:
    return {
        "date": date_str,
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
        "adj_close": adj,
    }


# ---------------------------------------------------------------------------
# clean()
# ---------------------------------------------------------------------------


class TestClean:
    def test_clean_valid_records_pass_through(self, processor):
        records = [_good_record("2024-01-02"), _good_record("2024-01-03", o=101)]
        result = processor.clean(records)
        assert len(result) == 2

    def test_clean_removes_none_price(self, processor):
        bad = {**_good_record(), "open": None}
        result = processor.clean([bad])
        assert result == []

    def test_clean_removes_zero_price(self, processor):
        bad = {**_good_record(), "close": 0}
        result = processor.clean([bad])
        assert result == []

    def test_clean_removes_negative_volume(self, processor):
        bad = {**_good_record(), "volume": -1}
        result = processor.clean([bad])
        assert result == []

    def test_clean_removes_high_less_than_low(self, processor):
        bad = _good_record(h=98.0, l=105.0)  # h < l
        result = processor.clean([bad])
        assert result == []

    def test_clean_removes_close_above_high(self, processor):
        bad = _good_record(h=100.0, l=99.0, c=110.0, o=100.0)  # close > high
        result = processor.clean([bad])
        assert result == []

    def test_clean_removes_close_below_low(self, processor):
        bad = _good_record(h=105.0, l=99.0, c=98.0, o=100.0)  # close < low
        result = processor.clean([bad])
        assert result == []

    def test_clean_removes_open_above_high(self, processor):
        bad = _good_record(h=100.0, l=95.0, o=110.0, c=98.0)  # open > high
        result = processor.clean([bad])
        assert result == []

    def test_clean_removes_open_below_low(self, processor):
        bad = _good_record(h=105.0, l=99.0, o=90.0, c=102.0)  # open < low
        result = processor.clean([bad])
        assert result == []

    def test_clean_deduplicates_on_date_keeps_last(self, processor):
        r1 = _good_record("2024-01-02", c=100.0)
        r2 = _good_record("2024-01-02", c=110.0)
        result = processor.clean([r1, r2])
        assert len(result) == 1
        assert result[0]["close"] == 110.0

    def test_clean_sorts_by_date(self, processor):
        r1 = _good_record("2024-01-03")
        r2 = _good_record("2024-01-02")
        result = processor.clean([r1, r2])
        assert result[0]["date"] == "2024-01-02"
        assert result[1]["date"] == "2024-01-03"

    def test_clean_adj_close_falls_back_to_close(self, processor):
        r = {
            "date": "2024-01-02",
            "open": 100.0,
            "high": 105.0,
            "low": 99.0,
            "close": 103.0,
            "volume": 1_000_000,
        }  # no adj_close key
        result = processor.clean([r])
        assert result[0]["adj_close"] == 103.0

    def test_clean_skips_malformed_row(self, processor):
        malformed = {"date": "2024-01-02"}  # missing price fields
        result = processor.clean([malformed])
        assert result == []

    def test_clean_empty_input_returns_empty(self, processor):
        assert processor.clean([]) == []


# ---------------------------------------------------------------------------
# normalize_tw()
# ---------------------------------------------------------------------------


class TestNormalizeTw:
    def test_normalize_passes_normal_rows(self, processor):
        records = [
            _good_record("2024-01-02", o=100, h=105, l=99, c=103),
            _good_record("2024-01-03", o=103, h=108, l=101, c=106),
        ]
        cleaned = processor.clean(records)
        result = processor.normalize_tw(cleaned)
        assert len(result) == 2

    def test_normalize_caps_extreme_high(self, processor):
        """A day where high exceeds +10% of prev_close should be capped."""
        records = [
            _good_record("2024-01-02", o=100, h=105, l=99, c=100),
            # Next day high = 200 — clearly > 110% of 100
            _good_record("2024-01-03", o=101, h=200, l=100, c=110),
        ]
        cleaned = processor.clean(records)
        result = processor.normalize_tw(cleaned)
        limit_up = round(100 * _TW_LIMIT_UP_RATIO, 2) * 1.01
        assert result[1]["high"] <= limit_up

    def test_normalize_caps_extreme_low(self, processor):
        """A day where low goes below -10% of prev_close should be capped."""
        records = [
            _good_record("2024-01-02", o=100, h=105, l=99, c=100),
            # Next day low = 5 — clearly < 90% of 100
            _good_record("2024-01-03", o=91, h=92, l=5, c=90),
        ]
        cleaned = processor.clean(records)
        result = processor.normalize_tw(cleaned)
        limit_down = round(100 * _TW_LIMIT_DOWN_RATIO, 2) * 0.99
        assert result[1]["low"] >= limit_down

    def test_normalize_empty_input_returns_empty(self, processor):
        assert processor.normalize_tw([]) == []

    def test_normalize_single_row_no_crash(self, processor):
        cleaned = processor.clean([_good_record()])
        result = processor.normalize_tw(cleaned)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# process_and_store() — DB interaction mocked
# ---------------------------------------------------------------------------


class TestProcessAndStore:
    async def test_process_and_store_returns_rowcount(self, processor):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()

        # Patch _get_or_create_stock_id to skip DB lookup
        with patch.object(processor, "_get_or_create_stock_id", return_value=1):
            count = await processor.process_and_store(
                "AAPL",
                [_good_record("2024-01-02"), _good_record("2024-01-03", o=101)],
                mock_db,
            )

        assert count == 2

    async def test_process_and_store_empty_returns_zero(self, processor):
        mock_db = AsyncMock()
        count = await processor.process_and_store("AAPL", [], mock_db)
        assert count == 0
        mock_db.execute.assert_not_called()

    async def test_process_and_store_all_bad_records_returns_zero(self, processor):
        mock_db = AsyncMock()
        bad_records = [{"date": "2024-01-02"}]  # missing price fields
        with patch.object(processor, "_get_or_create_stock_id", return_value=1):
            count = await processor.process_and_store("AAPL", bad_records, mock_db)
        assert count == 0

    async def test_process_and_store_tw_symbol_invokes_normalize(self, processor):
        """TW symbol should trigger normalize_tw path."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        records = [_good_record()]
        with patch.object(processor, "_get_or_create_stock_id", return_value=1):
            with patch.object(processor, "normalize_tw", wraps=processor.normalize_tw) as mock_norm:
                await processor.process_and_store("2330", records, mock_db)
                mock_norm.assert_called_once()

    async def test_process_and_store_accepts_date_object(self, processor):
        """Records with date as a date object (not string) should be handled."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        record = {**_good_record(), "date": date(2024, 1, 2)}
        with patch.object(processor, "_get_or_create_stock_id", return_value=1):
            count = await processor.process_and_store("AAPL", [record], mock_db)

        assert count == 1
