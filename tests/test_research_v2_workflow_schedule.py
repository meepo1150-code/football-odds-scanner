from pathlib import Path


WORKFLOW = Path(".github/workflows/research-v2-scheduled-slot-recovery.yml")


def test_weekday_canonical_slots_have_exact_triggers_and_recovery_heartbeats():
    text = WORKFLOW.read_text()
    assert "- cron: '0 11,14 * * 1-5'" in text
    assert "- cron: '17,47 11 * * 1-5'" in text
    assert "- cron: '17,37,57 14 * * 1-5'" in text


def test_primary_scanner_covers_all_canonical_slots():
    text = Path(".github/workflows/free-research-v2-scanner.yml").read_text()
    assert "- cron: '0 11,14 * * 1-5'" in text
    assert "- cron: '0 5,8,11,12,13,14,15 * * 0,6'" in text
