"""Comprehensive stock quality scoring system (0-100).

Combines valuation, technical, and fundamental dimensions into a single
grade that reflects the overall quality of a stock at the time of scoring.

Score breakdown:
  - Valuation  :  0 – 30
  - Technical  :  0 – 40
  - Fundamental:  0 – 30

Grade mapping:
  >= 80  優質
  60-79  良好
  40-59  中性
  20-39  偏弱
  <  20  危險
"""

import asyncio
import logging
from dataclasses import dataclass, field

from app.services.data_fetcher import StockDataFetcher
from app.services.technical_analysis import TechnicalAnalyzer
from app.services.valuation import ValuationAnalyzer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ScoreResult:
    overall_score: int
    valuation_score: float
    technical_score: float
    fundamental_score: float
    grade: str
    signals: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _grade(score: int) -> str:
    if score >= 80:
        return "優質"
    if score >= 60:
        return "良好"
    if score >= 40:
        return "中性"
    if score >= 20:
        return "偏弱"
    return "危險"


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _latest_value(series: list[dict]) -> float | None:
    """Return the most recent ``value`` from a dated series list."""
    if not series:
        return None
    return series[-1]["value"]


# ---------------------------------------------------------------------------
# Scoring sub-functions (all return a score and a list of signal dicts)
# ---------------------------------------------------------------------------


def _score_valuation(val: dict) -> tuple[float, list[dict]]:
    """Score valuation metrics; max 30 points.

    Sub-components (10 pts each):
      1. P/E ratio
      2. P/B ratio
      3. Dividend yield
    """
    signals: list[dict] = []
    total = 0.0

    # --- P/E ratio (0-10) --------------------------------------------------
    pe = val.get("pe_ratio")
    if pe is None:
        signals.append({"type": "neutral", "message": "P/E 比無資料，略過估值分項"})
    elif pe <= 0:
        # Negative earnings → penalise
        total += 0.0
        signals.append({"type": "negative", "message": f"P/E 為負值 ({pe:.1f})，公司目前虧損"})
    elif pe < 15:
        total += 10.0
        signals.append({"type": "positive", "message": f"P/E ({pe:.1f}) 低於 15，估值偏低"})
    elif pe <= 25:
        pts = 10.0 - (pe - 15) * 0.5  # 10 → 5 linearly across 15-25
        total += _clamp(pts, 2.0, 10.0)
        signals.append({"type": "neutral", "message": f"P/E ({pe:.1f}) 處於合理範圍 15-25"})
    else:
        pts = max(0.0, 5.0 - (pe - 25) * 0.2)
        total += pts
        signals.append({"type": "negative", "message": f"P/E ({pe:.1f}) 高於 25，估值偏貴"})

    # --- P/B ratio (0-10) --------------------------------------------------
    pb = val.get("pb_ratio")
    if pb is None:
        signals.append({"type": "neutral", "message": "P/B 比無資料，略過估值分項"})
    elif pb <= 0:
        total += 0.0
        signals.append({"type": "negative", "message": f"P/B 為負值 ({pb:.2f})，淨值為負"})
    elif pb < 1.5:
        total += 10.0
        signals.append({"type": "positive", "message": f"P/B ({pb:.2f}) 低於 1.5，資產估值吸引"})
    elif pb <= 3.0:
        pts = 10.0 - (pb - 1.5) * (8.0 / 1.5)  # 10 → 2 across 1.5-3.0
        total += _clamp(pts, 2.0, 10.0)
        signals.append({"type": "neutral", "message": f"P/B ({pb:.2f}) 處於合理範圍 1.5-3"})
    else:
        pts = max(0.0, 2.0 - (pb - 3.0) * 0.4)
        total += pts
        signals.append({"type": "negative", "message": f"P/B ({pb:.2f}) 高於 3，資產溢價明顯"})

    # --- Dividend yield (0-10) ---------------------------------------------
    dy = val.get("dividend_yield")
    if dy is None:
        signals.append({"type": "neutral", "message": "股息殖利率無資料，略過估值分項"})
    else:
        # yfinance expresses yield as decimal (0.03 = 3%); FinMind computes
        # cash_div / price which is also a decimal.  Normalise to percent if
        # the raw value looks like a fraction < 1.
        dy_pct = dy * 100 if dy < 1.0 else dy
        if dy_pct >= 3.0:
            total += 10.0
            signals.append(
                {"type": "positive", "message": f"股息殖利率 ({dy_pct:.2f}%) 高於 3%，配息豐厚"}
            )
        elif dy_pct >= 1.0:
            pts = 2.0 + (dy_pct - 1.0) * (8.0 / 2.0)  # 2 → 10 across 1-3%
            total += _clamp(pts, 2.0, 10.0)
            signals.append(
                {"type": "neutral", "message": f"股息殖利率 ({dy_pct:.2f}%) 介於 1%-3%"}
            )
        else:
            total += min(2.0, dy_pct * 2.0)
            signals.append(
                {"type": "negative", "message": f"股息殖利率 ({dy_pct:.2f}%) 低於 1%，配息偏少"}
            )

    return total, signals


