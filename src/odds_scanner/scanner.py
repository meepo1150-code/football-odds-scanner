from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from .settlement_ev import settlement_ev
from .sgodds_provider import CurrentMarket, two_way_fair_probs

DEFAULT_MIN_ODDS = 1.80
DEFAULT_MAX_ODDS = 2.20
DEFAULT_MIN_EV = 0.01
DEFAULT_FORWARD_DAYS = 7


class CurrentTradableProvider(Protocol):
    """Execution-price provider contract. Opening snapshots must not implement this by default."""

    provider_id: str

    def fetch(self) -> list[CurrentMarket]: ...


def _write_today(root: Path, payload: dict) -> dict:
    p = root / "reports/today.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _in_band(value: float, band) -> bool:
    if not band:
        return True
    lo, hi = float(band[0]), float(band[1])
    return lo <= value < hi


def _favorite(m: CurrentMarket) -> tuple[str | None, float | None]:
    h, a = m.one_x_two_home, m.one_x_two_away
    if h is None or a is None:
        return None, None
    return ("H", h) if h < a else ("A", a)


def _fair_favorite_probability(m: CurrentMarket, side: str) -> float | None:
    odds = (m.one_x_two_home, m.one_x_two_draw, m.one_x_two_away)
    if any(x is None for x in odds):
        return None
    raw = [1.0 / float(x) for x in odds]
    total = sum(raw)
    probs = [x / total for x in raw]
    return probs[0] if side == "H" else probs[2]


def _market_values(m: CurrentMarket, pattern: dict) -> tuple[float | None, float | None, float | None]:
    key = pattern.get("pattern_key", {})
    fav_side = key.get("favorite_side")
    market = pattern.get("market")
    if market == "AH":
        if fav_side == "H":
            return m.ah_home_odds, m.ah_away_odds, m.ah_home_line
        if fav_side == "A":
            return m.ah_away_odds, m.ah_home_odds, m.ah_away_line
    if market == "OU":
        if key.get("ou_side") == "O":
            return m.over_odds, m.under_odds, m.ou_line
        if key.get("ou_side") == "U":
            return m.under_odds, m.over_odds, m.ou_line
    return None, None, None


def _pattern_matches_structure(m: CurrentMarket, pattern: dict) -> tuple[bool, str]:
    key = pattern.get("pattern_key") or {}
    fav_side, _ = _favorite(m)
    required_side = key.get("favorite_side")
    if fav_side is None or required_side not in {"H", "A"} or fav_side != required_side:
        return False, "FAVORITE_SIDE_MISMATCH"

    current_ah_line = m.ah_home_line if fav_side == "H" else m.ah_away_line
    current_ah_price = m.ah_home_odds if fav_side == "H" else m.ah_away_odds
    if current_ah_line is None or abs(current_ah_line - float(key.get("ah_line"))) > 1e-9:
        return False, "AH_LINE_MISMATCH"
    if current_ah_price is None:
        return False, "AH_PRICE_MISSING"
    if key.get("ah_price_band") and not _in_band(current_ah_price, key["ah_price_band"]):
        return False, "AH_PRICE_STRUCTURE_MISMATCH"

    if key.get("ou_line") is not None:
        if m.ou_line is None or abs(m.ou_line - float(key["ou_line"])) > 1e-9:
            return False, "OU_LINE_MISMATCH"
        ou_price = m.over_odds if key.get("ou_side") == "O" else m.under_odds
        if ou_price is None:
            return False, "OU_PRICE_MISSING"
        if key.get("ou_price_band") and not _in_band(ou_price, key["ou_price_band"]):
            return False, "OU_PRICE_STRUCTURE_MISMATCH"

    if key.get("favorite_probability_band"):
        fav_p = _fair_favorite_probability(m, fav_side)
        if fav_p is None or not _in_band(fav_p, key["favorite_probability_band"]):
            return False, "1X2_STRUCTURE_MISMATCH"

    return True, "MATCH"


def _within_window(m: CurrentMarket, today: date, forward_days: int) -> bool:
    try:
        d = date.fromisoformat(m.date)
    except ValueError:
        return False
    return today <= d <= today + timedelta(days=forward_days)


