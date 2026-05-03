from __future__ import annotations

from decimal import Decimal

MONEY_PRECISION = Decimal("0.01")
PROBABILITY_PRECISION = Decimal("0.000001")

SUPPORTED_OPPORTUNITY_ACTION_TYPES = {
    "VIEWED",
    "ACTIONED",
    "SKIPPED",
    "EXPIRED",
    "ODDS_CHANGED",
    "BET_REJECTED",
    "WON",
    "LOST",
}
