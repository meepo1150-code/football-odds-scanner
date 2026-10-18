"""Probe the actual current Manual/Auto account outside historical environment overrides."""
from datetime import datetime, timezone
import os
from pathlib import Path

from .safety import HttpClient, StopPilot, summarize_account


def probe(key, *, client_factory=HttpClient, now=None):
    if not key:
        raise StopPilot('CURRENT_SCAN_KEY_MISSING')
    import json
    now = now or datetime.now(timezone.utc)
    status, _, raw = client_factory(key)('/account', {})
    if status != 200:
        raise StopPilot('CURRENT_SCAN_ACCOUNT_HTTP_'+str(status))
    try:
        payload = json.loads(raw)
        if not payload.get('current_subscription_id'):
            raise StopPilot('CURRENT_SCAN_SUBSCRIPTION_ID_MISSING')
        account = summarize_account(payload, set(), now)
    except (ValueError, KeyError, TypeError):
        raise StopPilot('CURRENT_SCAN_ACCOUNT_RESPONSE_INVALID') from None
    return {'fingerprint': account['subscription_fingerprint'], 'probed_at': now.isoformat()}


def main():
    try:
        result = probe(os.environ.get('CURRENT_SCAN_KEY'))
        with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
            for key, value in result.items():
                output.write(key+'='+value+'\n')
        print('Current Manual/Auto subscription verified via /account; no odds requests.')
        return 0
    except (StopPilot, ValueError, KeyError, TypeError, OSError) as exc:
        # Only our fixed error codes are printed; never raw provider exceptions.
        print(str(exc) if isinstance(exc, StopPilot) else type(exc).__name__)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
