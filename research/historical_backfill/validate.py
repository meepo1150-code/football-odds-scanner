"""Validate historical AH records without accessing production or external services."""
from __future__ import annotations

import math
from typing import Any

from research.historical_backfill.reconstruct import parse_time

REQUIRED = (
    "fixture_id", "source", "bookmaker", "kickoff_utc",
    "home_team", "away_team", "line", "home_ticks", "away_ticks",
)


def validate_ah_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return a fresh validated record. Never silently invent missing fields."""
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    for key in REQUIRED:
        if key not in record:
            raise ValueError(f"missing {key}")
    for key in ("fixture_id", "source", "bookmaker", "home_team", "away_team"):
        if not isinstance(record[key], str) or not record[key].strip():
            raise ValueError(f"invalid {key}")
    kickoff = parse_time(record["kickoff_utc"])
    line = record["line"]
    if isinstance(line, bool) or not isinstance(line, (int, float)) or not math.isfinite(line) or abs(line * 4 - round(line * 4)) > 1e-8:
        raise ValueError("invalid AH line")
    result = dict(record)
    for side in ("home_ticks", "away_ticks"):
        ticks = record[side]
        if not isinstance(ticks, list):
            raise ValueError(f"invalid {side}")
        validated = []
        for tick in ticks:
            if not isinstance(tick, dict) or "created_at" not in tick or "price" not in tick:
                raise ValueError("invalid quote")
            timestamp = parse_time(tick["created_at"])
            price = tick["price"]
            if timestamp >= kickoff:
                raise ValueError("post-kickoff quote")
            if isinstance(price, bool) or not isinstance(price, (int, float)) or not (1 < price < float("inf")):
                raise ValueError("invalid decimal price")
            validated.append({**tick, "created_at": timestamp.isoformat(), "price": float(price)})
        result[side] = sorted(validated, key=lambda x: x["created_at"])
    result["kickoff_utc"] = kickoff.isoformat()
    result["line"] = float(line)
    result["provenance"] = "HISTORICAL_RECONSTRUCTED"
    return result

