"""Pydantic schemas for the stock screener endpoint."""

from pydantic import BaseModel, field_validator

from app.schemas.common import MetaResponse

_VALID_OPERATORS = {"gt", "gte", "lt", "lte", "eq", "above", "below"}


class ScreenerCondition(BaseModel):
    """A single screening condition.

    ``indicator`` — name understood by StockScreener (e.g. ``rsi``, ``sma_20``).
    ``operator``  — one of: gt, gte, lt, lte, eq, above, below.
    ``value``     — numeric threshold or a reference indicator name for cross
                    operators.
    """

    indicator: str
    operator: str
    value: float | str

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        if v not in _VALID_OPERATORS:
            raise ValueError(
                f"operator must be one of {sorted(_VALID_OPERATORS)}, got {v!r}"
            )
        return v


class ScreenerRequest(BaseModel):
    """Request body for the screener endpoint."""

    conditions: list[ScreenerCondition]
    market: str = "US"
    limit: int = 50


class ScreenerResultItem(BaseModel):
    """A single symbol that passed the screener conditions."""

    symbol: str
    indicators: dict


class ScreenerResponse(BaseModel):
    """Screener results envelope."""

    data: list[ScreenerResultItem]
    meta: MetaResponse
