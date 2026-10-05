from pathlib import Path


WORKFLOW = Path(".github/workflows/research-v2-scheduled-slot-recovery.yml")


def test_weekday_canonical_slots_have_exact_triggers_and_recovery_heartbeats():
    text = WORKFLOW.read_text()
    assert "- cron: '0 11,14 * * 1-5'" in text
    assert "- cron: '17,47 11 * * 1-5'" in text
    assert "- cron: '17,37,57 14 * * 1-5'" in text
