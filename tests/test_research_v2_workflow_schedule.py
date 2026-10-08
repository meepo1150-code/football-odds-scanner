from pathlib import Path


WORKFLOW = Path(".github/workflows/research-v2-scheduled-slot-recovery.yml")


def test_weekday_canonical_slots_have_exact_triggers_and_recovery_heartbeats():
    text = WORKFLOW.read_text()
    assert "- cron: '0 11,14 * * 1-5'" in text
    assert "- cron: '17,47 11,12,13 * * 1-5'" in text
    assert "- cron: '17,37,57 14 * * 1-5'" in text
    assert "- cron: '17,37,57 15,16 * * 1-5'" in text


def test_primary_scanner_covers_all_canonical_slots():
    text = Path(".github/workflows/free-research-v2-scanner.yml").read_text()
    assert "- cron: '0 11,14 * * 1-5'" in text
    assert "- cron: '0 5,8,11,12,13,14,15 * * 0,6'" in text


def test_primary_scanner_uses_guarded_provider_fallback_collector():
    text = Path(".github/workflows/free-research-v2-scanner.yml").read_text()
    assert "python -m odds_scanner.research_v2_slot_recovery" in text
    assert "ODDSPAPI_KEY:" in text
    assert "PROPLINE_API_KEY:" in text
    assert "python -m odds_scanner.propline_research_v2" not in text


def test_primary_scanner_gates_provider_and_rebuild_work_when_not_due():
    text = Path(".github/workflows/free-research-v2-scanner.yml").read_text()
    assert "python -m odds_scanner.research_v2_scan_due" in text
    assert "id: due" in text
    assert text.count("if: steps.due.outputs.collect == 'true'") >= 4


def test_watchdog_gates_expensive_steps_but_keeps_missed_slot_finalization():
    text = Path('.github/workflows/research-v2-slot-watchdog.yml').read_text()
    assert "SCAN_FINALIZE_MISSED: 'true'" in text
    assert text.count("if: steps.due.outputs.collect == 'true'") == 5
    assert text.index('id: due') < text.index('actions/setup-python')


def test_watchdog_event_fallback_is_main_only_and_has_no_self_loop():
    import yaml
    text = Path('.github/workflows/research-v2-slot-watchdog.yml').read_text()
    data = yaml.safe_load(text)
    triggers = data.get('on', data.get(True))
    upstream = triggers['workflow_run']
    assert upstream['workflows'] == ['Live Odds Scan', 'Validation v2 Pipeline Health']
    assert upstream['branches'] == ['main']
    assert upstream['types'] == ['completed']
    assert data['name'] not in upstream['workflows']
    assert "event != 'pull_request'" in data['jobs']['recover']['if']
    assert 'with: {ref: main}' in text
    assert "SCAN_EVENT: ${{ github.event_name }}" in text


def test_watchdog_upstreams_do_not_subscribe_back_to_watchdog():
    import yaml
    for path in ('.github/workflows/live-scan.yml', '.github/workflows/v2-pipeline-health.yml'):
        data = yaml.safe_load(Path(path).read_text())
        triggers = data.get('on', data.get(True))
        assert 'Research V2 Independent Slot Watchdog' not in triggers.get('workflow_run', {}).get('workflows', [])
