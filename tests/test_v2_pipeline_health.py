import json
from datetime import datetime, timezone
from pathlib import Path

from odds_scanner.v2_pipeline_health import build_pipeline_health

NOW = datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc)


def _write(root: Path, path: str, payload: dict):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload), encoding="utf-8")


def _healthy_inputs(root: Path):
    _write(root, "reports/oddspapi_quota_health.json", {"status": "QUOTA_AVAILABLE", "quota_exhausted": False, "request_limit": 250, "request_count": 63, "request_remaining": 187, "usage_fraction": 0.252, "soccer_sport_id_10_allowed": True, "bet365_allowed": True})
    _write(root, "reports/v2_mainline_observer.json", {"status": "MAINLINE_SNAPSHOTS_OBSERVED", "observed_at": "2026-09-11T01:00:00Z", "requests_attempted": 2, "batch_count": 2, "snapshots_stored": 12})
    _write(root, "reports/v2_forward_entry_status.json", {"status": "COLLECTING_FORWARD_EVIDENCE", "entries_total": 0})
    _write(root, "reports/v2_forward_performance.json", {"status": "NO_FORWARD_ENTRIES", "settled_entries": 0})
    _write(root, "reports/v2_forward_readiness.json", {"status": "COLLECTING_FORWARD_EVIDENCE"})


def test_healthy_collection_is_operational_only(tmp_path):
    _healthy_inputs(tmp_path)
    out = build_pipeline_health(tmp_path, now=NOW)
    assert out["status"] == "HEALTHY_COLLECTING"
    assert out["operational_blockers"] == []
    assert out["production_promotion_allowed"] is False
    assert out["research_gate_effect"].startswith("NONE_")


def test_clean_zero_snapshot_run_is_operationally_healthy_not_research_success(tmp_path):
    _healthy_inputs(tmp_path)
    _write(tmp_path, "reports/v2_mainline_observer.json", {"status": "NO_UNAMBIGUOUS_MAINLINE_SNAPSHOTS", "observed_at": "2026-09-11T01:00:00Z", "requests_attempted": 2, "batch_count": 2, "snapshots_stored": 0, "errors": []})
    out = build_pipeline_health(tmp_path, now=NOW)
    assert out["status"] == "HEALTHY_COLLECTING"
    assert out["observer"]["operational_success"] is True
    assert out["forward"]["readiness_status"] == "COLLECTING_FORWARD_EVIDENCE"
    assert out["production_promotion_allowed"] is False


def test_result_backfill_not_yet_run_is_non_blocking_before_entries(tmp_path):
    _healthy_inputs(tmp_path)
    out = build_pipeline_health(tmp_path, now=NOW)
    assert out["forward"]["entries_total"] == 0
    assert out["forward"]["result_backfill_status"] == "NOT_YET_RUN"
    assert out["status"] == "HEALTHY_COLLECTING"
    assert out["operational_blockers"] == []


def test_observer_batch_failure_is_degraded_not_quota_exhausted(tmp_path):
    _healthy_inputs(tmp_path)
    _write(tmp_path, "reports/v2_mainline_observer.json", {"status": "CURRENT_BATCH_UNAVAILABLE", "generated_at": "2026-09-11T01:14:00Z", "failed_universe": "THIRD_UNIVERSE_OU", "errors": ["HTTPError: HTTP Error 429: Too Many Requests"]})
    out = build_pipeline_health(tmp_path, now=NOW)
    assert out["status"] == "OBSERVER_DEGRADED"
    assert "ODDSPAPI_MONTHLY_QUOTA_EXHAUSTED" not in out["operational_blockers"]
    assert any("CURRENT_BATCH_UNAVAILABLE" in x for x in out["operational_blockers"])


def test_missing_quota_health_is_unknown_not_exhausted(tmp_path):
    _healthy_inputs(tmp_path)
    (tmp_path / "reports/oddspapi_quota_health.json").unlink()
    out = build_pipeline_health(tmp_path, now=NOW)
    assert out["status"] == "HEALTH_UNKNOWN"
    assert "ODDSPAPI_QUOTA_HEALTH_UNAVAILABLE" in out["operational_blockers"]
    assert "ODDSPAPI_MONTHLY_QUOTA_EXHAUSTED" not in out["operational_blockers"]


def test_monthly_quota_exhaustion_is_distinct_blocker(tmp_path):
    _healthy_inputs(tmp_path)
    _write(tmp_path, "reports/oddspapi_quota_health.json", {"status": "QUOTA_EXHAUSTED", "quota_exhausted": True, "request_limit": 250, "request_count": 250, "request_remaining": 0, "soccer_sport_id_10_allowed": True, "bet365_allowed": True})
    out = build_pipeline_health(tmp_path, now=NOW)
    assert out["status"] == "BLOCKED_QUOTA"
    assert "ODDSPAPI_MONTHLY_QUOTA_EXHAUSTED" in out["operational_blockers"]


def test_stale_observer_is_explicit(tmp_path):
    _healthy_inputs(tmp_path)
    _write(tmp_path, "reports/v2_mainline_observer.json", {"status": "MAINLINE_SNAPSHOTS_OBSERVED", "observed_at": "2026-09-10T00:00:00Z"})
    out = build_pipeline_health(tmp_path, now=NOW)
    assert out["status"] == "OBSERVER_STALE"
    assert "MAINLINE_OBSERVER_STALE" in out["operational_blockers"]
