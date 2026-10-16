"""Retirement contract for the old discovery and mainline observer workflows."""
from pathlib import Path

import yaml


def test_discovery_workflow_has_no_provider_access_or_automatic_trigger():
    workflow = yaml.safe_load(Path(".github/workflows/europe-discovery.yml").read_text())
    triggers = workflow.get("on", workflow.get(True, {}))
    assert "schedule" not in triggers
    assert "push" not in triggers
    assert all(str(job.get("if", "")).strip() == "${{ false }}" for job in workflow["jobs"].values())
    assert "secrets.ODDSPAPI_KEY" not in str(workflow)


def test_core_observer_is_retired_without_quota_requests():
    workflow = yaml.safe_load(Path(".github/workflows/v2-mainline-observer.yml").read_text())
    triggers = workflow.get("on", workflow.get(True, {}))
    assert "schedule" not in triggers
    assert "workflow_run" not in triggers
    assert all(str(job.get("if", "")).strip() == "${{ false }}" for job in workflow["jobs"].values())
    assert "oddspapi_quota_health" not in str(workflow)
