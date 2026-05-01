from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping


@dataclass(frozen=True)
class ArbitrageLeg:
    bookmaker: str
    outcome: str
    odds: Decimal
    implied_probability: Decimal


@dataclass(frozen=True)
class ArbitrageResult:
    implied_probability_total: Decimal
    margin: Decimal
    legs: list[ArbitrageLeg]


def find_arbitrage(outcomes_by_bookmaker: Mapping[str, Mapping[str, Decimal]]) -> ArbitrageResult | None:
    best_by_outcome: dict[str, ArbitrageLeg] = {}

    for bookmaker, outcomes in outcomes_by_bookmaker.items():
        for outcome, odds in outcomes.items():
            if odds <= 0:
                continue

            current = best_by_outcome.get(outcome)
            if current is None or odds > current.odds:
                best_by_outcome[outcome] = ArbitrageLeg(
                    bookmaker=bookmaker,
                    outcome=outcome,
                    odds=odds,
                    implied_probability=Decimal("1") / odds,
                )

    if len(best_by_outcome) < 2:
        return None

    implied_probability_total = sum((leg.implied_probability for leg in best_by_outcome.values()), Decimal("0"))
    if implied_probability_total >= Decimal("1"):
        return None

    return ArbitrageResult(
        implied_probability_total=implied_probability_total,
        margin=Decimal("1") - implied_probability_total,
        legs=list(best_by_outcome.values()),
    )