def _score_technical(prices: list[dict], indicators: dict) -> tuple[float, list[dict]]:
    """Score technical indicators; max 40 points.

    Sub-components (10 pts each):
      1. RSI(14) position
      2. Price vs SMA200
      3. MACD direction
      4. Bollinger Band position
    """
    signals: list[dict] = []
    total = 0.0

    if not prices:
        signals.append({"type": "neutral", "message": "無價格資料，技術面分項略過"})
        return total, signals

    latest_close = prices[-1]["close"]

    # --- RSI(14) position (0-10) -------------------------------------------
    rsi_series: list[dict] = indicators.get("rsi_14", [])
    rsi_val = _latest_value(rsi_series)
    if rsi_val is None:
        signals.append({"type": "neutral", "message": "RSI(14) 無資料"})
    elif 30.0 <= rsi_val <= 70.0:
        total += 10.0
        signals.append({"type": "positive", "message": f"RSI ({rsi_val:.1f}) 處於正常範圍 30-70"})
    elif rsi_val > 70.0:
        # Overbought: scale 0-5 as RSI goes from 70 to 100
        penalty = (rsi_val - 70.0) / 30.0 * 10.0
        pts = max(0.0, 10.0 - penalty)
        total += pts
        signals.append({"type": "negative", "message": f"RSI ({rsi_val:.1f}) 超買，注意回檔風險"})
    else:
        # Oversold: scale 0-5 as RSI goes from 30 to 0
        penalty = (30.0 - rsi_val) / 30.0 * 10.0
        pts = max(0.0, 10.0 - penalty)
        total += pts
        signals.append({"type": "negative", "message": f"RSI ({rsi_val:.1f}) 超賣，短期弱勢"})

    # --- Price vs SMA200 (0-10) -------------------------------------------
    # Use SMA50 as proxy when there is not enough data for SMA200.
    sma200_series: list[dict] = indicators.get("sma_200", [])
    if not sma200_series:
        sma200_series = indicators.get("sma_50", [])
        label = "SMA50（資料不足，以 SMA50 替代）"
    else:
        label = "SMA200"

    sma200_val = _latest_value(sma200_series)
    if sma200_val is None:
        signals.append({"type": "neutral", "message": f"{label} 無資料，略過趨勢評分"})
    elif latest_close > sma200_val:
        total += 10.0
        signals.append(
            {
                "type": "positive",
                "message": f"股價 ({latest_close:.2f}) 位於 {label} ({sma200_val:.2f}) 之上，上升趨勢",
            }
        )
    else:
        pct_below = (sma200_val - latest_close) / sma200_val * 100
        pts = max(0.0, 10.0 - pct_below * 0.5)
        total += pts
        signals.append(
            {
                "type": "negative",
                "message": f"股價位於 {label} 之下，偏離 {pct_below:.1f}%，下降趨勢",
            }
        )

    # --- MACD direction (0-10) --------------------------------------------
    macd_data: dict = indicators.get("macd", {})
    macd_series: list[dict] = macd_data.get("macd", [])
    signal_series: list[dict] = macd_data.get("signal", [])
    macd_val = _latest_value(macd_series)
    signal_val = _latest_value(signal_series)
    if macd_val is None or signal_val is None:
        signals.append({"type": "neutral", "message": "MACD 無資料，略過動能評分"})
    elif macd_val > signal_val:
        total += 10.0
        signals.append(
            {
                "type": "positive",
                "message": f"MACD ({macd_val:.3f}) > Signal ({signal_val:.3f})，多頭動能",
            }
        )
    else:
        gap = abs(macd_val - signal_val)
        # Soft penalty proportional to the gap relative to the signal magnitude
        ref = max(abs(signal_val), 1e-6)
        penalty = min(10.0, gap / ref * 5.0)
        pts = max(0.0, 10.0 - penalty)
        total += pts
        signals.append(
            {
                "type": "negative",
                "message": f"MACD ({macd_val:.3f}) < Signal ({signal_val:.3f})，空頭動能",
            }
        )

    # --- Bollinger Band position (0-10) -----------------------------------
    bb_data: dict = indicators.get("bollinger_bands", {})
    upper_series: list[dict] = bb_data.get("upper", [])
    middle_series: list[dict] = bb_data.get("middle", [])
    lower_series: list[dict] = bb_data.get("lower", [])
    upper_val = _latest_value(upper_series)
    middle_val = _latest_value(middle_series)
    lower_val = _latest_value(lower_series)

    if upper_val is None or middle_val is None or lower_val is None:
        signals.append({"type": "neutral", "message": "布林通道無資料，略過波動評分"})
    else:
        band_width = upper_val - lower_val
        if band_width <= 0:
            signals.append({"type": "neutral", "message": "布林通道寬度為零，略過波動評分"})
        else:
            # Normalise position within band: 0=lower, 0.5=middle, 1=upper
            position = (latest_close - lower_val) / band_width
            # Maximum score when price is near the middle (position ~0.5)
            distance_from_middle = abs(position - 0.5)  # 0 = perfect, 0.5 = at band
            pts = max(0.0, 10.0 - distance_from_middle * 20.0)
            total += pts
            if position > 0.9:
                signals.append(
                    {"type": "negative", "message": f"股價接近布林上軌，超買跡象 (位置 {position:.2f})"}
                )
            elif position < 0.1:
                signals.append(
                    {"type": "negative", "message": f"股價接近布林下軌，超賣跡象 (位置 {position:.2f})"}
                )
            else:
                signals.append(
                    {
                        "type": "positive" if distance_from_middle < 0.2 else "neutral",
                        "message": f"股價位於布林通道中軌附近 (位置 {position:.2f})",
                    }
                )

    return total, signals


