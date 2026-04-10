from datetime import date

from sqlalchemy import BigInteger, Date, Float, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DailyPrice(Base):
    __tablename__ = "daily_prices"

    __table_args__ = (
        UniqueConstraint("stock_id", "date", name="uq_daily_prices_stock_date"),
        Index("ix_daily_prices_stock_date", "stock_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    adj_close: Mapped[float | None] = mapped_column(Float, nullable=True)

    stock: Mapped["Stock"] = relationship(back_populates="daily_prices")  # noqa: F821
