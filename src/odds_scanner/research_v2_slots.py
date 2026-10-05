"""Canonical Bangkok collection slots and persisted evidence validation."""
import json
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BKK = ZoneInfo('Asia/Bangkok')
RECOVERY_MINUTES = 150
LEDGER = Path('data/normalized/research_v2_slot_ledger.jsonl')


def stamp(value):
    try:
        result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return result.astimezone(BKK) if result.tzinfo else None
    except (ValueError, TypeError):
        return None


def targets(day):
    if isinstance(day, str):
        day = datetime.fromisoformat(day).date()
    hours = (12, 15, 18, 19, 20, 21, 22) if day.weekday() >= 5 else (18, 21)
    return [datetime.combine(day, time(hour), BKK) for hour in hours]


def read_ledger(root=Path('.')):
    path = root / LEDGER
    rows = []
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
            except ValueError:
                continue
    return rows


def valid_completion(row, target, now):
    observed = stamp(row.get('actual_observed_at') or row.get('observed_at'))
    if stamp(row.get('scheduled_target_at')) != target or observed is None:
        return False
    if not target <= observed <= min(now, target + timedelta(minutes=RECOVERY_MINUTES)):
        return False
    state = row.get('state')
    if state == 'OBSERVED':
        return (row.get('strict_snapshots') or row.get('valid_snapshot_count') or 0) > 0
    return state == 'ZERO_FIXTURES' and row.get('football_day_fixtures') == 0


def coverage(now, day, ledger, snapshots):
    local = now.astimezone(BKK)
    details = []
    for target in targets(day):
        matched = []
        for snap in snapshots:
            observed = stamp(snap.get('observed_at'))
            explicit = stamp(snap.get('scheduled_target_at'))
            # Legacy fallback targets used observation time. Map each observation
            # once to its latest elapsed canonical slot, never fill older gaps.
            if snap.get('provider') in {'propline', 'pinnwire'} and explicit == observed:
                prior = [t for t in targets(day) if observed and t <= observed]
                explicit = max(prior) if prior else None
            if explicit == target and observed and target <= observed <= min(local, target + timedelta(minutes=RECOVERY_MINUTES)):
                matched.append(snap)
        evidence = [r for r in ledger if valid_completion(r, target, local)]
        completed = bool(matched or evidence)
        latest = max((stamp(r.get('observed_at')) for r in matched), default=None)
        row = evidence[-1] if evidence else {}
        observed = latest or stamp(row.get('actual_observed_at') or row.get('observed_at'))
        state = ('OBSERVED' if matched else row.get('state')) if completed else (
            'UPCOMING' if target > local else 'MISSED' if local > target + timedelta(minutes=RECOVERY_MINUTES) else 'MISSING')
        details.append({'target_time': target.isoformat(), 'state': state,
                        'provider': matched[-1].get('provider') if matched else row.get('provider'),
                        'observed_at': observed.isoformat() if observed else None,
                        'lag_minutes': round((observed-target).total_seconds()/60, 2) if observed else None,
                        'valid_snapshot_count': len(matched),
                        'canonical_fixture_count': len({r.get('fixture_id') for r in matched}),
                        'recovered': bool(completed and observed and observed > target + timedelta(minutes=30))})
    elapsed = [r for r in details if r['state'] != 'UPCOMING']
    done = [r for r in elapsed if r['state'] in {'OBSERVED', 'ZERO_FIXTURES'}]
    return {'bangkok_now': local.isoformat(), 'canonical_slots': details,
            'expected_elapsed_slots': len(elapsed), 'observed_slots': len(done),
            'missing_elapsed_slots': len(elapsed)-len(done),
            'coverage_fraction': round(len(done)/len(elapsed), 3) if elapsed else None,
            'collection_state': 'NOT_DUE' if not elapsed else 'COMPLETE' if len(done) == len(elapsed) else 'DEGRADED',
            'recovered_slots': [r['target_time'] for r in details if r['recovered']],
            'missed_slots': [r['target_time'] for r in details if r['state'] == 'MISSED']}
