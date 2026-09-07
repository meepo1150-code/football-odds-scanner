from __future__ import annotations
import math
from typing import Iterable

from .normalize import choose_triplet, OPENING_TRIPLETS, fair_probs


def _num(row: dict, *names: str) -> float | None:
    for name in names:
        value = row.get(name)
        if value in (None, ""):
            continue
        try:
            x = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(x):
            return x
    return None


def _odds_pair(row: dict, pairs: list[tuple[str, str]]) -> tuple[float | None, float | None, str | None]:
    for left, right in pairs:
        a, b = _num(row, left), _num(row, right)
        if a is not None and b is not None and a > 1.0 and b > 1.0:
            return a, b, f"{left}/{right}"
    return None, None, None


def normalize_multimarket_rows(rows: Iterable[dict], season: str) -> list[dict]:
    """Normalize rows that contain 1X2 + Asian handicap + totals.

    The schema intentionally supports arbitrary total lines, although the current
    GitHub historical mirror only exposes the 2.5 total market.
    """
    out: list[dict] = []
    for row in rows:
        hgoals = _num(row, "FTHG", "home_goals")
        agoals = _num(row, "FTAG", "away_goals")
        if hgoals is None or agoals is None:
            continue

        one_x_two, source = choose_triplet(row, OPENING_TRIPLETS)
        if not all(one_x_two):
            continue
        probs, margin = fair_probs(*one_x_two)
        favorite_side = "H" if probs[0] >= probs[2] else "A"
        favorite_prob = probs[0] if favorite_side == "H" else probs[2]

        home_line = _num(row, "AHh", "ah_line")
        ah_home, ah_away, ah_source = _odds_pair(row, [
            ("AvgAHH", "AvgAHA"),
            ("B365AHH", "B365AHA"),
            ("market_avg_ah_home", "market_avg_ah_away"),
            ("bet365_ah_home", "bet365_ah_away"),
        ])
        ou_line = _num(row, "OU_LINE", "ou_line", "total_line")
        over, under, ou_source = _odds_pair(row, [
            ("AvgO", "AvgU"),
            ("B365O", "B365U"),
            ("market_avg_over25", "market_avg_under25"),
            ("bet365_over25", "bet365_under25"),
        ])
        if home_line is None or ah_home is None or ou_line is None or over is None:
            continue

        favorite_ah_line = home_line if favorite_side == "H" else -home_line
        favorite_ah_price = ah_home if favorite_side == "H" else ah_away
        if favorite_ah_price is None:
            continue

        out.append({
            "season": season,
            "division": row.get("Div", ""),
            "date": row.get("Date", ""),
            "home": row.get("HomeTeam", ""),
            "away": row.get("AwayTeam", ""),
            "home_goals": int(hgoals),
            "away_goals": int(agoals),
            "favorite_side": favorite_side,
            "favorite_fair_probability": favorite_prob,
            "one_x_two_source": source,
            "one_x_two_overround": margin,
            "favorite_ah_line": favorite_ah_line,
            "favorite_ah_price": favorite_ah_price,
            "ah_source": ah_source,
            "ou_line": ou_line,
            "over_price": over,
            "under_price": under,
            "ou_source": ou_source,
        })
    return out
