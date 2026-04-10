"""Alert API routes.

Endpoints
---------
POST   /api/v1/alerts              — create alert
GET    /api/v1/alerts              — list alerts (paginated, filterable)
GET    /api/v1/alerts/{id}         — get single alert
PUT    /api/v1/alerts/{id}         — update alert
DELETE /api/v1/alerts/{id}         — delete alert
GET    /api/v1/alerts/{id}/check   — manually evaluate alert right now
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_alert_evaluator
from app.db.session import get_db
from app.models.alert import Alert
from app.schemas.alert import (
    AlertCheckResponse,
    AlertCreate,
    AlertDeleteResponse,
    AlertDetailResponse,
    AlertListResponse,
    AlertResponse,
    AlertUpdate,
)
from app.schemas.common import MetaResponse
from app.services.alert_evaluator import AlertEvaluationError, AlertEvaluator

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _alert_to_response(alert: Alert) -> AlertResponse:
    """Convert an Alert ORM instance to the response schema."""
    return AlertResponse.model_validate(alert)


async def _get_alert_or_404(alert_id: int, db: AsyncSession) -> Alert:
    """Fetch an alert by primary key or raise HTTP 404."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": f"Alert {alert_id} not found.",
                "code": "ALERT_NOT_FOUND",
            },
        )
    return alert


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", response_model=AlertDetailResponse, status_code=201)
async def create_alert(
    body: AlertCreate,
    db: AsyncSession = Depends(get_db),
) -> AlertDetailResponse:
    """Create a new price or indicator alert."""
    alert = Alert(
        symbol=body.symbol,
        alert_type=body.alert_type,
        condition=body.condition,
        is_active=True,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    logger.info(
        "Alert created: id=%d symbol=%s type=%s",
        alert.id,
        alert.symbol,
        alert.alert_type,
    )
    return AlertDetailResponse(data=_alert_to_response(alert))


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    symbol: str | None = Query(None, description="Filter by ticker symbol"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> AlertListResponse:
    """Return a paginated list of alerts with optional filters."""
    base_query = select(Alert)

    if symbol is not None:
        base_query = base_query.where(Alert.symbol == symbol.strip().upper())
    if is_active is not None:
        base_query = base_query.where(Alert.is_active == is_active)

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    offset = (page - 1) * limit
    result = await db.execute(
        base_query.order_by(Alert.id.desc()).offset(offset).limit(limit)
    )
    alerts = result.scalars().all()

    return AlertListResponse(
        data=[_alert_to_response(a) for a in alerts],
        meta=MetaResponse(total=total, page=page, limit=limit),
    )


@router.get("/{alert_id}", response_model=AlertDetailResponse)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
) -> AlertDetailResponse:
    """Return a single alert by ID.

    Raises HTTP 404 when the alert does not exist.
    """
    alert = await _get_alert_or_404(alert_id, db)
    return AlertDetailResponse(data=_alert_to_response(alert))


@router.put("/{alert_id}", response_model=AlertDetailResponse)
async def update_alert(
    alert_id: int,
    body: AlertUpdate,
    db: AsyncSession = Depends(get_db),
) -> AlertDetailResponse:
    """Update an alert's active status and/or condition.

    Raises HTTP 404 when the alert does not exist.
    """
    alert = await _get_alert_or_404(alert_id, db)

    if body.is_active is not None:
        alert.is_active = body.is_active
        # When re-activating a previously triggered alert, clear the
        # triggered_at timestamp so it can fire again.
        if body.is_active and alert.triggered_at is not None:
            alert.triggered_at = None

    if body.condition is not None:
        alert.condition = body.condition

    await db.commit()
    await db.refresh(alert)

    logger.info("Alert updated: id=%d", alert.id)
    return AlertDetailResponse(data=_alert_to_response(alert))


@router.delete("/{alert_id}", response_model=AlertDeleteResponse)
async def delete_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
) -> AlertDeleteResponse:
    """Delete an alert permanently.

    Raises HTTP 404 when the alert does not exist.
    """
    alert = await _get_alert_or_404(alert_id, db)
    await db.delete(alert)
    await db.commit()

    logger.info("Alert deleted: id=%d", alert_id)
    return AlertDeleteResponse(detail=f"Alert {alert_id} deleted successfully.")


@router.get("/{alert_id}/check", response_model=AlertCheckResponse)
async def check_alert_now(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    evaluator: AlertEvaluator = Depends(get_alert_evaluator),
) -> AlertCheckResponse:
    """Manually evaluate an alert against the current market data.

    Returns ``{"triggered": bool, "current_value": float}`` without
    persisting any state change.  Useful for on-demand verification.

    Raises HTTP 404 when the alert does not exist.
    Raises HTTP 422 when the alert condition cannot be evaluated (e.g.
    missing required condition keys or no market data available).
    """
    alert = await _get_alert_or_404(alert_id, db)

    try:
        triggered, current_value = await evaluator.evaluate(alert)
    except AlertEvaluationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"detail": str(exc), "code": "ALERT_EVALUATION_ERROR"},
        ) from exc

    return AlertCheckResponse(triggered=triggered, current_value=current_value)
