"""Pydantic schemas for portfolio endpoints."""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import MetaResponse


class PortfolioCreate(BaseModel):
    """Request body for creating a portfolio."""

    name: str


class PortfolioHoldingAdd(BaseModel):
    """Request body for adding a holding to a portfolio."""

    symbol: str
    shares: float
    avg_cost: float


class PortfolioHoldingResponse(BaseModel):
    """A single portfolio holding."""

    id: int
    symbol: str
    shares: float
    avg_cost: float
    added_at: datetime

    model_config = {"from_attributes": True}


class PortfolioResponse(BaseModel):
    """Full portfolio with all holdings."""

    id: int
    name: str
    created_at: datetime
    holdings: list[PortfolioHoldingResponse]

    model_config = {"from_attributes": True}


class PortfolioListResponse(BaseModel):
    """Paginated list of portfolios."""

    data: list[PortfolioResponse]
    meta: MetaResponse


class PortfolioDetailResponse(BaseModel):
    """Single portfolio detail envelope."""

    data: PortfolioResponse


class PortfolioDeleteResponse(BaseModel):
    """Confirmation response for portfolio deletion."""

    detail: str
    code: str = "PORTFOLIO_DELETED"


class HoldingDeleteResponse(BaseModel):
    """Confirmation response for holding removal."""

    detail: str
    code: str = "HOLDING_DELETED"