def evaluate_candidate(
    m: CurrentMarket,
    pattern: dict,
    *,
    min_odds: float = DEFAULT_MIN_ODDS,
    max_odds: float = DEFAULT_MAX_ODDS,
    min_ev: float = DEFAULT_MIN_EV,
) -> tuple[dict | None, str]:
    ok, reason = _pattern_matches_structure(m, pattern)
    if not ok:
        return None, reason

    target_odds, opposite_odds, line = _market_values(m, pattern)
    if target_odds is None or opposite_odds is None or line is None:
        return None, "MARKET_PRICE_INCOMPLETE"
    if not (min_odds <= target_odds <= max_odds):
        return None, "PRICE_OUT_OF_RANGE"

    distributions = pattern.get("settlement_distributions") or {}
    if set(distributions) < {"train", "validation", "holdout"}:
        return None, "SETTLEMENT_DISTRIBUTION_MISSING"

    phase_ev = {phase: settlement_ev(dist, target_odds) for phase, dist in distributions.items()}
    min_phase = min(phase_ev.values())
    if min_phase < min_ev:
        return None, "EDGE_ERODED"

    target_fair, _, overround = two_way_fair_probs(target_odds, opposite_odds)
    return {
        "date": m.date,
        "time": m.kickoff,
        "league": m.league,
        "home": m.home,
        "away": m.away,
        "pattern_id": pattern.get("pattern_id"),
        "pattern": pattern.get("pattern"),
        "market": pattern.get("market"),
        "line": line,
        "current_odds": target_odds,
        "current_fair_probability": round(target_fair, 6),
        "market_overround": round(overround, 6),
        "phase_ev": {k: round(v, 6) for k, v in phase_ev.items()},
        "min_phase_ev": round(min_phase, 6),
        "train_n": pattern.get("train_n"),
        "validation_n": pattern.get("validation_n"),
        "holdout_n": pattern.get("holdout_n"),
        "q_validation_bh": pattern.get("q_validation_bh"),
        "source": m.source,
    }, "ELIGIBLE"


def scan(
    root: Path,
    *,
    markets: list[CurrentMarket] | None = None,
    provider: CurrentTradableProvider | None = None,
    min_odds: float = DEFAULT_MIN_ODDS,
    max_odds: float = DEFAULT_MAX_ODDS,
    min_ev: float = DEFAULT_MIN_EV,
    forward_days: int = DEFAULT_FORWARD_DAYS,
) -> dict:
    generated_at = datetime.now(timezone.utc).isoformat()
    registry_path = root / "reports/pattern_registry.json"
    if not registry_path.exists():
        return _write_today(root, {
            "schema_version": "3.1",
            "status": "REGISTRY_UNAVAILABLE",
            "generated_at": generated_at,
            "matches_scanned": 0,
            "qualifying": 0,
            "candidates": [],
            "reason": "Validated pattern registry has not been generated.",
        })

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    patterns = registry.get("patterns", [])
    if not patterns:
        return _write_today(root, {
            "schema_version": "3.1",
            "status": "NO_VALIDATED_PATTERNS",
            "generated_at": generated_at,
            "matches_scanned": 0,
            "patterns_available": 0,
            "qualifying": 0,
            "candidates": [],
            "message": "NO QUALIFYING BETS",
            "reason": "No historical pattern passed the frozen train-validation-holdout and cross-league gates.",
        })

    if markets is not None and provider is not None:
        raise ValueError("Provide either injected markets or a current tradable provider, not both")

    if markets is not None:
        source_markets = markets
        provider_id = "injected_tradable_market_rows"
    elif provider is not None:
        try:
            source_markets = provider.fetch()
            provider_id = provider.provider_id
        except Exception as exc:
            return _write_today(root, {
                "schema_version": "3.1",
                "status": "PROVIDER_UNAVAILABLE",
                "generated_at": generated_at,
                "matches_scanned": 0,
                "patterns_available": len(patterns),
                "qualifying": 0,
                "candidates": [],
                "reason": f"Current tradable provider failed: {type(exc).__name__}: {exc}",
            })
    else:
        return _write_today(root, {
            "schema_version": "3.1",
            "status": "CURRENT_TRADABLE_PROVIDER_REQUIRED",
            "generated_at": generated_at,
            "matches_scanned": 0,
            "patterns_available": len(patterns),
            "qualifying": 0,
            "candidates": [],
            "message": "NO QUALIFYING BETS",
            "reason": "Validated patterns exist, but no true current tradable multi-market price provider is configured. Opening-only snapshots are not accepted as execution prices.",
        })

    today = datetime.now(timezone.utc).date()
    current = [m for m in source_markets if _within_window(m, today, forward_days)]
    candidates = []
    rejection_counts: dict[str, int] = {}
    for m in current:
        for pattern in patterns:
            candidate, reason = evaluate_candidate(
                m, pattern, min_odds=min_odds, max_odds=max_odds, min_ev=min_ev
            )
            if candidate:
                candidates.append(candidate)
            else:
                rejection_counts[reason] = rejection_counts.get(reason, 0) + 1

    candidates.sort(
        key=lambda x: (x["min_phase_ev"], x["holdout_n"] or 0, -(x["q_validation_bh"] or 1.0)),
        reverse=True,
    )
    top = candidates[:5]
    return _write_today(root, {
        "schema_version": "3.1",
        "status": "OK" if top else "NO_QUALIFYING_MATCHES",
        "generated_at": generated_at,
        "provider": provider_id,
        "matches_scanned": len(current),
        "patterns_available": len(patterns),
        "pattern_match_evaluations": len(current) * len(patterns),
        "qualifying": len(candidates),
        "displayed": len(top),
        "candidates": top,
        "rejection_counts": rejection_counts,
        "rule": {
            "exact_line_match": True,
            "current_odds_min": min_odds,
            "current_odds_max": max_odds,
            "minimum_ev_each_phase": min_ev,
            "forward_days": forward_days,
            "max_display": 5,
            "opening_snapshots_allowed_as_current": False,
        },
        "message": "NO QUALIFYING BETS" if not top else None,
    })
