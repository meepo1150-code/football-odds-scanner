"""Account-only maintenance probe. Never authorize secondary odds transport.

Raw account payloads, keys and account identifiers never leave memory. Distinct
subscription IDs identify accounting buckets, not independent quota entitlement.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from .historical_manual.safety import HttpClient, summarize_account

REPORT = Path('reports/automatic_account_audit.json')


def run(root=Path('.'), *, env=None, factory=HttpClient, now=None):
    env = os.environ if env is None else env
    now = now or datetime.now(timezone.utc)
    report = dict(generated_at=now.isoformat(), fallback_enabled=False,
                  fallback_status='DISABLED', metered_requests=0, account_requests=0,
                  current_odds_entitlement='UNVERIFIED', independent_quota='UNVERIFIED',
                  reason='CURRENT_ENDPOINT_AND_INDEPENDENT_QUOTA_NOT_VERIFIED', accounts={})
    for role, name in [('primary', 'ODDSPAPI_KEY'), ('secondary', 'HISTORICAL_ODDSPAPI_KEY')]:
        if not env.get(name):
            report['accounts'][role] = dict(status='SECRET_NOT_AVAILABLE')
            continue
        try:
            report['account_requests'] += 1
            status, _, raw = factory(env[name])('/account', {})
            if status != 200:
                report['accounts'][role] = dict(status='ACCOUNT_UNAVAILABLE', http_status=status)
                continue
            payload = json.loads(raw)
            # Without an explicit subscription ID a hash of null proves nothing.
            if not payload.get('current_subscription_id'):
                raise ValueError('Missing explicit subscription identity')
            summary = summarize_account(payload, {'pinnacle'}, now)
            report['accounts'][role] = dict(status='ACCOUNT_VERIFIED', **summary,
                request_remaining=summary['request_limit']-summary['request_count'])
        except Exception as exc:
            report['accounts'][role] = dict(status='ACCOUNT_UNVERIFIED', error_type=type(exc).__name__)
    a, b = (report['accounts'].get(k, {}) for k in ('primary', 'secondary'))
    if a.get('subscription_fingerprint') and b.get('subscription_fingerprint'):
        report['subscription_relationship'] = ('SAME_SUBSCRIPTION' if a['subscription_fingerprint'] == b['subscription_fingerprint'] else 'DISTINCT_SUBSCRIPTIONS')
    else:
        report['subscription_relationship'] = 'UNVERIFIED'
    p = root/REPORT
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    print(json.dumps(run()))
