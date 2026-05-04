from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ApiUsageLog,
    ArbitrageLeg,
    ArbitrageOpportunity,
    Bookmaker,
    Event,
    MarketQualityCheck,
    OddsSnapshot,
    ScanRun,
    Sport,
)


def seed_demo_data(db: Session) -> dict[str, int]:
    """Create deterministic demo odds data for local onboarding.

    The seed is idempotent for core sports, events, bookmakers, and opportunities.
    It never contacts an external provider and is safe to run without an API key.
    """

    now = datetime.now(timezone.utc).replace(microsecond=0)
    sport = get_or_create_sport(db, key="aussierules_afl", name="AFL")
    bookmakers = [
        get_or_create_bookmaker(db, name="DemoBet", api_key_name="demo_bet"),
        get_or_create_bookmaker(db, name="Local Odds", api_key_name="local_odds"),
        get_or_create_bookmaker(db, name="Harbour Sports", api_key_name="harbour_sports"),
    ]

    live_event = get_or_create_event(
        db,
        sport=sport,
        external_id="demo-afl-richmond-carlton",
        home_team="Richmond",
        away_team="Carlton",
        start_time=now + timedelta(hours=3),
    )
    stale_event = get_or_create_event(
        db,
        sport=sport,
        external_id="demo-afl-collingwood-geelong",
        home_team="Collingwood",
        away_team="Geelong",
        start_time=now + timedelta(days=1, hours=2),
    )

    add_snapshot_set(
        db,
        event=live_event,
        bookmakers=bookmakers[:2],
        captured_at=now - timedelta(seconds=20),
        prices=[
            {"Home": Decimal("2.2000"), "Away": Decimal("1.7800")},
            {"Home": Decimal("1.7600"), "Away": Decimal("2.2500")},
        ],
    )
    add_snapshot_set(
        db,
        event=stale_event,
        bookmakers=bookmakers[1:],
        captured_at=now - timedelta(minutes=12),
        prices=[
            {"Home": Decimal("2.1500"), "Away": Decimal("1.8400")},
            {"Home": Decimal("1.7800"), "Away": Decimal("2.2000")},
        ],
    )

    valid_opportunity = get_or_create_opportunity(
        db,
        event=live_event,
        implied_probability_total=Decimal("0.898990"),
        margin=Decimal("0.101010"),
        guaranteed_return=Decimal("1112.36"),
        guaranteed_profit=Decimal("112.36"),
        status="open",
        validation_status="FRESH",
        validation_reasons={"reasons": ["Demo opportunity seeded from local odds."], "odds_age_seconds": 20},
        detected_at=now - timedelta(seconds=20),
        expires_at=now + timedelta(minutes=5),
    )
    ensure_legs(
        db,
        opportunity=valid_opportunity,
        legs=[
            (bookmakers[0], "Home", Decimal("2.2000"), Decimal("505.62"), Decimal("1112.36")),
            (bookmakers[1], "Away", Decimal("2.2500"), Decimal("494.38"), Decimal("1112.36")),
        ],
    )

    stale_opportunity = get_or_create_opportunity(
        db,
        event=stale_event,
        implied_probability_total=Decimal("0.919540"),
        margin=Decimal("0.080460"),
        guaranteed_return=Decimal("1087.50"),
        guaranteed_profit=Decimal("87.50"),
        status="open",
        validation_status="STALE",
        validation_reasons={"reasons": ["Demo stale odds example."], "odds_age_seconds": 720},
        detected_at=now - timedelta(minutes=12),
        expires_at=now - timedelta(minutes=5),
    )
    ensure_legs(
        db,
        opportunity=stale_opportunity,
        legs=[
            (bookmakers[1], "Home", Decimal("2.1500"), Decimal("505.81"), Decimal("1087.50")),
            (bookmakers[2], "Away", Decimal("2.2000"), Decimal("494.19"), Decimal("1087.50")),
        ],
    )

    ensure_quality_check(
        db,
        event=live_event,
        status="VERIFIED",
        confidence_score=Decimal("0.9500"),
        reasons={"checks": ["Demo two-way market has all required outcomes."]},
        checked_at=now - timedelta(seconds=15),
    )
    ensure_quality_check(
        db,
        event=stale_event,
        status="REJECTED",
        confidence_score=Decimal("0.4000"),
        reasons={"failures": ["Demo stale market rejected because odds are too old."]},
        checked_at=now - timedelta(minutes=10),
    )

    ensure_demo_scan_run(db, now)
    ensure_demo_usage_log(db, now)
    db.flush()

    return {
        "sports": 1,
        "events": 2,
        "bookmakers": len(bookmakers),
        "opportunities": 2,
    }


def get_or_create_sport(db: Session, key: str, name: str) -> Sport:
    sport = db.scalar(select(Sport).where(Sport.key == key))
    if sport is None:
        sport = Sport(key=key, name=name, is_active=True)
        db.add(sport)
        db.flush()
    return sport


def get_or_create_bookmaker(db: Session, name: str, api_key_name: str) -> Bookmaker:
    bookmaker = db.scalar(select(Bookmaker).where(Bookmaker.api_key_name == api_key_name))
    if bookmaker is None:
        bookmaker = Bookmaker(name=name, region="au", api_key_name=api_key_name, is_active=True)
        db.add(bookmaker)
        db.flush()
    return bookmaker


