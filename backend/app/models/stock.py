from datetime import datetime

from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    market: Mapped[str] = mapped_column(String(10))  # "US" or "TW"
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    daily_prices: Mapped[list["DailyPrice"]] = relationship(  # noqa: F821
        back_populates="stock", cascade="all, delete-orphan"
    )
    technical_indicators: Mapped[list["TechnicalIndicator"]] = relationship(  # noqa: F821
        back_populates="stock", cascade="all, delete-orphan"
    )
