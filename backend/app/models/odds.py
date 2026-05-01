from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Event(TimestampMixin, Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(128), unique=True)
    sport_key: Mapped[str] = mapped_column(String(64), index=True)
    home_team: Mapped[str] = mapped_column(String(255))
    away_team: Mapped[str] = mapped_column(String(255))
    commence_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    odds_quotes: Mapped[list[OddsQuote]] = relationship(back_populates="event", cascade="all, delete-orphan")
    arbitrage_opportunities: Mapped[list[ArbitrageOpportunity]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )


class Bookmaker(TimestampMixin, Base):
    __tablename__ = "bookmakers"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(255))

    odds_quotes: Mapped[list[OddsQuote]] = relationship(back_populates="bookmaker", cascade="all, delete-orphan")


class OddsQuote(TimestampMixin, Base):
    __tablename__ = "odds_quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    bookmaker_id: Mapped[int] = mapped_column(ForeignKey("bookmakers.id", ondelete="CASCADE"))
    market_key: Mapped[str] = mapped_column(String(64), index=True)
    outcome_name: Mapped[str] = mapped_column(String(255))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    last_update: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    event: Mapped[Event] = relationship(back_populates="odds_quotes")
    bookmaker: Mapped[Bookmaker] = relationship(back_populates="odds_quotes")


class ArbitrageOpportunity(Base):
    __tablename__ = "arbitrage_opportunities"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    market_key: Mapped[str] = mapped_column(String(64))
    stake_currency: Mapped[str] = mapped_column(String(3), default="USD")
    total_implied_probability: Mapped[Decimal] = mapped_column(Numeric(10, 6))
    profit_margin: Mapped[Decimal] = mapped_column(Numeric(10, 6))
    legs: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    event: Mapped[Event] = relationship(back_populates="arbitrage_opportunities")
