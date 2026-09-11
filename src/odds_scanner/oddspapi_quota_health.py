from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .oddspapi_provider import ENV_KEY, _get, _safe_account_summary

REPORT_PATH = Path("reports/oddspapi_quota_health.json")


def summarize_account(account: dict) -> dict:
    safe = _safe_account_summary(account)
    active = safe.get("active_subscription") is True
    sports = safe.get("sport_ids") if isinstance(safe.get("sport_ids"), list) else []
    bookmakers = safe.get("bookmakers") if isinstance(safe.get("bookmakers"), list) else []
    base = {
        "active_subscription": active,
        "request_limit": safe.get("request_limit"),
        "request_count": safe.get("request_count"),
        "rate_limit": safe.get("rate_limit"),
        "soccer_sport_id_10_allowed": 10 in sports,
        "bet365_allowed": "bet365" in bookmakers,
        "allowed_sport_count": len(sports),
        "allowed_bookmaker_count": len(bookmakers),
    }
    if not active:
        return {"status": "NO_ACTIVE_SUBSCRIPTION", **base}
    try:
        limit_i = int(base["request_limit"])
        count_i = int(base["request_count"])
    except (TypeError, ValueError):
        return {"status": "USAGE_FIELDS_UNAVAILABLE", **base}
    remaining = max(0, limit_i - count_i)
    usage = (count_i / limit_i) if limit_i > 0 else None
    return {
        "status": "QUOTA_EXHAUSTED" if remaining == 0 else "QUOTA_AVAILABLE",
        **base,
        "request_remaining": remaining,
        "usage_fraction": usage,
        "quota_exhausted": remaining == 0,
    }


def check_from_env(root: Path = Path(".")) -> dict:
    generated_at = datetime.now(timezone.utc).isoformat()
    key = os.getenv(ENV_KEY)
    if not key:
        payload = {
            "schema_version": "1.1",
            "provider": "oddspapi",
            "status": "API_KEY_NOT_CONFIGURED",
            "generated_at": generated_at,
            "account_endpoint_metered": False,
        }
        return _write(root, payload)
    try:
        account = _get("/account", key)
        summary = summarize_account(account if isinstance(account, dict) else {})
        payload = {
            "schema_version": "1.1",
            "provider": "oddspapi",
            "generated_at": generated_at,
            "account_endpoint_metered": False,
            **summary,
        }
    except Exception as exc:
        payload = {
            "schema_version": "1.1",
            "provider": "oddspapi",
            "status": "ACCOUNT_UNAVAILABLE",
            "generated_at": generated_at,
            "account_endpoint_metered": False,
            "errors": [f"{type(exc).__name__}: {exc}"],
        }
    return _write(root, payload)


def _write(root: Path, payload: dict) -> dict:
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(check_from_env(), ensure_ascii=False))