def get_or_create_event(
    db: Session,
    sport: Sport,
    external_id: str,
    home_team: str,
    away_team: str,
    start_time: datetime,
) -> Event:
    event = db.scalar(select(Event).where(Event.external_id == external_id))
    normalized_key = f"{sport.key}:{start_time.date().isoformat()}:{away_team.lower()}:{home_team.lower()}"
    if event is None:
        event = Event(
            external_id=external_id,
            sport_id=sport.id,
            home_team=home_team,
            away_team=away_team,
            start_time=start_time,
            normalized_event_key=normalized_key,
        )
        db.add(event)
    else:
        event.start_time = start_time
        event.normalized_event_key = normalized_key
    db.flush()
    return event


def add_snapshot_set(
    db: Session,
    event: Event,
    bookmakers: list[Bookmaker],
    captured_at: datetime,
    prices: list[dict[str, Decimal]],
) -> None:
    for bookmaker, bookmaker_prices in zip(bookmakers, prices, strict=True):
        for outcome_name, decimal_odds in bookmaker_prices.items():
            exists = db.scalar(
                select(OddsSnapshot)
                .where(OddsSnapshot.event_id == event.id)
                .where(OddsSnapshot.bookmaker_id == bookmaker.id)
                .where(OddsSnapshot.market_type == "h2h")
                .where(OddsSnapshot.outcome_name == outcome_name)
                .where(OddsSnapshot.decimal_odds == decimal_odds)
            )
            if exists is None:
                db.add(
                    OddsSnapshot(
                        event_id=event.id,
                        bookmaker_id=bookmaker.id,
                        market_type="h2h",
                        line=None,
                        outcome_name=outcome_name,
                        decimal_odds=decimal_odds,
                        captured_at=captured_at,
                    )
                )


def get_or_create_opportunity(
    db: Session,
    event: Event,
    implied_probability_total: Decimal,
    margin: Decimal,
    guaranteed_return: Decimal,
    guaranteed_profit: Decimal,
    status: str,
    validation_status: str,
    validation_reasons: dict[str, object],
    detected_at: datetime,
    expires_at: datetime,
) -> ArbitrageOpportunity:
    opportunity = db.scalar(
        select(ArbitrageOpportunity)
        .where(ArbitrageOpportunity.event_id == event.id)
        .where(ArbitrageOpportunity.market_type == "h2h")
        .where(ArbitrageOpportunity.validation_status == validation_status)
    )
    if opportunity is None:
        opportunity = ArbitrageOpportunity(
            event_id=event.id,
            market_type="h2h",
            line=None,
            implied_probability_total=implied_probability_total,
            margin=margin,
            total_stake=Decimal("1000.00"),
            guaranteed_return=guaranteed_return,
            guaranteed_profit=guaranteed_profit,
            status=status,
            reliability_score=Decimal("95.00") if validation_status == "FRESH" else Decimal("35.00"),
            validation_status=validation_status,
            validation_reasons=validation_reasons,
            last_validated_at=detected_at,
            detected_at=detected_at,
            expires_at=expires_at,
        )
        db.add(opportunity)
    else:
        opportunity.validation_status = validation_status
        opportunity.validation_reasons = validation_reasons
        opportunity.expires_at = expires_at
    db.flush()
    return opportunity


def ensure_legs(
    db: Session,
    opportunity: ArbitrageOpportunity,
    legs: list[tuple[Bookmaker, str, Decimal, Decimal, Decimal]],
) -> None:
    for bookmaker, outcome_name, decimal_odds, stake, expected_return in legs:
        exists = db.scalar(
            select(ArbitrageLeg)
            .where(ArbitrageLeg.opportunity_id == opportunity.id)
            .where(ArbitrageLeg.bookmaker_id == bookmaker.id)
            .where(ArbitrageLeg.outcome_name == outcome_name)
        )
        if exists is None:
            db.add(
                ArbitrageLeg(
                    opportunity_id=opportunity.id,
                    bookmaker_id=bookmaker.id,
                    outcome_name=outcome_name,
                    decimal_odds=decimal_odds,
                    stake=stake,
                    expected_return=expected_return,
                )
            )


def ensure_quality_check(
    db: Session,
    event: Event,
    status: str,
    confidence_score: Decimal,
    reasons: dict[str, object],
    checked_at: datetime,
) -> None:
    exists = db.scalar(
        select(MarketQualityCheck)
        .where(MarketQualityCheck.event_id == event.id)
        .where(MarketQualityCheck.market_type == "h2h")
        .where(MarketQualityCheck.status == status)
    )
    if exists is None:
        db.add(
            MarketQualityCheck(
                event_id=event.id,
                market_type="h2h",
                line=None,
                status=status,
                confidence_score=confidence_score,
                reasons=reasons,
                checked_at=checked_at,
            )
        )


def ensure_demo_scan_run(db: Session, now: datetime) -> None:
    exists = db.scalar(select(ScanRun).where(ScanRun.error_message == "Demo data seeded locally"))
    if exists is None:
        db.add(
            ScanRun(
                status="completed",
                sports_scanned=1,
                events_processed=2,
                markets_processed=4,
                snapshots_saved=8,
                opportunities_found=2,
                error_message="Demo data seeded locally",
                started_at=now - timedelta(minutes=1),
                completed_at=now,
            )
        )


def ensure_demo_usage_log(db: Session, now: datetime) -> None:
    exists = db.scalar(select(ApiUsageLog).where(ApiUsageLog.endpoint == "demo_seed"))
    if exists is None:
        db.add(
            ApiUsageLog(
                provider="the_odds_api",
                endpoint="demo_seed",
                sport_key="aussierules_afl",
                regions="au",
                markets="h2h",
                requests_remaining=500,
                requests_used=0,
                requests_last=0,
                estimated_cost=0,
                captured_at=now,
            )
        )
