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
    "api-football-shadow.yml",
    "breadth.yml",
    "europe-pinnacle-coverage-probe.yml",
    "five-dollar-research.yml",
    "fotmob-pinnwire-coverage-probe.yml",
    "global-expansion-matchday-probe.yml",
    "independent-league-confirmation.yml",
    "master-provider-snapshot.yml",
    "multiseason-market-validation.yml",
    "oddspapi-health.yml",
    "oddspapi-market-catalog-refresh.yml",
    "oddspapi-quota-health.yml",
    "oddspapi-v5-score-probe.yml",
    "prospective-2026-27.yml",
    "provider-health.yml",
    "research-v2-results.yml",
    "research.yml",
    "resolve-research-universe.yml",
    "third-universe-ou-confirmation.yml",
    "v2-ah-marker-probe.yml",
)


def test_retired_workflow_entrypoint_files_are_deleted():
    for filename in RETIRED:
        assert not (WORKFLOWS / filename).exists(), filename


def test_retired_auto_panel_is_not_loaded_or_built():
    assert not Path('apps/dashboard/automatic-rounds.js').exists()
    for filename in ('apps/dashboard/index.html', 'apps/dashboard/monitor.html',
                     '.github/workflows/pages.yml'):
        assert 'automatic-rounds.js' not in Path(filename).read_text(), filename
    assert 'collection-health.js' in Path('apps/dashboard/monitor.html').read_text()
    # Retiring the old UI must not erase the evidence it used to display.
    for filename in ('reports/automatic_scan_latest.json',
                     'data/normalized/automatic_scan_slots.jsonl'):
        assert Path(filename).is_file(), filename


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
