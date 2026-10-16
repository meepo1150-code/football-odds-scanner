import copy
from pathlib import Path

import pytest
import yaml

from odds_scanner.historical_manual.publish_gate import classify


def receipt(status="NO_VERIFIED_FIXTURES"):
    return {
        "status": status,
        "research_only": True,
        "run_url": "https://github.com/acme/repo/actions/runs/123",
        "results": [],
        "errors": [],
        "historical_requests": 0,
        "account_requests": 0,
        "production_writes": 0,
        "plan": {
            "unique_fixtures": 0,
            "fixture_bookmaker_pairs": 0,
            "requested_target_slots": 0,
            "planned_historical_requests": 0,
        },
    }


def test_empty_verified_manifest_is_noop_not_deploy():
    assert classify(receipt(), "123") is False


def test_completed_scan_can_publish():
    assert classify(receipt("COMPLETED"), "123") is True


@pytest.mark.parametrize("status", ["STOPPED", "BLOCKED", "PARTIAL_CACHE_MISS", "PLANNED"])
def test_noncompleted_scan_still_fails_closed(status):
    with pytest.raises(ValueError, match="HISTORICAL_SCAN_NOT_COMPLETED"):
        classify(receipt(status), "123")


@pytest.mark.parametrize("change", [
    {"research_only": False},
    {"run_url": "https://github.com/acme/repo/actions/runs/456"},
    {"historical_requests": 1},
    {"account_requests": 1},
    {"production_writes": 1},
    {"errors": ["FAILED"]},
    {"results": [{"fixture_id": "id1"}]},
    {"plan": {"unique_fixtures": 1}},
])
def test_false_empty_evidence_rejected(change):
    report = receipt()
    if "plan" in change:
        report["plan"].update(change["plan"])
    else:
        report.update(change)
    with pytest.raises(ValueError):
        classify(report, "123")


def test_workflow_keeps_manual_collector_and_gates_all_publication_steps():
    workflow = yaml.safe_load(Path(".github/workflows/manual-historical-scan.yml").read_text())
    steps = workflow["jobs"]["publish"]["steps"]
    gate = next(s for s in steps if s.get("id") == "artifact_gate")
    assert "publish_gate" in gate["run"]
    assert "historical_manual.runner" not in gate["run"]
    published = [
        s for s in steps if s.get("name") in {
            "Validate, import, and rebuild main statistics (offline)",
            "Commit data and regenerated statistics, preserving other main changes",
            "Explicitly dispatch Pages deployment after publish",
        }
    ]
    assert len(published) == 3
    assert all(s.get("if") == "steps.artifact_gate.outputs.publish == 'true'" for s in published)
    assert workflow["jobs"]["historical"]["environment"] == "historical-research"
