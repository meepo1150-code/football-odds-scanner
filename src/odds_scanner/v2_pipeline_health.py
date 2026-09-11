from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

QUOTA_PATH = Path("reports/oddspapi_quota_health.json")
OBSERVER_PATH = Path("reports/v2_mainline_observer.json")
ENTRY_PATH = Path("reports/v2_forward_entry_status.json")
RESULT_PATH = Path("reports/v2_forward_result_backfill.json")
PERFORMANCE_PATH = Path("reports/v2_forward_performance.json")
READINESS_PATH = Path("reports/v2_forward_readiness.json")
REPORT_PATH = Path("reports/v2_pipeline_health.json")
OBSERVER_STALE_AFTER = timedelta(hours=18)


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _utc(value) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def build_pipeline_health(root: Path = Path("."), *, now: datetime | None = None) -> dict:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    quota = _load(root / QUOTA_PATH)
    observer = _load(root / OBSERVER_PATH)
    entry = _load(root / ENTRY_PATH)
    result = _load(root / RESULT_PATH)
    performance = _load(root / PERFORMANCE_PATH)
    readiness = _load(root / READINESS_PATH)

    quota_status = str(quota.get("status") or "UNAVAILABLE")
    quota_available = quota_status == "QUOTA_AVAILABLE" and quota.get("quota_exhausted") is False
    required_access = quota.get("soccer_sport_id_10_allowed", True) is not False and quota.get("bet365_allowed", True) is not False

    observer_status = str(observer.get("status") or "UNAVAILABLE")
    observed_at = _utc(observer.get("observed_at") or observer.get("generated_at"))
    observer_age_hours = (current - observed_at).total_seconds() / 3600.0 if observed_at else None
    observer_stale = observer_age_hours is None or observer_age_hours > OBSERVER_STALE_AFTER.total_seconds() / 3600.0
    observer_success = observer_status == "MAINLINE_SNAPSHOTS_OBSERVED"

    blockers: list[str] = []
    if quota_status == "QUOTA_EXHAUSTED":
        blockers.append("ODDSPAPI_MONTHLY_QUOTA_EXHAUSTED")
    elif not quota_available:
        blockers.append("ODDSPAPI_QUOTA_HEALTH_UNAVAILABLE")
    if not required_access:
        blockers.append("ODDSPAPI_REQUIRED_SOCCER_OR_BET365_ACCESS_MISSING")
    if observer_stale:
        blockers.append("MAINLINE_OBSERVER_STALE")
    if not observer_success:
        blockers.append(f"MAINLINE_OBSERVER_{observer_status}")

    if "ODDSPAPI_MONTHLY_QUOTA_EXHAUSTED" in blockers:
        status = "BLOCKED_QUOTA"
    elif not required_access:
        status = "BLOCKED_PROVIDER_CAPABILITY"
    elif observer_stale:
        status = "OBSERVER_STALE"
    elif not observer_success:
        status = "OBSERVER_DEGRADED"
    elif quota_available:
        status = "HEALTHY_COLLECTING"
    else:
        status = "HEALTH_UNKNOWN"

    payload = {
        "schema_version": "1.0",
        "classification": "VALIDATION_V2_OPERATIONAL_PIPELINE_HEALTH",
        "status": status,
        "generated_at": current.isoformat(),
        "research_gate_effect": "NONE_OPERATIONAL_HEALTH_DOES_NOT_CHANGE_FROZEN_FORWARD_GATES",
        "quota": {
            "status": quota_status,
            "request_limit": quota.get("request_limit"),
            "request_count": quota.get("request_count"),
            "request_remaining": quota.get("request_remaining"),
            "usage_fraction": quota.get("usage_fraction"),
            "quota_exhausted": quota.get("quota_exhausted"),
            "soccer_sport_id_10_allowed": quota.get("soccer_sport_id_10_allowed"),
            "bet365_allowed": quota.get("bet365_allowed"),
            "generated_at": quota.get("generated_at"),
        },
        "observer": {
            "status": observer_status,
            "generated_at": observer.get("generated_at"),
            "observed_at": observer.get("observed_at"),
            "age_hours": observer_age_hours,
            "stale_after_hours": OBSERVER_STALE_AFTER.total_seconds() / 3600.0,
            "stale": observer_stale,
            "failed_universe": observer.get("failed_universe"),
            "errors": (observer.get("errors") or [])[:3],
            "requests_attempted": observer.get("requests_attempted"),
            "snapshots_stored": observer.get("snapshots_stored"),
        },
        "forward": {
            "entry_status": entry.get("status") or "UNAVAILABLE",
            "entries_total": entry.get("entries_total"),
            "entries_with_exact_external_ids": entry.get("entries_with_exact_external_ids"),
            "result_backfill_status": result.get("status") or "NOT_YET_RUN",
            "result_requests_attempted": result.get("requests_attempted"),
            "settled_entries": performance.get("settled_entries"),
            "performance_status": performance.get("status") or "UNAVAILABLE",
            "readiness_status": readiness.get("status") or "UNAVAILABLE",
        },
        "operational_blockers": blockers,
        "paper_label": "PAPER_RESEARCH_ONLY",
        "production_promotion_allowed": False,
    }
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_pipeline_health(), ensure_ascii=False))
