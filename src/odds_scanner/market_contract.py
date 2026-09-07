from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CurrentMarket:
    """Provider-neutral pre-match market snapshot used by the production scanner."""

    source: str
    league: str
    date: str
    kickoff: str
    home: str
    away: str
    ah_home_line: float | None
    ah_home_odds: float | None
    ah_away_line: float | None
    ah_away_odds: float | None
    ou_line: float | None
    over_odds: float | None
    under_odds: float | None
    one_x_two_home: float | None
    one_x_two_draw: float | None
    one_x_two_away: float | None
    status: str | None = None
    as_of: str | None = None
    stale: bool | None = None
    tradable: bool | None = None


def two_way_fair_probs(a_odds: float, b_odds: float) -> tuple[float, float, float]:
    """Proportional de-vig for a valid two-way decimal-odds market."""
    if a_odds <= 1.0 or b_odds <= 1.0:
        raise ValueError("two-way decimal odds must both be greater than 1.0")
    ia, ib = 1.0 / a_odds, 1.0 / b_odds
    total = ia + ib
    return ia / total, ib / total, total - 1.0
