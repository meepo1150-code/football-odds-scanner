from __future__ import annotations

from collections import Counter
from typing import Iterable

SETTLEMENTS = ("FULL_WIN", "HALF_WIN", "PUSH", "HALF_LOSS", "FULL_LOSS")


def settlement_distribution(values: Iterable[str]) -> dict[str, int]:
    counts = Counter(str(v) for v in values)
    return {name: int(counts.get(name, 0)) for name in SETTLEMENTS}


def settlement_ev(distribution: dict[str, int], decimal_odds: float) -> float:
    if decimal_odds <= 1.0:
        raise ValueError("Decimal odds must be > 1")
    n = sum(int(distribution.get(name, 0)) for name in SETTLEMENTS)
    if n <= 0:
        raise ValueError("Settlement distribution must contain observations")
    win = decimal_odds - 1.0
    total_profit = (
        distribution.get("FULL_WIN", 0) * win
        + distribution.get("HALF_WIN", 0) * (win / 2.0)
        + distribution.get("PUSH", 0) * 0.0
        + distribution.get("HALF_LOSS", 0) * -0.5
        + distribution.get("FULL_LOSS", 0) * -1.0
    )
    return total_profit / n


def minimum_phase_ev(phase_distributions: dict[str, dict[str, int]], decimal_odds: float) -> float:
    if not phase_distributions:
        raise ValueError("At least one phase distribution is required")
    return min(settlement_ev(dist, decimal_odds) for dist in phase_distributions.values())
