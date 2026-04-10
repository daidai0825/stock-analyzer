"""Portfolio management API routes.

Endpoints
---------
POST   /api/v1/portfolios                               — create portfolio
GET    /api/v1/portfolios                               — list portfolios (paginated)
GET    /api/v1/portfolios/{id}                          — get portfolio with holdings
POST   /api/v1/portfolios/{id}/holdings                 — add holding
DELETE /api/v1/portfolios/{id}/holdings/{holding_id}    — remove holding
DELETE /api/v1/portfolios/{id}                          — delete portfolio
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.portfolio import Portfolio, PortfolioHolding
from app.models.user import User
from app.schemas.common import MetaResponse
from app.schemas.portfolio import (
    HoldingDeleteResponse,
    PortfolioCreate,
    PortfolioDeleteResponse,
    PortfolioDetailResponse,
    PortfolioHoldingAdd,
    PortfolioHoldingResponse,
    PortfolioListResponse,
    PortfolioResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _portfolio_to_response(portfolio: Portfolio) -> PortfolioResponse:
    """Convert a Portfolio ORM instance to a response schema."""
    return PortfolioResponse(
        id=portfolio.id,
        name=portfolio.name,
        created_at=portfolio.created_at,
        holdings=[
            PortfolioHoldingResponse(
                id=h.id,
                symbol=h.symbol,
                shares=h.shares,
                avg_cost=h.avg_cost,
                added_at=h.added_at,
            )
            for h in portfolio.holdings
        ],
    )


async def _get_portfolio_or_404(
    portfolio_id: int, db: AsyncSession
) -> Portfolio:
    """Load a Portfolio with holdings or raise HTTP 404."""
    result = await db.execute(
        select(Portfolio)
        .options(selectinload(Portfolio.holdings))
        .where(Portfolio.id == portfolio_id)
    )
    portfolio = result.scalar_one_or_none()
    if portfolio is None:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": f"Portfolio {portfolio_id} not found.",
                "code": "PORTFOLIO_NOT_FOUND",
            },
        )
    return portfolio


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", response_model=PortfolioDetailResponse, status_code=201)
async def create_portfolio(
    body: PortfolioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PortfolioDetailResponse:
    """Create an empty portfolio."""
    portfolio = Portfolio(name=body.name, user_id=current_user.id)
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)

    # Re-fetch with holdings relationship loaded (empty at creation).
    result = await db.execute(
        select(Portfolio)
        .options(selectinload(Portfolio.holdings))
        .where(Portfolio.id == portfolio.id)
    )
    portfolio = result.scalar_one()

    return PortfolioDetailResponse(data=_portfolio_to_response(portfolio))


@router.get("", response_model=PortfolioListResponse)
async def list_portfolios(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> PortfolioListResponse:
    """Return a paginated list of all portfolios with their holdings."""
    count_result = await db.execute(select(func.count(Portfolio.id)))
    total = count_result.scalar_one()

    offset = (page - 1) * limit
    result = await db.execute(
        select(Portfolio)
        .options(selectinload(Portfolio.holdings))
        .order_by(Portfolio.id)
        .offset(offset)
        .limit(limit)
    )
    portfolios = result.scalars().all()

    return PortfolioListResponse(
        data=[_portfolio_to_response(p) for p in portfolios],
        meta=MetaResponse(total=total, page=page, limit=limit),
    )


@router.get("/{portfolio_id}", response_model=PortfolioDetailResponse)
async def get_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
) -> PortfolioDetailResponse:
    """Return a single portfolio with all its holdings.

    Raises 404 when the portfolio does not exist.
    """
    portfolio = await _get_portfolio_or_404(portfolio_id, db)
    return PortfolioDetailResponse(data=_portfolio_to_response(portfolio))


@router.post(
    "/{portfolio_id}/holdings",
    response_model=PortfolioDetailResponse,
    status_code=201,
)
async def add_holding(
    portfolio_id: int,
    body: PortfolioHoldingAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PortfolioDetailResponse:
    """Add a holding to a portfolio.

    Raises 404 when the portfolio does not exist.
    """
    portfolio = await _get_portfolio_or_404(portfolio_id, db)

    holding = PortfolioHolding(
        portfolio_id=portfolio.id,
        symbol=body.symbol.upper(),
        shares=body.shares,
        avg_cost=body.avg_cost,
    )
    db.add(holding)
    await db.commit()

    # Re-fetch to include the new holding.
    portfolio = await _get_portfolio_or_404(portfolio_id, db)
    return PortfolioDetailResponse(data=_portfolio_to_response(portfolio))


@router.delete(
    "/{portfolio_id}/holdings/{holding_id}",
    response_model=HoldingDeleteResponse,
)
async def remove_holding(
    portfolio_id: int,
    holding_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> HoldingDeleteResponse:
    """Remove a specific holding from a portfolio.

    Raises 404 when the portfolio or the holding does not exist, or when
    the holding does not belong to the given portfolio.
    """
    # Verify the portfolio exists first.
    await _get_portfolio_or_404(portfolio_id, db)

    result = await db.execute(
        select(PortfolioHolding).where(
            PortfolioHolding.id == holding_id,
            PortfolioHolding.portfolio_id == portfolio_id,
        )
    )
    holding = result.scalar_one_or_none()

    if holding is None:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": f"Holding {holding_id} not found in portfolio {portfolio_id}.",
                "code": "HOLDING_NOT_FOUND",
            },
        )

    await db.delete(holding)
    await db.commit()

    return HoldingDeleteResponse(
        detail=f"Holding {holding_id} removed from portfolio {portfolio_id}."
    )


@router.delete("/{portfolio_id}", response_model=PortfolioDeleteResponse)
async def delete_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PortfolioDeleteResponse:
    """Delete a portfolio and all its holdings.

    Raises 404 when the portfolio does not exist.
    """
    portfolio = await _get_portfolio_or_404(portfolio_id, db)
    await db.delete(portfolio)
    await db.commit()

    return PortfolioDeleteResponse(
        detail=f"Portfolio {portfolio_id} deleted successfully."
    )
