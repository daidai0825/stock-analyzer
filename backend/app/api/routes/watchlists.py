"""Watchlist API routes.

Endpoints
---------
POST   /api/v1/watchlists          — create watchlist
GET    /api/v1/watchlists          — list watchlists (paginated)
GET    /api/v1/watchlists/{id}     — get single watchlist with items
PUT    /api/v1/watchlists/{id}     — update watchlist name and/or items
DELETE /api/v1/watchlists/{id}     — delete watchlist
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.models.watchlist import Watchlist, WatchlistItem
from app.schemas.common import MetaResponse
from app.schemas.watchlist import (
    WatchlistCreate,
    WatchlistDeleteResponse,
    WatchlistDetailResponse,
    WatchlistItemResponse,
    WatchlistListResponse,
    WatchlistResponse,
    WatchlistUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _watchlist_to_response(wl: Watchlist) -> WatchlistResponse:
    """Convert a Watchlist ORM instance to a response schema."""
    return WatchlistResponse(
        id=wl.id,
        name=wl.name,
        items=[
            WatchlistItemResponse(id=item.id, symbol=item.symbol)
            for item in wl.items
        ],
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", response_model=WatchlistDetailResponse, status_code=201)
async def create_watchlist(
    body: WatchlistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> WatchlistDetailResponse:
    """Create a new watchlist and optionally populate it with symbols."""
    wl = Watchlist(name=body.name, user_id=current_user.id)
    for symbol in body.symbols:
        wl.items.append(WatchlistItem(symbol=symbol.upper()))

    db.add(wl)
    await db.commit()
    await db.refresh(wl)

    # Eager-load items so the response includes them.
    result = await db.execute(
        select(Watchlist)
        .options(selectinload(Watchlist.items))
        .where(Watchlist.id == wl.id)
    )
    wl = result.scalar_one()

    return WatchlistDetailResponse(data=_watchlist_to_response(wl))


@router.get("", response_model=WatchlistListResponse)
async def list_watchlists(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> WatchlistListResponse:
    """Return a paginated list of all watchlists with their items."""
    count_result = await db.execute(select(func.count(Watchlist.id)))
    total = count_result.scalar_one()

    offset = (page - 1) * limit
    result = await db.execute(
        select(Watchlist)
        .options(selectinload(Watchlist.items))
        .order_by(Watchlist.id)
        .offset(offset)
        .limit(limit)
    )
    watchlists = result.scalars().all()

    return WatchlistListResponse(
        data=[_watchlist_to_response(wl) for wl in watchlists],
        meta=MetaResponse(total=total, page=page, limit=limit),
    )


@router.get("/{watchlist_id}", response_model=WatchlistDetailResponse)
async def get_watchlist(
    watchlist_id: int,
    db: AsyncSession = Depends(get_db),
) -> WatchlistDetailResponse:
    """Return a single watchlist with all its items.

    Raises 404 when the watchlist does not exist.
    """
    result = await db.execute(
        select(Watchlist)
        .options(selectinload(Watchlist.items))
        .where(Watchlist.id == watchlist_id)
    )
    wl = result.scalar_one_or_none()

    if wl is None:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": f"Watchlist {watchlist_id} not found.",
                "code": "WATCHLIST_NOT_FOUND",
            },
        )

    return WatchlistDetailResponse(data=_watchlist_to_response(wl))


@router.put("/{watchlist_id}", response_model=WatchlistDetailResponse)
async def update_watchlist(
    watchlist_id: int,
    body: WatchlistUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> WatchlistDetailResponse:
    """Update a watchlist.

    When ``name`` is supplied the name is changed.  When ``symbols`` is
    supplied the item list is **replaced** entirely with the new symbols.
    Raises 404 when the watchlist does not exist.
    """
    result = await db.execute(
        select(Watchlist)
        .options(selectinload(Watchlist.items))
        .where(Watchlist.id == watchlist_id)
    )
    wl = result.scalar_one_or_none()

    if wl is None:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": f"Watchlist {watchlist_id} not found.",
                "code": "WATCHLIST_NOT_FOUND",
            },
        )

    if body.name is not None:
        wl.name = body.name

    if body.symbols is not None:
        # Remove all existing items and replace with the new list.
        for item in list(wl.items):
            await db.delete(item)
        await db.flush()
        for symbol in body.symbols:
            wl.items.append(WatchlistItem(symbol=symbol.upper()))

    await db.commit()

    # Re-fetch to get fresh state with items loaded.
    result = await db.execute(
        select(Watchlist)
        .options(selectinload(Watchlist.items))
        .where(Watchlist.id == watchlist_id)
    )
    wl = result.scalar_one()

    return WatchlistDetailResponse(data=_watchlist_to_response(wl))


@router.delete("/{watchlist_id}", response_model=WatchlistDeleteResponse)
async def delete_watchlist(
    watchlist_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> WatchlistDeleteResponse:
    """Delete a watchlist and all its items.

    Raises 404 when the watchlist does not exist.
    """
    result = await db.execute(select(Watchlist).where(Watchlist.id == watchlist_id))
    wl = result.scalar_one_or_none()

    if wl is None:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": f"Watchlist {watchlist_id} not found.",
                "code": "WATCHLIST_NOT_FOUND",
            },
        )

    await db.delete(wl)
    await db.commit()

    return WatchlistDeleteResponse(
        detail=f"Watchlist {watchlist_id} deleted successfully."
    )
