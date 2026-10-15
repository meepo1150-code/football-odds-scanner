"""Offline historical snapshot reconstruction. No network or production imports."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def parse_time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp required")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if result.tzinfo is None:
        raise ValueError("timezone-aware timestamp required")
    return result.astimezone(timezone.utc)


def reconstruct_slot(
    *,
    fixture_id: str,
    kickoff: str,
    slot: str,
    source: str,
    bookmaker: str,
    market: str,
    line: float,
    selections: dict[str, list[dict[str, Any]]],
    max_age_seconds: int = 3600,
) -> dict[str, Any]:
    """Use independently timestamped, non-stale quotes at/before a prematch slot.

    Both sides must be available for AH/OU. No interpolation or future lookahead.
    """
    if not source or not bookmaker or not fixture_id:
        raise ValueError("source, bookmaker and fixture_id required")
    if market not in {"AH", "OU"}:
        raise ValueError("unsupported market")
    if not isinstance(line, (int, float)) or isinstance(line, bool) or abs(line * 4 - round(line * 4)) > 1e-8:
        raise ValueError("line must be on quarter grid")
    if max_age_seconds < 0:
        raise ValueError("max age must be nonnegative")
    ko, at = parse_time(kickoff), parse_time(slot)
    if at >= ko:
        raise ValueError("slot must precede kickoff")
    required = ("home", "away") if market == "AH" else ("over", "under")
    found: dict[str, dict[str, Any]] = {}
    for side in required:
        candidates = []
        for tick in selections.get(side, []):
            ts = parse_time(tick["created_at"])
            price = tick["price"]
            if not isinstance(price, (int, float)) or isinstance(price, bool) or price <= 1:
                continue
            if ts <= at and ts < ko and (at - ts).total_seconds() <= max_age_seconds:
                candidates.append((ts, float(price)))
        if not candidates:
            return {"status": "NO_HISTORICAL_DATA", "fixture_id": fixture_id, "slot": slot, "missing_side": side}
        ts, price = max(candidates, key=lambda item: item[0])
        found[side] = {"price": price, "quote_at_utc": ts.isoformat()}
    return {
        "status": "COMPLETE",
        "provenance": "HISTORICAL_RECONSTRUCTED",
        "fixture_id": fixture_id,
        "source": source,
        "bookmaker": bookmaker,
        "market": market,
        "line": float(line),
        "slot_utc": at.isoformat(),
        "kickoff_utc": ko.isoformat(),
        "quotes": found,
    }
