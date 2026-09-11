from pathlib import Path


def test_discovery_workflow_uses_provider_env_contract():
    text = Path('.github/workflows/europe-discovery.yml').read_text(encoding='utf-8')
    assert 'ODDSPAPI_KEY: ${{ secrets.ODDSPAPI_KEY }}' in text
    assert 'ODDSPAPI_API_KEY' not in text


def test_discovery_workflow_has_connector_safe_manual_token_trigger():
    text = Path('.github/workflows/europe-discovery.yml').read_text(encoding='utf-8')
    assert "paths: ['controls/europe_discovery_run_token.txt']" in text
    assert 'branches: [main]' in text
    assert 'evidence commits do not retrigger this workflow' in text


def test_core_observer_refreshes_unmetered_quota_report():
    text = Path('.github/workflows/v2-mainline-observer.yml').read_text(encoding='utf-8')
    assert 'python -m odds_scanner.oddspapi_quota_health' in text
    assert 'reports/oddspapi_quota_health.json' in text
    assert '/account quota refresh is unmetered' in text
