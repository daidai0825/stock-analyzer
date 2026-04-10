"""Pydantic schemas for alert endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.common import MetaResponse

_VALID_ALERT_TYPES = {
    "price_above",
    "price_below",
    "rsi_above",
    "rsi_below",
    "sma_cross",
    "volume_above",
}


class AlertCreate(BaseModel):
    """Request body for creating a new alert."""

    symbol: str
    alert_type: str
    condition: dict

    @field_validator("alert_type")
    @classmethod
    def validate_alert_type(cls, v: str) -> str:
        if v not in _VALID_ALERT_TYPES:
            raise ValueError(f"alert_type must be one of {_VALID_ALERT_TYPES}")
        return v

    @field_validator("symbol")
    @classmethod
    def normalise_symbol(cls, v: str) -> str:
        return v.strip().upper()


class AlertUpdate(BaseModel):
    """Request body for updating an alert (all fields optional)."""

    is_active: bool | None = None
    condition: dict | None = None


class AlertResponse(BaseModel):
    """Full alert representation returned by the API."""

    id: int
    symbol: str
    alert_type: str
    condition: dict
    is_active: bool
    triggered_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertListResponse(BaseModel):
    """Paginated list of alerts."""

    data: list[AlertResponse]
    meta: MetaResponse


class AlertDetailResponse(BaseModel):
    """Single alert detail envelope."""

    data: AlertResponse


class AlertDeleteResponse(BaseModel):
    """Confirmation response for alert deletion."""

    detail: str
    code: str = "ALERT_DELETED"


class AlertCheckResponse(BaseModel):
    """Result of an on-demand alert evaluation."""

    triggered: bool
    current_value: float
