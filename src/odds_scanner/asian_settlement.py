from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class Settlement(str, Enum):
    FULL_WIN = "FULL_WIN"
    HALF_WIN = "HALF_WIN"
    PUSH = "PUSH"
    HALF_LOSS = "HALF_LOSS"
    FULL_LOSS = "FULL_LOSS"


@dataclass(frozen=True)
class SettledBet:
    settlement: Settlement
    profit_units: float
    return_units: float


def _split_quarter_line(line: float) -> tuple[float, float]:
    q = round(line * 4)
    if abs(line * 4 - q) > 1e-8:
        raise ValueError(f"Asian line must be on a 0.25 grid: {line}")
    if q % 2 == 0:
        return line, line
    lo = (q - 1) / 4
    hi = (q + 1) / 4
    return lo, hi


def _leg_profit(score: float, odds: float) -> float:
    if score > 1e-9:
        return odds - 1.0
    if score < -1e-9:
        return -1.0
    return 0.0


def _classify(profit: float, odds: float) -> Settlement:
    full_win = odds - 1.0
    if abs(profit - full_win) < 1e-8:
        return Settlement.FULL_WIN
    if abs(profit - full_win / 2) < 1e-8:
        return Settlement.HALF_WIN
    if abs(profit) < 1e-8:
        return Settlement.PUSH
    if abs(profit + 0.5) < 1e-8:
        return Settlement.HALF_LOSS
    if abs(profit + 1.0) < 1e-8:
        return Settlement.FULL_LOSS
    raise ValueError(f"Unexpected Asian settlement profit: {profit}")


def settle_asian_handicap(home_goals: int, away_goals: int, line: float, odds: float, side: str) -> SettledBet:
    """Settle a 1-unit Asian handicap bet.

    `line` is expressed from the selected side's perspective. Examples:
    home -0.75 => side='H', line=-0.75
    away +0.75 => side='A', line=+0.75
    """
    if odds <= 1.0:
        raise ValueError("Decimal odds must be > 1")
    side = side.upper()
    if side not in {"H", "A"}:
        raise ValueError("AH side must be H or A")
    goal_diff = home_goals - away_goals
    selected_diff = goal_diff if side == "H" else -goal_diff
    a, b = _split_quarter_line(line)
    profit = (_leg_profit(selected_diff + a, odds) + _leg_profit(selected_diff + b, odds)) / 2
    return SettledBet(_classify(profit, odds), profit, 1.0 + profit)


def settle_asian_total(home_goals: int, away_goals: int, line: float, odds: float, side: str) -> SettledBet:
    """Settle a 1-unit Asian total bet. side is O or U."""
    if odds <= 1.0:
        raise ValueError("Decimal odds must be > 1")
    side = side.upper()
    if side not in {"O", "U"}:
        raise ValueError("OU side must be O or U")
    total = home_goals + away_goals
    a, b = _split_quarter_line(line)
    def score(part: float) -> float:
        return total - part if side == "O" else part - total
    profit = (_leg_profit(score(a), odds) + _leg_profit(score(b), odds)) / 2
    return SettledBet(_classify(profit, odds), profit, 1.0 + profit)