def _score_fundamental(val: dict) -> tuple[float, list[dict]]:
    """Score fundamental metrics; max 30 points.

    Sub-components (10 pts each):
      1. Profit margin
      2. EPS direction
      3. Revenue presence
    """
    signals: list[dict] = []
    total = 0.0

    # --- Profit margin (0-10) ---------------------------------------------
    pm = val.get("profit_margin")
    if pm is None:
        signals.append({"type": "neutral", "message": "利潤率無資料，略過基本面分項"})
    else:
        # May be expressed as decimal (0.15) or percent (15); normalise.
        pm_pct = pm * 100 if abs(pm) <= 1.0 else pm
        if pm_pct >= 15.0:
            total += 10.0
            signals.append(
                {"type": "positive", "message": f"利潤率 ({pm_pct:.1f}%) 高於 15%，盈利能力強"}
            )
        elif pm_pct >= 5.0:
            pts = 2.0 + (pm_pct - 5.0) * (8.0 / 10.0)  # 2 → 10 across 5-15%
            total += _clamp(pts, 2.0, 10.0)
            signals.append(
                {"type": "neutral", "message": f"利潤率 ({pm_pct:.1f}%) 介於 5%-15%，表現普通"}
            )
        elif pm_pct >= 0.0:
            total += min(2.0, pm_pct * 0.4)
            signals.append(
                {"type": "negative", "message": f"利潤率 ({pm_pct:.1f}%) 低於 5%，獲利空間薄"}
            )
        else:
            total += 0.0
            signals.append(
                {"type": "negative", "message": f"利潤率為負 ({pm_pct:.1f}%)，目前虧損"}
            )

    # --- EPS direction (0-10) --------------------------------------------
    eps = val.get("eps")
    if eps is None:
        signals.append({"type": "neutral", "message": "EPS 無資料，略過基本面分項"})
    elif eps > 0:
        # Logarithmic scale: EPS=0.01 → ~0 pts, EPS=10 → ~10 pts
        import math

        pts = min(10.0, max(0.0, math.log10(eps + 0.1) * 5.0 + 5.0))
        total += pts
        signals.append({"type": "positive", "message": f"EPS 為正 ({eps:.2f})，公司獲利中"})
    else:
        total += 0.0
        signals.append({"type": "negative", "message": f"EPS 為負或零 ({eps:.2f})，公司虧損"})

    # --- Revenue presence (0-10) -----------------------------------------
    revenue = val.get("revenue")
    if revenue is None:
        signals.append({"type": "neutral", "message": "營收無資料，略過基本面分項"})
    elif revenue > 0:
        # Give full baseline score for having revenue; treat it as a qualifier.
        total += 10.0
        signals.append({"type": "positive", "message": "有營收數據，業務運作正常"})
    else:
        total += 0.0
        signals.append({"type": "negative", "message": "營收為零或負，業務異常"})

    return total, signals


