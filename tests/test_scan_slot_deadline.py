from datetime import datetime, timedelta, timezone

import pytest

from odds_scanner.scan_slot_deadline import classify


T = datetime(2026, 10, 15, 21, tzinfo=timezone(timedelta(hours=7)))


def test_upcoming():
    assert classify(T, T - timedelta(minutes=1))["state"] == "UPCOMING"


def test_no_snapshot_is_not_success():
    assert classify(T, T + timedelta(minutes=2), active_attempt=True)["state"] == "RUNNING"
    assert classify(T, T + timedelta(minutes=29))["state"] == "RECOVERY_REQUIRED"


def test_deadline_is_inclusive():
    result = classify(T, T + timedelta(minutes=30))
    assert result["state"] == "OVERDUE"
    assert result["alert_required"]


def test_observed_before_deadline():
    result = classify(T, T + timedelta(minutes=31),
                      observed_at=T + timedelta(minutes=20), snapshot_count=38)
    assert result["state"] == "PASS"


def test_late_observation_not_on_time():
    result = classify(T, T + timedelta(minutes=35),
                      observed_at=T + timedelta(minutes=31), snapshot_count=38)
    assert result["state"] == "LATE_OBSERVED"


def test_workflow_success_without_snapshot_cannot_pass():
    assert classify(T, T + timedelta(minutes=30), snapshot_count=0)["state"] == "OVERDUE"


def test_naive_time_rejected():
    with pytest.raises(ValueError):
        classify(T.replace(tzinfo=None), T)


def test_negative_snapshot_count_rejected():
    with pytest.raises(ValueError):
        classify(T, T, snapshot_count=-1)
