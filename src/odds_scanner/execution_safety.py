from __future__ import annotations

from datetime import datetime, timezone


ALLOWED_PREMATCH_STATUS = {"scheduled", "pre_match", "prematch", "open"}


def execution_snapshot_status(market, *, now: datetime | None = None, max_age_minutes: int = 30) -> tuple[bool, str]:
    """Validate that a canonical market row is a fresh, open, pre-match execution quote."""
    status = getattr(market, "status", None)
    if not isinstance(status, str) or status.lower() not in ALLOWED_PREMATCH_STATUS:
        return False, "EXECUTION_STATUS_INVALID_OR_MISSING"
    if getattr(market, "stale", None) is not False:
        return False, "STALE_OR_UNVERIFIED_QUOTE"
    if getattr(market, "tradable", None) is not True:
        return False, "MARKET_NOT_VERIFIED_TRADABLE"

    as_of = getattr(market, "as_of", None)
    if not isinstance(as_of, str) or not as_of.strip():
        return False, "QUOTE_TIMESTAMP_MISSING"
    try:
        stamp = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    except ValueError:
        return False, "QUOTE_TIMESTAMP_INVALID"
    if stamp.tzinfo is None:
        return False, "QUOTE_TIMESTAMP_NOT_UTC_AWARE"

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    age_seconds = (current.astimezone(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds()
    if age_seconds < -300:
        return False, "QUOTE_TIMESTAMP_IN_FUTURE"
    if age_seconds > max_age_minutes * 60:
        return False, "QUOTE_TOO_OLD"
    return True, "EXECUTION_SAFE"
