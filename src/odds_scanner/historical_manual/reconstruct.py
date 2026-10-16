"""Network-free reconstruction; latest state wins, including suspension/invalidity."""
from __future__ import annotations
from datetime import datetime, timezone
import math


def parse_time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError('timestamp required')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('timezone-aware timestamp required')
    return result.astimezone(timezone.utc)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def reconstruct_slot(*, fixture_id, kickoff, slot, source, bookmaker, market,
                     line, selections, max_age_seconds=3600):
    if not source or not bookmaker or not fixture_id:
        raise ValueError('source, bookmaker and fixture_id required')
    if market not in {'AH', 'OU'}:
        raise ValueError('unsupported market')
    if not finite(line) or abs(line * 4 - round(line * 4)) > 1e-8:
        raise ValueError('line must be on quarter grid')
    if type(max_age_seconds) is not int or max_age_seconds < 0:
        raise ValueError('max age must be a nonnegative integer')
    ko, at = parse_time(kickoff), parse_time(slot)
    if at >= ko:
        raise ValueError('slot must precede kickoff')
    base = dict(fixture_id=fixture_id, source=source, bookmaker=bookmaker,
                market=market, line=float(line), slot_utc=at.isoformat(),
                kickoff_utc=ko.isoformat(), data_origin='BACKFILLED',
                provenance='HISTORICAL_RECONSTRUCTED')
    found = {}
    for side in (('home', 'away') if market == 'AH' else ('over', 'under')):
        candidates = []
        for tick in selections.get(side, []):
            try:
                ts = parse_time(tick['created_at'])
            except (ValueError, KeyError, TypeError):
                return {**base, 'status': 'INVALID_TIMESTAMP', 'missing_side': side}
            if ts <= at and ts < ko:
                candidates.append((ts, tick))
        if not candidates:
            return {**base, 'status': 'NO_HISTORICAL_DATA', 'missing_side': side}
        latest = max(t for t, _ in candidates)
        ticks = [v for t, v in candidates if t == latest]
        if len({(str(v.get('price')), str(v.get('active'))) for v in ticks}) > 1:
            return {**base, 'status': 'AMBIGUOUS_LATEST_STATE', 'missing_side': side}
        tick = ticks[0]
        if tick.get('active') is not True:
            return {**base, 'status': 'INACTIVE_OR_UNKNOWN', 'missing_side': side}
        price = tick.get('price')
        if not finite(price) or price <= 1:
            return {**base, 'status': 'INVALID_PRICE', 'missing_side': side}
        if (at - latest).total_seconds() > max_age_seconds:
            return {**base, 'status': 'STALE_QUOTE', 'missing_side': side}
        found[side] = dict(price=float(price), quote_at_utc=latest.isoformat(),
                           source_record_id=tick.get('id'), active=True)
    return {**base, 'status': 'COMPLETE', 'quotes': found}
