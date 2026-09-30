"""Fail-closed, local request budget shared by all OddsPapi transports.

/account remains accessible when exhausted. /historical-odds costs zero but
is still blocked at exhaustion. All other endpoints cost one request.
Source: https://oddspapi.io/us/docs/requests-and-quota (verified 2026-09-29).
"""
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

_LOCK = threading.Lock()
_ACCOUNT = None
_SPENT = 0
_BLOCKED = False


class QuotaBlocked(RuntimeError):
    pass


def observe_account(account):
    global _ACCOUNT, _SPENT, _BLOCKED
    if not isinstance(account, dict):
        return
    # Same account shapes used by the provider's safe account summary.
    from .oddspapi_provider import _safe_account_summary
    summary = _safe_account_summary(account)
    with _LOCK:
        _ACCOUNT = summary
        _SPENT = 0
        _BLOCKED = False


def block_metered_requests():
    global _BLOCKED
    with _LOCK:
        _BLOCKED = True


def reserve_request(path, root=Path('.')):
    global _SPENT
    if path.rstrip('/') == '/account':
        return
    with _LOCK:
        if _BLOCKED:
            raise QuotaBlocked('ODDSPAPI_RATE_LIMITED: no more metered calls in this run')
        account = _ACCOUNT
        if account is None:
            try:
                account = json.loads((root / 'reports/oddspapi_quota_health.json').read_text())
                stamp = datetime.fromisoformat(account['generated_at'].replace('Z', '+00:00'))
                age = (datetime.now(timezone.utc) - stamp).total_seconds()
                # Exhausted stays blocked until the unmetered account refresh proves reset.
                if account.get('status') != 'QUOTA_EXHAUSTED' and not 0 <= age <= 86400:
                    raise ValueError('stale quota report')
            except (OSError, ValueError, KeyError, TypeError):
                raise QuotaBlocked('ODDSPAPI_QUOTA_UNKNOWN: refresh unmetered /account first') from None
        try:
            remaining = int(account['request_limit']) - int(account['request_count']) - _SPENT
        except (KeyError, TypeError, ValueError):
            raise QuotaBlocked('ODDSPAPI_QUOTA_UNKNOWN') from None
        if account.get('active_subscription') is not True or remaining <= 0:
            raise QuotaBlocked('ODDSPAPI_EXTERNALLY_QUOTA_BLOCKED: no metered request sent')
        # Reserve before transport, including failures: quota semantics for failed
        # requests are not guaranteed, so do not refund them speculatively.
        if path.rstrip("/") != "/historical-odds":
            _SPENT += 1
