from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from odds_scanner.scan_slot_deadline_report import report

BKK = timezone(timedelta(hours=7))
T = datetime(2026, 10, 15, 21, tzinfo=BKK)


def test_missing_slot_after_30_minutes_is_overdue():
    with patch("odds_scanner.scan_slot_deadline_report.read_ledger", return_value=[]), \
         patch("odds_scanner.scan_slot_deadline_report.read_snapshots", return_value=[]):
        data = report(now=T + timedelta(minutes=31), football_day="2026-10-15")
    slot = next(s for s in data["slots"] if s["scheduled_target_at"] == T.isoformat())
    assert slot["state"] == "OVERDUE"
    assert slot["snapshot_count"] == 0
    assert slot["alert_required"]


def test_zero_quote_completion_does_not_claim_price_pass():
    ledger = [{"scheduled_target_at": T.isoformat(), "state": "ZERO_COHORT",
               "collection_succeeded": True, "football_day_fixtures": 0,
               "actual_observed_at": (T + timedelta(minutes=5)).isoformat()}]
    with patch("odds_scanner.scan_slot_deadline_report.read_ledger", return_value=ledger), \
         patch("odds_scanner.scan_slot_deadline_report.read_snapshots", return_value=[]):
        data = report(now=T + timedelta(minutes=31), football_day="2026-10-15")
    slot = next(s for s in data["slots"] if s["scheduled_target_at"] == T.isoformat())
    assert slot["state"] == "OVERDUE"
