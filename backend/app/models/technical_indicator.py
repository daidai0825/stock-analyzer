from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"

    __table_args__ = (
        UniqueConstraint(
            "stock_id",
            "date",
            "indicator_name",
            name="uq_technical_indicators_stock_date_name",
        ),
        Index("ix_technical_indicators_stock_date", "stock_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    # e.g. "RSI_14", "SMA_20", "EMA_50", "MACD_12_26_9"
    indicator_name: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)

    stock: Mapped["Stock"] = relationship(back_populates="technical_indicators")  # noqa: F821
