"""Legacy schedule retirement contracts.

The former scanner schedule and fallback orchestration must not run.  These
checks replace the obsolete expectation that collection remains scheduled.
"""
from pathlib import Path

import yaml


RETIRED = (
    "europe-pinnacle-daily-discovery",
    "research-v2-scheduled-slot-recovery",
    "research-v2-slot-watchdog",
    "free-research-v2-scanner",
    "live-scan",
    "scanner",
    "v2-mainline-observer",
)


def test_all_legacy_scanner_entrypoints_are_disabled():
    for name in RETIRED:
        if not Path(".github/workflows", name + ".yml").exists():
            continue  # Deleted entrypoint cannot execute.
        workflow = yaml.safe_load(Path(".github/workflows", name + ".yml").read_text())
        triggers = workflow.get("on", workflow.get(True, {}))
        assert "schedule" not in triggers, name
        assert "push" not in triggers, name
        assert "workflow_run" not in triggers, name
        assert all(
            str(job.get("if", "")).strip() == "${{ false }}"
            for job in workflow["jobs"].values()
        ), name


def test_legacy_scanner_has_no_provider_credentials_or_collector_commands():
    for name in RETIRED:
        if not Path(".github/workflows", name + ".yml").exists():
            continue
        text = Path(".github/workflows", name + ".yml").read_text()
        for forbidden in (
            "secrets.ODDSPAPI_KEY",
            "secrets.PROPLINE_API_KEY",
            "python -m odds_scanner.research_v2_slot_recovery",
            "python -m odds_scanner.research_v2_scan_due",
        ):
            assert forbidden not in text, (name, forbidden)


def test_previous_day_result_recovery_remains_active():
    workflow = yaml.safe_load(Path(".github/workflows/daily-preparation-scan.yml").read_text())
    assert "previous-day-results" in workflow["jobs"]
    assert "first-odds-snapshot" not in workflow["jobs"]
    steps = workflow["jobs"]["previous-day-results"]["steps"]
    assert any("daily_preparation" in str(step.get("run", "")) for step in steps)
