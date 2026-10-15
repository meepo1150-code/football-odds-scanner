"""Read-only scan deadline report from durable canonical evidence.

No provider requests, history mutation, or quota reservation.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .research_v2_slots import (
    read_ledger, read_snapshots, targets, target_football_day,
    matched_snapshots, completed, stamp,
)
from .scan_slot_deadline import classify


def report(now=None, root=Path("."), football_day=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    from .europe_pinnacle_discovery import _football_day_bounds
    day = football_day or _football_day_bounds(now)[2]
    ledger, snapshots = read_ledger(root), read_snapshots(root)
    rows = []
    for target in targets(day):
        matched = matched_snapshots(target, now, snapshots)
        valid = completed(target, now, ledger, snapshots)
        # An OBSERVED receipt with a verified cohort but zero individual
        # valid quotes must not be advertised as a successful price scan.
        observed = max((stamp(s.get("observed_at")) for s in matched), default=None)
        rows_for_slot = [r for r in ledger if stamp(r.get("scheduled_target_at")) == target]
        attempts = [r for r in rows_for_slot if r.get("state") not in ("OBSERVED", "ZERO_FIXTURES", "ZERO_COHORT")]
        failure = next((str(r.get("status") or r.get("state")) for r in reversed(attempts)
                        if r.get("status") or r.get("state")), None)
        item = classify(target, now, observed_at=observed,
                        snapshot_count=len(matched), failure_reason=failure)
        item["canonical_fixture_count"] = len({s.get("fixture_id") for s in matched})
        item["football_day"] = target_football_day(target)
        item["ledger_completion"] = bool(valid)
        item["provider"] = matched[-1].get("provider") if matched else None
        rows.append(item)
    return {"generated_at": now.isoformat(), "football_day": str(day),
            "slots": rows, "overdue_count": sum(r["state"] == "OVERDUE" for r in rows)}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only 30-minute canonical slot deadline audit")
    parser.add_argument("--football-day", default=None)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)
    result = report(root=Path(args.root), football_day=args.football_day)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\\n"
    if args.output:
        Path(args.output).write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
