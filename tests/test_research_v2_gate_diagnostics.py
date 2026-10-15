"""Read-only slot diagnostic regressions: no provider calls or production mutation."""
from datetime import datetime, timedelta, timezone
from odds_scanner.research_v2_gate_diagnostics import explain


def test_not_due_does_not_collect():
    t = datetime(2026, 10, 15, 8, 0, tzinfo=timezone.utc)
    assert explain(t-timedelta(minutes=1), [t], [], [])["reason"] == "NOT_DUE_OR_EXPIRED"


def test_expired_does_not_collect():
    t = datetime(2026, 10, 15, 8, 0, tzinfo=timezone.utc)
    assert explain(t+timedelta(minutes=151), [t], [], [])["collect"] is False


def test_eligible_slot_explained_without_provider_call():
    t = datetime(2026, 10, 15, 8, 0, tzinfo=timezone.utc)
    assert explain(t+timedelta(minutes=3), [t], [], []) == {
        "collect": True, "reason": "ELIGIBLE_FOR_COLLECTION", "target": t.isoformat()
    }
