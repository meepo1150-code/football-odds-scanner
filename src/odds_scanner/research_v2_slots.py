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
        count = row.get('strict_snapshots') or row.get('valid_snapshot_count') or 0
        return isinstance(count, int) and not isinstance(count, bool) and count > 0
    used = row.get('requests_used', 0)
    receipt = (row['collection_succeeded'] is True if 'collection_succeeded' in row
               else isinstance(used, int) and used > 0)
    return (state == 'ZERO_FIXTURES' and row.get('football_day_fixtures') == 0
            and not row.get('strict_snapshots') and receipt)


def collection_snapshot(row):
    from .research_v2_integrity import trusted_snapshot, finite_number
    from .research_population import in_scope
    if not trusted_snapshot(row) or not in_scope(row) or not row.get('fixture_id'):
        return False
    observed, kickoff = stamp(row.get('observed_at')), stamp(row.get('kickoff'))
    if observed is None or kickoff is None or observed >= kickoff:
        return False
    ah = row.get('ah')
    if not isinstance(ah, dict):
        return False
    hl, al, hp, ap, sl, sp = (finite_number(ah.get(k)) for k in
        ('home_line', 'away_line', 'home_price', 'away_price', 'selected_side_line', 'selected_side_price'))
    if any(v is None for v in (hl, al, hp, ap, sl, sp)):
        return False
    side = row.get('favorite_side')
    return (side in {'H','A'} and abs(hl+al) < 1e-9 and hp > 1 and ap > 1
            and abs(sl*4-round(sl*4)) < 1e-9 and 1.8 <= sp <= 2.2
            and abs(sl-(hl if side == 'H' else al)) < 1e-9
            and abs(sp-(hp if side == 'H' else ap)) < 1e-9)


def matched_snapshots(target, now, snapshots):
    matched = []
    for snap in snapshots:
        if not collection_snapshot(snap):
            continue
        observed = stamp(snap.get('observed_at'))
        explicit = stamp(snap.get('scheduled_target_at'))
        if snap.get('provider') in {'propline', 'pinnwire'} and explicit == observed:
            prior = [t for t in targets(target.date()) if observed and t <= observed]
            explicit = max(prior) if prior else None
        if explicit == target and observed and target <= observed <= min(now, target + timedelta(minutes=RECOVERY_MINUTES)):
            matched.append(snap)
    return matched


def read_snapshots(root=Path('.')):
    from .research_v2_integrity import trusted_snapshot
    from .research_population import in_scope
    path = root / 'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl'
    rows = []
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                row = json.loads(line)
                if isinstance(row, dict) and collection_snapshot(row):
                    rows.append(row)
            except (ValueError, TypeError, KeyError):
                continue
    return rows


def completed(target, now, ledger, snapshots):
    return bool(matched_snapshots(target, now, snapshots) or any(
        row.get('state') == 'ZERO_FIXTURES' and valid_completion(row, target, now)
        for row in ledger))


def slot_completed(root, target, now):
    return completed(target, now, read_ledger(root), read_snapshots(root))


def coverage(now, day, ledger, snapshots):
    local = now.astimezone(BKK)
    details = []
    for target in targets(day):
        matched = matched_snapshots(target, local, snapshots)
        evidence = [r for r in ledger if valid_completion(r, target, local)
                    and (r.get('state') == 'ZERO_FIXTURES' or matched)]
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
