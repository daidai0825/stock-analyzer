"""Stock screener API route.

Endpoints
---------
POST /api/v1/screener  — screen stocks by multi-condition criteria
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_screener
from app.db.session import get_db
from app.schemas.common import MetaResponse
from app.schemas.screener import (
    ScreenerRequest,
    ScreenerResponse,
    ScreenerResultItem,
)
from app.services.screener import StockScreener

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=ScreenerResponse)
async def screen_stocks(
    body: ScreenerRequest,
    db: AsyncSession = Depends(get_db),
    screener: StockScreener = Depends(get_screener),
) -> ScreenerResponse:
    """Screen stocks in the given market that satisfy ALL supplied conditions.

    Conditions are evaluated against the most recent indicator values
    computed from 6 months of daily price history.  Only symbols present
    in the database are considered (the universe is loaded from the
    ``stocks`` table filtered by ``market``).

    Example request body::

        {
            "conditions": [
                {"indicator": "rsi", "operator": "lt", "value": 30},
                {"indicator": "price", "operator": "gt", "value": 10}
            ],
            "market": "US",
            "limit": 20
        }
    """
    conditions_raw = [
        {"indicator": c.indicator, "operator": c.operator, "value": c.value}
        for c in body.conditions
    ]

    results = await screener.screen(
        conditions=conditions_raw,
        market=body.market,
        limit=body.limit,
        db=db,
    )

    items = [
        ScreenerResultItem(symbol=r["symbol"], indicators=r["indicators"])
        for r in results
    ]

    return ScreenerResponse(
        data=items,
        meta=MetaResponse(total=len(items), page=1, limit=body.limit),
    )
