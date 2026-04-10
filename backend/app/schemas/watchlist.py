"""Pydantic schemas for watchlist endpoints."""

from pydantic import BaseModel

from app.schemas.common import MetaResponse


class WatchlistCreate(BaseModel):
    """Request body for creating a new watchlist."""

    name: str
    symbols: list[str] = []


class WatchlistUpdate(BaseModel):
    """Request body for updating a watchlist (all fields optional)."""

    name: str | None = None
    symbols: list[str] | None = None


class WatchlistItemResponse(BaseModel):
    """A single item within a watchlist."""

    id: int
    symbol: str

    model_config = {"from_attributes": True}


class WatchlistResponse(BaseModel):
    """Full watchlist with all items."""

    id: int
    name: str
    items: list[WatchlistItemResponse]

    model_config = {"from_attributes": True}


class WatchlistListResponse(BaseModel):
    """Paginated list of watchlists."""

    data: list[WatchlistResponse]
    meta: MetaResponse


class WatchlistDetailResponse(BaseModel):
    """Single watchlist detail envelope."""

    data: WatchlistResponse


class WatchlistDeleteResponse(BaseModel):
    """Confirmation response for watchlist deletion."""

    detail: str
    code: str = "WATCHLIST_DELETED"
