from __future__ import annotations

import hashlib
import math
import random
from collections import defaultdict
from statistics import stdev

BOOTSTRAP_DRAWS = 500
SIGN_FLIP_DRAWS = 1000


def _seed(label: str) -> int:
    return int.from_bytes(hashlib.sha256(label.encode("utf-8")).digest()[:8], "big")


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_values[lo]
    frac = pos - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def _bootstrap_ci(values: list[float], rng: random.Random, draws: int) -> tuple[float, float]:
    n = len(values)
    if not n:
        return 0.0, 0.0
    means = []
    for _ in range(draws):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return _quantile(means, 0.025), _quantile(means, 0.975)


def _sign_flip_p(values: list[float], rng: random.Random, draws: int) -> float:
    if not values:
        return 1.0
    observed = abs(sum(values) / len(values))
    extreme = 0
    for _ in range(draws):
        trial = abs(sum(v if rng.random() < 0.5 else -v for v in values) / len(values))
        if trial >= observed - 1e-15:
            extreme += 1
    return (extreme + 1) / (draws + 1)


def _max_drawdown(values: list[float]) -> float:
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for value in values:
        cumulative += value
        peak = max(peak, cumulative)
        max_dd = max(max_dd, peak - cumulative)
    return max_dd


def _longest_losing_streak(values: list[float]) -> int:
    longest = current = 0
    for value in values:
        if value < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def profit_diagnostics(
    profits: list[float],
    seasons: list[str],
    *,
    seed_label: str,
    bootstrap_draws: int = BOOTSTRAP_DRAWS,
    sign_flip_draws: int = SIGN_FLIP_DRAWS,
) -> dict:
    """Summarize an observed chronological flat-stake profit sequence.

    Bootstrap and sign-flip simulations are deterministic for a stable seed label so
    CI/audit output is reproducible in GitHub Actions. Sign-flip p is a diagnostic null
    test, not a standalone production gate.
    """
    values = [float(v) for v in profits]
    n = len(values)
    if len(seasons) != n:
        raise ValueError("profits and seasons must have equal length")
    if not n:
        return {
            "n": 0,
            "mean_roi": 0.0,
            "sample_sd": 0.0,
            "bootstrap_ci95": [0.0, 0.0],
            "sign_flip_p": 1.0,
            "max_drawdown_units": 0.0,
            "longest_losing_streak": 0,
            "worst_season_roi": None,
            "season_abs_concentration": 0.0,
        }

    rng = random.Random(_seed(seed_label))
    lo, hi = _bootstrap_ci(values, rng, bootstrap_draws)
    # Use a separate deterministic stream so changing bootstrap draws does not alter p.
    flip_rng = random.Random(_seed(seed_label + "|signflip"))
    p = _sign_flip_p(values, flip_rng, sign_flip_draws)

    season_values: dict[str, list[float]] = defaultdict(list)
    for season, value in zip(seasons, values):
        season_values[str(season)].append(value)
    season_rois = {s: sum(vs) / len(vs) for s, vs in season_values.items()}
    season_totals = [sum(vs) for vs in season_values.values()]
    abs_total = sum(abs(x) for x in season_totals)
    concentration = max((abs(x) for x in season_totals), default=0.0) / abs_total if abs_total else 0.0

    return {
        "n": n,
        "mean_roi": round(sum(values) / n, 6),
        "sample_sd": round(stdev(values), 6) if n > 1 else 0.0,
        "bootstrap_ci95": [round(lo, 6), round(hi, 6)],
        "bootstrap_draws": bootstrap_draws,
        "sign_flip_p": round(p, 6),
        "sign_flip_draws": sign_flip_draws,
        "max_drawdown_units": round(_max_drawdown(values), 6),
        "longest_losing_streak": _longest_losing_streak(values),
        "worst_season_roi": round(min(season_rois.values()), 6) if season_rois else None,
        "season_abs_concentration": round(concentration, 6),
        "season_rois": {k: round(v, 6) for k, v in sorted(season_rois.items())},
    }
