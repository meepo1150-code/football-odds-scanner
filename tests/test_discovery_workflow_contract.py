"""Retirement contract for the old discovery and mainline observer workflows."""
from pathlib import Path

import yaml


def test_discovery_workflow_has_no_provider_access_or_automatic_trigger():
    assert not Path('.github/workflows/europe-discovery.yml').exists()


def test_core_observer_is_retired_without_quota_requests():
    assert not Path('.github/workflows/v2-mainline-observer.yml').exists()
