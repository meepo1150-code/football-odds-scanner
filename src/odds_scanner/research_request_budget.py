"""UTC reservations for OddsPapi research; failures consume capacity."""
import calendar
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

DAILY_LIMIT = 8
MONTHLY_LIMIT = 240
RUN_LIMIT = 2
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
    # One market call per future slot, plus the day's fixture discovery if the
    # preparation slot is still ahead. Manual and recovery cannot spend this.
    future_reserve = len(future) + int(bool(future) and future[0] == slots[0])
    # Protect five requests (discovery + four observations) on each future UTC
    # day; optional second batches yield before reaching 240/month.
    future_month_reserve = sum(len(utc_targets(now.date() + timedelta(days=i))) + 1
        for i in range(1, calendar.monthrange(now.year, now.month)[1] - now.day + 1))
    run_limit = RUN_LIMIT
    # One odds batch defines the daily cohort, even if discovery is cached.
    # This keeps every repeat observation affordable under the future-slot minimum.
    if now.date().isoformat() >= '2026-10-14' and not manual and slots and slots[0] <= now <= slots[0]+timedelta(minutes=150):
        run_limit = min(RUN_LIMIT, overhead+1)
    available = max(0, min(run_limit, DAILY_LIMIT-daily-future_reserve,
                          MONTHLY_LIMIT-monthly-future_reserve-future_month_reserve))
    remaining = max(0, available-overhead)
    batches = [ids[i:i+batch_size] for i in range(0, len(ids), batch_size)]
    chosen = [batches[i if prioritized else (now.date().toordinal()+i)%len(batches)]
              for i in range(min(remaining, len(batches)))] if batches else []
    return [x for b in chosen for x in b], {
        'request_budget_policy': 'RESEARCH_8_PER_UTC_DAY_240_PER_UTC_MONTH',
        'research_requests_used_today': daily, 'research_requests_used_month': monthly,
        'research_daily_limit': DAILY_LIMIT, 'research_monthly_limit': MONTHLY_LIMIT,
        'research_run_limit': run_limit, 'quota_utc_day': now.date().isoformat(),
        'canonical_slots_in_football_day': len(slots),
        'future_utc_slots': [t.isoformat() for t in future],
        'future_utc_requests_reserved': future_reserve,
        'future_month_requests_reserved': future_month_reserve,
        'canonical_request_reservation': 'UTC_FUTURE_SLOTS_PLUS_DISCOVERY; MANUAL_AND_RECOVERY_YIELD; FAILED_ATTEMPTS_COUNT',
        'budget_scope': 'ODDSPAPI_RESEARCH_COLLECTOR_ONLY',
        'coverage_mode': 'MASTER_SCHEDULE_PRIORITIZED' if prioritized else 'DAILY_STABLE_COHORT_WITH_REPEAT_OBSERVATIONS',
        'schedule_requests_reserved': overhead,
        'coverage_complete': len(chosen) == len(batches),
        'coverage_tournament_ids': [x for b in chosen for x in b],
    }
