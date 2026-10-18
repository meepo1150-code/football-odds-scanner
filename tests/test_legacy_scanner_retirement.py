"""Contract tests for retirement of the legacy odds collector.

These tests intentionally preserve result backfills, statistics and historical
data while preventing a retired odds workflow from making provider requests.
"""
from pathlib import Path

import yaml

WORKFLOWS = Path(".github/workflows")
RETIRED = (
    "live-scan.yml",
    "scanner.yml",
    "free-research-v2-scanner.yml",
    "research-v2-scheduled-slot-recovery.yml",
    "research-v2-slot-watchdog.yml",
    "europe-pinnacle-daily-discovery.yml",
    "five-dollar-archive.yml",
    "pinnwire-probe.yml",
    "oddspapi-history-archive.yml",
    "master-schedule-manual-recovery.yml",
    "scan-health-monitor.yml",
    "v2-pipeline-health.yml",
)


def test_retired_workflows_have_no_runnable_jobs_or_schedules():
    for filename in RETIRED:
        if not (WORKFLOWS / filename).exists():
            continue  # Deleted entrypoint cannot execute.
        workflow = yaml.safe_load((WORKFLOWS / filename).read_text())
        events = workflow.get("on", workflow.get(True, {}))
        assert "schedule" not in events, filename
        assert "push" not in events, filename
        assert "workflow_run" not in events, filename
        jobs = workflow["jobs"]
        assert jobs, filename
        for job in jobs.values():
            assert str(job.get("if", "")).strip() == "${{ false }}", filename
            for step in job.get("steps", []):
                assert "ODDSPAPI_KEY" not in str(step), filename
                assert "PROPLINE_API_KEY" not in str(step), filename


def test_results_statistics_and_dashboard_workflows_are_retained():
    for filename in (
        "research-v2-free-result-backfill.yml",
        "research-v2-result-backfill.yml",
        "v2-forward-result-backfill.yml",
        "research-v2-market-state-stats.yml",
        "research-v2-offline-evidence.yml",
        "pages.yml",
    ):
        workflow = yaml.safe_load((WORKFLOWS / filename).read_text())
        assert workflow.get("jobs"), filename


def test_historical_evidence_and_statistics_remain_present():
    for filename in (
        "data/normalized/europe_pinnacle_research_v2_snapshots.jsonl",
        "data/normalized/v2_forward_settlements.jsonl",
        "reports/research_v2_pattern_statistics.json",
        "reports/v2_forward_performance.json",
    ):
        assert Path(filename).is_file(), filename
