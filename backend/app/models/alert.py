from datetime import datetime

from sqlalchemy import Boolean, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # alert_type: "price_above", "price_below", "indicator"
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # condition stores the rule as JSON, e.g.:
    #   {"threshold": 150.0}  for price_above/below
    #   {"indicator": "RSI_14", "operator": ">", "value": 70}  for indicator
    condition: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    triggered_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
