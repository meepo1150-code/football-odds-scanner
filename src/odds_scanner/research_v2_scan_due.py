"""Local-only scheduled recovery gate: never fetch provider data here."""
import json
import os
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BKK = ZoneInfo('Asia/Bangkok')


def due(now, report, event='schedule', fallback=None, ledger_rows=None):
    if event != 'schedule':
        return True  # Manual/code-change runs still obey the transport cooldown.
    local = now.astimezone(BKK)
    hours = (12, 15, 18, 19, 20, 21, 22) if local.weekday() >= 5 else (18, 21)
    targets = [datetime.combine(local.date(), time(h), BKK) for h in hours]
    targets = [t for t in targets if timedelta(0) <= local-t <= timedelta(minutes=150)]
    if ledger_rows:
        done={str(x.get('scheduled_target_at')) for x in ledger_rows if str(x.get('state')) in {'OBSERVED','ZERO_FIXTURES'}}
        targets=[t for t in targets if t.isoformat() not in done]
    if not targets:
        return False
    for output in (report, fallback or {}):
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
        if attempted.tzinfo and max(targets) <= attempted <= now:
            return now-attempted >= timedelta(minutes=60)
    except (ValueError, TypeError, KeyError):
        pass
    return True


if __name__ == '__main__':
    try:
        report = json.loads(Path('reports/pinnwire_research_v2_status.json').read_text())
    except (OSError, ValueError):
        report = {}
    try:
        fallback = json.loads(Path('reports/propline_research_v2_status.json').read_text())
    except (OSError, ValueError):
        fallback = {}
    ledger=[]
    try:
        for line in Path('data/normalized/research_v2_slot_ledger.jsonl').read_text().splitlines():
            try: ledger.append(json.loads(line))
            except json.JSONDecodeError: pass
    except OSError:
        pass
    print('collect=' + str(due(datetime.now(timezone.utc), report, os.getenv('SCAN_EVENT', 'schedule'), fallback, ledger)).lower())
