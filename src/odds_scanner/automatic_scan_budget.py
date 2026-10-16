"""Auto grant planning: no artificial research day/month limits.

The clone refreshes /account before reserve; shared transport enforces actual
subscription, rate-limit cooldown and ACCOUNT_RESERVE before every HTTP call.
"""
from datetime import timezone
from .research_request_budget import usage


def allocation(path, ids, now, batch_size=5, *, prioritized=False, overhead=0, manual=False):
    if now.tzinfo is None:
        raise ValueError('aware clock required')
    daily, monthly = usage(path, now.astimezone(timezone.utc))
    return list(ids), dict(request_budget_policy='AUTO_PROVIDER_QUOTA_ONLY',
        research_requests_used_today=daily, research_requests_used_month=monthly,
        research_daily_limit=None, research_monthly_limit=None,
        research_run_limit=(len(ids)+batch_size-1)//batch_size+overhead,
        quota_utc_day=now.astimezone(timezone.utc).date().isoformat(),
        future_utc_requests_reserved=0, future_month_requests_reserved=0,
        coverage_complete=True, coverage_tournament_ids=list(ids))
