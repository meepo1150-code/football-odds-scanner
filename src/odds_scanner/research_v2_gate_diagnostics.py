"""Read-only explanation of canonical slot gating; never contacts providers."""
from datetime import timedelta
from .research_v2_slots import completed, provider_attempt_receipt, stamp


def explain(now, targets, ledger_rows, snapshots):
    """Return one mutually exclusive reason and target; no side effects."""
    elapsed = [t for t in targets if timedelta(0) <= now - t <= timedelta(minutes=150)]
    if not elapsed:
        return {"collect": False, "reason": "NOT_DUE_OR_EXPIRED", "target": None}
    target = max(elapsed)
    if completed(target, now, ledger_rows, snapshots):
        return {"collect": False, "reason": "ALREADY_OBSERVED", "target": target.isoformat()}
    receipts = [stamp(r.get("request_completed_at") or r.get("actual_observed_at"))
                for r in ledger_rows if provider_attempt_receipt(r)]
    receipts = [t for t in receipts if t and timedelta(0) <= now - t < timedelta(minutes=15)]
    if receipts:
        return {"collect": False, "reason": "TRANSPORT_COOLDOWN", "target": target.isoformat()}
    attempts = [stamp(r.get("request_completed_at") or r.get("actual_observed_at"))
                for r in ledger_rows if provider_attempt_receipt(r)
                and (r.get("requests_used", 0) or r.get("http_requests_attempted", 0))
                and stamp(r.get("scheduled_target_at")) == target]
    attempts = [t for t in attempts if t and timedelta(0) <= now - t < timedelta(minutes=60)]
    if attempts:
        return {"collect": False, "reason": "SLOT_RETRY_COOLDOWN", "target": target.isoformat()}
    return {"collect": True, "reason": "ELIGIBLE_FOR_COLLECTION", "target": target.isoformat()}
