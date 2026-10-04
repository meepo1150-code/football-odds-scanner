"""Conservative OddsPapi research allocation; free collectors remain independent."""
import json
from datetime import datetime, timezone

DAILY_LIMIT = 6
MONTHLY_LIMIT = 180
RUN_LIMIT = 2


def allocation(path, ids, now, batch_size=5):
    # Count unique attempts, including failures. Concurrent persistence may repeat
    # a record; divergent copies conservatively retain the largest request count.
    attempts = {}
    now = now.astimezone(timezone.utc)
    if path.exists():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            stamp = datetime.fromisoformat(row['finalized_at'].replace('Z', '+00:00'))
            if stamp.tzinfo is None:
                raise ValueError('request timestamp has no timezone')
            stamp = stamp.astimezone(timezone.utc)
            if (stamp.year,stamp.month) != (now.year,now.month):
                continue
            used = int(row.get('requests_used', 0))
            if used < 0:
                raise ValueError('negative recorded request usage')
            if not used:
                continue
            key = (row.get('scheduled_target_at'), stamp)
            attempts[key] = max(used, attempts.get(key, 0))
    monthly = sum(v for (_, t), v in attempts.items() if (t.year,t.month)==(now.year,now.month))
    daily = sum(v for (_, t), v in attempts.items() if t.date()==now.date())
    remaining = max(0, min(RUN_LIMIT, DAILY_LIMIT-daily, MONTHLY_LIMIT-monthly))
    batches = [ids[i:i+batch_size] for i in range(0,len(ids),batch_size)]
    chosen = [batches[(monthly+i)%len(batches)] for i in range(min(remaining,len(batches)))] if batches else []
    return [x for b in chosen for x in b], {
        'request_budget_policy':'RESEARCH_6_PER_UTC_DAY_180_PER_UTC_MONTH',
        'research_requests_used_today':daily, 'research_requests_used_month':monthly,
        'research_daily_limit':DAILY_LIMIT, 'research_monthly_limit':MONTHLY_LIMIT,
        'research_run_limit':RUN_LIMIT,
        'budget_scope':'ODDSPAPI_RESEARCH_COLLECTOR_ONLY',
        'coverage_mode':'BUDGETED_ROTATING_UNIVERSE',
        'coverage_complete':len(chosen)==len(batches),
        'coverage_tournament_ids':[x for b in chosen for x in b],
    }