# ---------------------------------------------------------------------------
# Main scorer class
# ---------------------------------------------------------------------------


class StockScorer:
    """Compute a comprehensive 0-100 quality score for a stock.

    Combines valuation (30 pts), technical (40 pts), and fundamental (30 pts)
    dimensions into a single grade.

    Usage::

        scorer = StockScorer()
        result = await scorer.score("AAPL")
        print(result.overall_score, result.grade)
    """

    def __init__(self) -> None:
        self._fetcher = StockDataFetcher()
        self._analyzer = TechnicalAnalyzer()
        self._valuation = ValuationAnalyzer(self._fetcher)

    async def score(self, symbol: str) -> ScoreResult:
        """Compute the quality score for *symbol*.

        Fetches price history, technical indicators, and valuation metrics
        concurrently, then aggregates sub-scores into the final result.

        Args:
            symbol: Ticker symbol (e.g. ``"AAPL"``, ``"2330"``).

        Returns:
            :class:`ScoreResult` with overall_score, sub-scores, grade, and
            a list of human-readable signal messages.
        """
        try:
            # Fetch data concurrently to minimise latency.
            prices_task = asyncio.create_task(
                self._fetcher.fetch_history(symbol, period="1y")
            )
            valuation_task = asyncio.create_task(
                self._valuation.get_valuation(symbol)
            )

            prices, valuation = await asyncio.gather(
                prices_task, valuation_task, return_exceptions=True
            )

            if isinstance(prices, Exception):
                logger.error("fetch_history error for %s: %s", symbol, prices)
                prices = []
            if isinstance(valuation, Exception):
                logger.error("get_valuation error for %s: %s", symbol, valuation)
                valuation = ValuationAnalyzer._empty_valuation()

            # Compute technical indicators from the fetched prices.
            indicators: dict = {}
            if prices:
                indicators = self._analyzer.compute_all(prices)
                # Also compute SMA200 which is not in compute_all defaults.
                indicators["sma_200"] = self._analyzer.sma(prices, period=200)

            # Score each dimension.
            val_score, val_signals = _score_valuation(valuation)
            tech_score, tech_signals = _score_technical(prices, indicators)
            fund_score, fund_signals = _score_fundamental(valuation)

            overall = int(round(_clamp(val_score + tech_score + fund_score, 0.0, 100.0)))

            return ScoreResult(
                overall_score=overall,
                valuation_score=round(val_score, 2),
                technical_score=round(tech_score, 2),
                fundamental_score=round(fund_score, 2),
                grade=_grade(overall),
                signals=val_signals + tech_signals + fund_signals,
            )

        except Exception as exc:  # noqa: BLE001
            logger.error("StockScorer.score failed for symbol=%s: %s", symbol, exc, exc_info=True)
            return ScoreResult(
                overall_score=0,
                valuation_score=0.0,
                technical_score=0.0,
                fundamental_score=0.0,
                grade="危險",
                signals=[{"type": "negative", "message": f"評分計算失敗：{exc}"}],
            )
