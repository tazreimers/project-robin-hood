from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Bookmaker(CreatedAtMixin, Base):
    __tablename__ = "bookmakers"
    __table_args__ = (UniqueConstraint("api_key_name", name="uq_bookmakers_api_key_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    region: Mapped[str] = mapped_column(String(32), index=True)
    api_key_name: Mapped[str] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    markets: Mapped[list[Market]] = relationship(back_populates="bookmaker", cascade="all, delete-orphan")
    odds_snapshots: Mapped[list[OddsSnapshot]] = relationship(back_populates="bookmaker", cascade="all, delete-orphan")
    arbitrage_legs: Mapped[list[ArbitrageLeg]] = relationship(back_populates="bookmaker")


class Sport(CreatedAtMixin, Base):
    __tablename__ = "sports"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    events: Mapped[list[Event]] = relationship(back_populates="sport", cascade="all, delete-orphan")


class Event(TimestampMixin, Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(128), unique=True)
    sport_id: Mapped[int] = mapped_column(ForeignKey("sports.id", ondelete="RESTRICT"))
    home_team: Mapped[str] = mapped_column(String(255))
    away_team: Mapped[str] = mapped_column(String(255))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    normalized_event_key: Mapped[str] = mapped_column(String(512), index=True)

    sport: Mapped[Sport] = relationship(back_populates="events")
    markets: Mapped[list[Market]] = relationship(back_populates="event", cascade="all, delete-orphan")
    odds_snapshots: Mapped[list[OddsSnapshot]] = relationship(back_populates="event", cascade="all, delete-orphan")
    arbitrage_opportunities: Mapped[list[ArbitrageOpportunity]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )


class Market(TimestampMixin, Base):
    __tablename__ = "markets"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "bookmaker_id",
            "market_type",
            "line",
            "is_live",
            name="uq_markets_event_bookmaker_type_line_live",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    bookmaker_id: Mapped[int] = mapped_column(ForeignKey("bookmakers.id", ondelete="CASCADE"), index=True)
    market_type: Mapped[str] = mapped_column(String(64), index=True)
    line: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    event: Mapped[Event] = relationship(back_populates="markets")
    bookmaker: Mapped[Bookmaker] = relationship(back_populates="markets")
    outcomes: Mapped[list[Outcome]] = relationship(back_populates="market", cascade="all, delete-orphan")


class Outcome(TimestampMixin, Base):
    __tablename__ = "outcomes"
    __table_args__ = (UniqueConstraint("market_id", "outcome_name", name="uq_outcomes_market_outcome_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id", ondelete="CASCADE"))
    outcome_name: Mapped[str] = mapped_column(String(255))
    decimal_odds: Mapped[Decimal] = mapped_column(Numeric(12, 4))

    market: Mapped[Market] = relationship(back_populates="outcomes")


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    bookmaker_id: Mapped[int] = mapped_column(ForeignKey("bookmakers.id", ondelete="CASCADE"), index=True)
    market_type: Mapped[str] = mapped_column(String(64), index=True)
    line: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    outcome_name: Mapped[str] = mapped_column(String(255))
    decimal_odds: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    event: Mapped[Event] = relationship(back_populates="odds_snapshots")
    bookmaker: Mapped[Bookmaker] = relationship(back_populates="odds_snapshots")


class ArbitrageOpportunity(Base):
    __tablename__ = "arbitrage_opportunities"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    market_type: Mapped[str] = mapped_column(String(64), index=True)
    line: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    implied_probability_total: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    margin: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    total_stake: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    guaranteed_return: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    guaranteed_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(32), default="open", server_default="open")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    event: Mapped[Event] = relationship(back_populates="arbitrage_opportunities")
    legs: Mapped[list[ArbitrageLeg]] = relationship(back_populates="opportunity", cascade="all, delete-orphan")


class ArbitrageLeg(Base):
    __tablename__ = "arbitrage_legs"

    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("arbitrage_opportunities.id", ondelete="CASCADE"))
    bookmaker_id: Mapped[int] = mapped_column(ForeignKey("bookmakers.id", ondelete="CASCADE"), index=True)
    outcome_name: Mapped[str] = mapped_column(String(255))
    decimal_odds: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    stake: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    expected_return: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    opportunity: Mapped[ArbitrageOpportunity] = relationship(back_populates="legs")
    bookmaker: Mapped[Bookmaker] = relationship(back_populates="arbitrage_legs")


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", server_default="queued", index=True)
    sports_scanned: Mapped[int] = mapped_column(default=0, server_default="0")
    events_processed: Mapped[int] = mapped_column(default=0, server_default="0")
    markets_processed: Mapped[int] = mapped_column(default=0, server_default="0")
    snapshots_saved: Mapped[int] = mapped_column(default=0, server_default="0")
    opportunities_found: Mapped[int] = mapped_column(default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def scan_id(self) -> int:
        return self.id
