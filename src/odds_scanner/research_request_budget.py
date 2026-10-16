"""UTC reservations for OddsPapi research; failures consume capacity."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

RESERVATIONS = Path('data/normalized/research_v2_quota_reservations.jsonl')


def _stamp(value):
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('request timestamp has no timezone')
    return stamp.astimezone(timezone.utc)


def _rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def usage(path, now):
    attempts = {}
    reservations = _rows(path.parent / RESERVATIONS.name)
    reserved_ids = {r['reservation_id'] for r in reservations}
    # A persisted grant survives a cancelled runner. Do not refund unused capacity
    # without provider evidence; its finalized receipt must not count a second time.
    for row in reservations + _rows(path):
        if row.get('provider', 'oddspapi') != 'oddspapi':
            continue
        if 'reservation_id' not in row and row.get('budget_reservation_id') in reserved_ids:
            continue
        stamp = _stamp(row['finalized_at'])
        if (stamp.year, stamp.month) != (now.year, now.month):
            continue
        used = row.get('requests_used', 0)
        if type(used) is not int or used < 0:
            raise ValueError('invalid recorded request usage')
        key = row.get('reservation_id') or (row.get('scheduled_target_at'), stamp)
        attempts[key] = (stamp, max(used, attempts.get(key, (stamp, 0))[1]))
    return (sum(v for t, v in attempts.values() if t.date() == now.date()),
            sum(v for t, v in attempts.values()))


def utc_targets(day):
    """A Bangkok midnight belongs to the preceding UTC quota day."""
    from .research_v2_slots import targets
    candidates = []
    for offset in (-1, 0, 1):
        candidates.extend(targets(day + timedelta(days=offset)))
    return sorted({t.astimezone(timezone.utc) for t in candidates
                   if t.astimezone(timezone.utc).date() == day})


def allocation(path, ids, now, batch_size=5, *, prioritized=False, overhead=0, manual=False):
    if now.tzinfo is None:
        raise ValueError('allocation requires an aware clock')
    now = now.astimezone(timezone.utc)
    daily, monthly = usage(path, now)
    slots = utc_targets(now.date())
    future = [t for t in slots if t > now]
    # Schedule metadata is observational; only provider entitlement gates transport.
    run_limit = (len(ids) + batch_size - 1) // batch_size + overhead
    remaining = max(0, run_limit - overhead)
    batches = [ids[i:i+batch_size] for i in range(0, len(ids), batch_size)]
    chosen = [batches[i if prioritized else (now.date().toordinal()+i)%len(batches)]
              for i in range(min(remaining, len(batches)))] if batches else []
    return [x for b in chosen for x in b], {
        'request_budget_policy': 'PROVIDER_ENFORCED_ONLY',
        'research_requests_used_today': daily, 'research_requests_used_month': monthly,
        'research_daily_limit': None, 'research_monthly_limit': None,
        'research_run_limit': run_limit, 'quota_utc_day': now.date().isoformat(),
        'canonical_slots_in_football_day': len(slots),
        'future_utc_slots': [t.isoformat() for t in future],
        'future_utc_requests_reserved': 0,
        'current_canonical_requests_reserved': 0,
        'future_month_requests_reserved': 0,
        'canonical_request_reservation': 'NONE_INTERNAL; PROVIDER_ENFORCED',
        'budget_scope': 'ODDSPAPI_RESEARCH_COLLECTOR_ONLY',
        'coverage_mode': 'MASTER_SCHEDULE_PRIORITIZED' if prioritized else 'DAILY_STABLE_COHORT_WITH_REPEAT_OBSERVATIONS',
        'schedule_requests_reserved': overhead,
        'coverage_complete': len(chosen) == len(batches),
        'coverage_tournament_ids': [x for b in chosen for x in b],
    }
