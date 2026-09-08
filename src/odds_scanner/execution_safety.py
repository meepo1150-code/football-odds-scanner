from __future__ import annotations

from datetime import datetime, timezone


ALLOWED_PREMATCH_STATUS = {"scheduled", "pre_match", "prematch", "open"}


def _parse_aware_timestamp(value: object, *, missing: str, invalid: str, naive: str):
    if not isinstance(value, str) or not value.strip():
        return None, missing
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None, invalid
    if stamp.tzinfo is None:
        return None, naive
    return stamp.astimezone(timezone.utc), None


def execution_snapshot_status(market, *, now: datetime | None = None, max_age_minutes: int = 30) -> tuple[bool, str]:
    """Validate that a canonical market row is a fresh, open, pre-match execution quote.

    Two freshness contracts are supported:
    1. Legacy/direct quote timestamp: `as_of` is the provider's freshness time.
    2. Verified current endpoint: `observed_at` is when a provider endpoint that
       explicitly returns current active odds was successfully observed. The
       distinct `price_changed_at` may legitimately be much older when a price
       has not moved; it is never substituted for observation freshness.

    A provider cannot opt into contract #2 merely by setting a fetch timestamp:
    `current_feed_verified` must be True and the adapter must independently prove
    bookmaker/market/selection active status before setting `tradable=True`.
    """
    status = getattr(market, "status", None)
    if not isinstance(status, str) or status.lower() not in ALLOWED_PREMATCH_STATUS:
        return False, "EXECUTION_STATUS_INVALID_OR_MISSING"
    if getattr(market, "stale", None) is not False:
        return False, "STALE_OR_UNVERIFIED_QUOTE"
    if getattr(market, "tradable", None) is not True:
        return False, "MARKET_NOT_VERIFIED_TRADABLE"

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)

    if getattr(market, "current_feed_verified", False) is True:
        stamp, error = _parse_aware_timestamp(
            getattr(market, "observed_at", None),
            missing="OBSERVATION_TIMESTAMP_MISSING",
            invalid="OBSERVATION_TIMESTAMP_INVALID",
            naive="OBSERVATION_TIMESTAMP_NOT_UTC_AWARE",
        )
        if error:
            return False, error
        freshness_basis = getattr(market, "freshness_basis", None)
        if not isinstance(freshness_basis, str) or not freshness_basis.strip():
            return False, "CURRENT_FEED_FRESHNESS_BASIS_MISSING"
    else:
        stamp, error = _parse_aware_timestamp(
            getattr(market, "as_of", None),
            missing="QUOTE_TIMESTAMP_MISSING",
            invalid="QUOTE_TIMESTAMP_INVALID",
            naive="QUOTE_TIMESTAMP_NOT_UTC_AWARE",
        )
        if error:
            return False, error

    age_seconds = (current - stamp).total_seconds()
    if age_seconds < -300:
        return False, "QUOTE_TIMESTAMP_IN_FUTURE"
    if age_seconds > max_age_minutes * 60:
        return False, "QUOTE_TOO_OLD"
    return True, "EXECUTION_SAFE"
