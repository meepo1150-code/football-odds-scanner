"""Local-only scheduled recovery gate: never fetch provider data here."""
import json
import os
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BKK = ZoneInfo('Asia/Bangkok')
from .research_v2_slots import targets as canonical_targets, read_ledger, read_snapshots, completed


def due(now, report, event='schedule', fallback=None, ledger_rows=None, snapshots=None):
    if event == 'workflow_dispatch':
        return True  # Explicit manual probes still obey the transport cooldown.
    # Pushes and automatic workflow triggers must obey the same slot/evidence
    # gate as cron; a code change is not permission to collect another quote.
    local = now.astimezone(BKK)
    from .europe_pinnacle_discovery import _football_day_bounds
    targets = [t for t in canonical_targets(_football_day_bounds(now)[2])
               if timedelta(0) <= local-t <= timedelta(minutes=150)]
    if ledger_rows is not None:
        targets = [t for t in targets if not completed(t, local, ledger_rows, snapshots or [])]
    if not targets:
        return False
    for output in (() if ledger_rows is not None else (report, fallback or {})):
        try:
            stamp = datetime.fromisoformat(output['generated_at'].replace('Z', '+00:00'))
            if (output.get('status') == 'RESEARCH_V2_OBSERVED'
                    and output.get('strict_snapshots_this_run', 0) > 0
                    and stamp.tzinfo and max(targets) <= stamp <= now):
                return False
        except (ValueError, TypeError, KeyError):
            pass
    try:
        attempted = datetime.fromisoformat(report['generated_at'].replace('Z', '+00:00'))
        if (attempted.tzinfo and max(targets) <= attempted <= now
                and (ledger_rows is None or report.get('scheduled_target_at') == max(targets).isoformat())):
            return now-attempted >= timedelta(minutes=60)
    except (ValueError, TypeError, KeyError):
        pass
    return True


def needs_finalization(now, ledger_rows, snapshots):
    """Allow one local-only pass to record expired slots as MISSED."""
    from .europe_pinnacle_discovery import _football_day_bounds
    from .research_v2_slots import RECOVERY_MINUTES, stamp
    for target in canonical_targets(_football_day_bounds(now)[2]):
        if now <= target + timedelta(minutes=RECOVERY_MINUTES):
            continue
        if completed(target, now, ledger_rows, snapshots):
            continue
        if not any(stamp(r.get('scheduled_target_at')) == target and
                   r.get('state') == 'MISSED' for r in ledger_rows):
            return True
    return False


if __name__ == '__main__':
    try:
        report = json.loads(Path('reports/pinnwire_research_v2_status.json').read_text())
    except (OSError, ValueError):
        report = {}
    try:
        fallback = json.loads(Path('reports/propline_research_v2_status.json').read_text())
    except (OSError, ValueError):
        fallback = {}
    now = datetime.now(timezone.utc)
    ledger, snapshots = read_ledger(), read_snapshots()
    collect = due(now, report, os.getenv('SCAN_EVENT', 'schedule'), fallback, ledger, snapshots)
    if os.getenv('SCAN_FINALIZE_MISSED') == 'true':
        collect = collect or needs_finalization(now, ledger, snapshots)
    print('collect=' + str(collect).lower())
