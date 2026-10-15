"""Pure, read-only 30-minute scan deadline classifier.

This module never calls providers or modifies quota/slot history.
A completed GitHub workflow is not proof of an observed odds snapshot.
"""
from datetime import datetime, timedelta


def classify(target: datetime, now: datetime, *, observed_at=None,
             snapshot_count=0, active_attempt=False, failure_reason=None):
    """Return a machine-readable deadline state for one canonical slot.

    All timestamps must be timezone-aware. Late observations remain late;
    a later recovery cannot be presented as on-time.
    """
    if target.tzinfo is None or now.tzinfo is None:
        raise ValueError("target and now must be timezone-aware")
    if observed_at is not None and observed_at.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")
    if snapshot_count < 0:
        raise ValueError("snapshot_count cannot be negative")
    deadline = target + timedelta(minutes=30)
    if observed_at is not None and snapshot_count > 0:
        state = "PASS" if target <= observed_at <= deadline else "LATE_OBSERVED"
    elif now < target:
        state = "UPCOMING"
    elif now >= deadline:
        state = "OVERDUE"
    elif failure_reason:
        state = "RECOVERY_REQUIRED"
    elif active_attempt:
        state = "RUNNING"
    else:
        state = "RECOVERY_REQUIRED"
    return {
        "scheduled_target_at": target.isoformat(),
        "deadline_at": deadline.isoformat(),
        "checked_at": now.isoformat(),
        "observed_at": observed_at.isoformat() if observed_at else None,
        "snapshot_count": snapshot_count,
        "state": state,
        "alert_required": state in {"PASS", "LATE_OBSERVED", "OVERDUE", "RECOVERY_REQUIRED"},
        "failure_reason": failure_reason,
    }
