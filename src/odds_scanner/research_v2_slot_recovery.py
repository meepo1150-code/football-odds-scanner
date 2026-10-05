"""Recover all elapsed slots using actual late observations, never old prices."""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from .research_v2_slots import RECOVERY_MINUTES, read_ledger, targets, valid_completion
from .europe_pinnacle_discovery import run as primary, _football_day_bounds, _record_slot, SLOT_LEDGER_PATH
from .propline_research_v2 import run as fallback


def run(root=Path('.'), now=None):
    now = now or datetime.now(timezone.utc)
    day = _football_day_bounds(now)[2]
    results = []
    for target in targets(day):
        if target > now:
            continue
        ledger = read_ledger(root)
        if any(valid_completion(row, target, now) for row in ledger):
            continue
        lag = (now-target).total_seconds()/60
        if lag > RECOVERY_MINUTES:
            if not any(row.get('scheduled_target_at') == target.isoformat() and row.get('state') == 'MISSED' for row in ledger):
                _record_slot(root/SLOT_LEDGER_PATH, {'scheduled_target_at':target.isoformat(),
                             'football_day':day,'generated_at':now.isoformat(),
                             'schedule_lag_minutes':lag,'status':'RECOVERY_WINDOW_EXPIRED',
                             'observation_timing':'OUTSIDE_WINDOW','requests_used':0}, 'MISSED')
            continue
        # A successful newer slot cannot suppress this older recoverable target.
        # The observed timestamp remains the actual fetch time and is labelled LATE.
        with patch.dict(os.environ, {'RESEARCH_V2_FORCE_RUN':'true',
                                     'RESEARCH_V2_FORCE_TARGET_AT':target.isoformat()}):
            report = primary(root)
        if not any(valid_completion(row, target, datetime.now(timezone.utc)) for row in read_ledger(root)):
            report = fallback(root, target_at=target)
        results.append(report)
    return results


if __name__ == '__main__':
    print(json.dumps(run()))
