"""Local-only scheduled recovery gate: never fetch provider data here."""
import json
import os
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BKK = ZoneInfo('Asia/Bangkok')


def due(now, report, event='schedule'):
    if event != 'schedule':
        return True  # Manual/code-change runs still obey the transport cooldown.
    local = now.astimezone(BKK)
    hours = (12, 15, 18, 19, 20, 21, 22) if local.weekday() >= 5 else (18, 21)
    targets = [datetime.combine(local.date(), time(h), BKK) for h in hours]
    targets = [t for t in targets if timedelta(0) <= local-t <= timedelta(minutes=150)]
    if not targets:
        return False
    try:
        attempted = datetime.fromisoformat(report['generated_at'].replace('Z', '+00:00'))
        if attempted.tzinfo and max(targets) <= attempted <= now:
            return False
    except (ValueError, TypeError, KeyError):
        pass
    return True


if __name__ == '__main__':
    try:
        report = json.loads(Path('reports/pinnwire_research_v2_status.json').read_text())
    except (OSError, ValueError):
        report = {}
    print('collect=' + str(due(datetime.now(timezone.utc), report, os.getenv('SCAN_EVENT', 'schedule'))).lower())
