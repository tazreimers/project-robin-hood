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
    total_implied_probability: Decimal
    profit_margin: Decimal
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

    total_implied_probability = sum((leg.implied_probability for leg in best_by_outcome.values()), Decimal("0"))
    if total_implied_probability >= Decimal("1"):
        return None

    return ArbitrageResult(
        total_implied_probability=total_implied_probability,
        profit_margin=Decimal("1") - total_implied_probability,
        legs=list(best_by_outcome.values()),
    )
