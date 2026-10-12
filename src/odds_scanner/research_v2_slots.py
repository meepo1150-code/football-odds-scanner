"""Canonical Bangkok collection slots and persisted evidence validation."""
import json
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BKK = ZoneInfo('Asia/Bangkok')
RECOVERY_MINUTES = 150
SCHEDULE_EFFECTIVE_DAY = '2026-10-12'
SCHEDULE_VERSION = 'BKK_18_SLOTS_V2'
PREPARATION_EFFECTIVE_DAY = '2026-10-13'
PREPARATION_VERSION = 'BKK_23_SLOTS_V3'
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
    if day.isoformat() < SCHEDULE_EFFECTIVE_DAY:
        hours = (12, 15, 18, 19, 20, 21, 22) if day.weekday() >= 5 else (18, 21)
        return [datetime.combine(day, time(hour), BKK) for hour in hours]
    hours = (15, 18, 21) if day.weekday() >= 5 or day.isoformat() >= PREPARATION_EFFECTIVE_DAY else (18, 21)
    slots = [datetime.combine(day, time(hour), BKK) for hour in hours]
    if day.weekday() >= 5:
        slots.append(datetime.combine(day + timedelta(days=1), time(0), BKK))
    return slots


def schedule_version(day):
    return PREPARATION_VERSION if str(day) >= PREPARATION_EFFECTIVE_DAY else SCHEDULE_VERSION if str(day) >= SCHEDULE_EFFECTIVE_DAY else 'BKK_LEGACY_V1'


def target_football_day(target):
    local = target.astimezone(BKK)
    return (local.date() - timedelta(days=1) if local.hour < 6 else local.date()).isoformat()


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


def provider_attempt_receipt(row):
    """Zero-request mapping/auth skips must not masquerade as quote/API attempts."""
    requests=(row.get('requests_used',0),row.get('http_requests_attempted',0))
    if any(type(n) is int and n>0 for n in requests):return True
    if 'requests_used' not in row and row.get('status')=='RATE_LIMITED':return True
    count=row.get('strict_snapshots') or row.get('valid_snapshot_count') or 0
    return (row.get('state')=='OBSERVED' and type(count) is int and count>0) or (
        row.get('state') in {'ZERO_FIXTURES','ZERO_COHORT'} and row.get('collection_succeeded') is True)


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
    return (state in {'ZERO_FIXTURES','ZERO_COHORT'} and row.get('football_day_fixtures') == 0
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
            prior = [t for t in targets(target_football_day(target)) if observed and t <= observed]
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
        row.get('state') in {'ZERO_FIXTURES','ZERO_COHORT'} and valid_completion(row, target, now)
        for row in ledger))


def slot_completed(root, target, now):
    return completed(target, now, read_ledger(root), read_snapshots(root))


def coverage(now, day, ledger, snapshots):
    local = now.astimezone(BKK)
    details = []
    for target in targets(day):
        matched = matched_snapshots(target, local, snapshots)
        evidence = [r for r in ledger if valid_completion(r, target, local)
                    and (r.get('state') in {'ZERO_FIXTURES','ZERO_COHORT'} or matched)]
        completed = bool(matched or evidence)
        latest = max((stamp(r.get('observed_at')) for r in matched), default=None)
        row = evidence[-1] if evidence else {}
        observed = latest or stamp(row.get('actual_observed_at') or row.get('observed_at'))
        state = ('OBSERVED' if matched else row.get('state')) if completed else (
            'UPCOMING' if target > local else 'MISSED' if local > target + timedelta(minutes=RECOVERY_MINUTES) else 'MISSING')
        if (state=='ZERO_FIXTURES' and str(day)>=SCHEDULE_EFFECTIVE_DAY
                and row.get('coverage_complete') is not True):
            # Preserve the old receipt for dedupe without asserting whole-scope emptiness.
            state='ZERO_COHORT'
        details.append({'target_time': target.isoformat(), 'state': state,
                        'provider': (matched[-1].get('provider') or ('oddspapi' if str(matched[-1].get('source_semantics','')).startswith('CURRENT_ODDSPAPI_') else 'UNRESOLVED_PROVIDER')) if matched else row.get('provider'),
                        'observed_at': observed.isoformat() if observed else None,
                        'lag_minutes': round((observed-target).total_seconds()/60, 2) if observed else None,
                        'valid_snapshot_count': len(matched),
                        'canonical_fixture_count': len({r.get('fixture_id') for r in matched}),
                        'observation_timing': ('ON_TIME' if observed and observed <= target + timedelta(minutes=30) else 'LATE' if observed else state),
                        'recovered': bool(completed and observed and observed > target + timedelta(minutes=30))})
    elapsed = [r for r in details if r['state'] != 'UPCOMING']
    done = [r for r in elapsed if r['state'] in {'OBSERVED', 'ZERO_FIXTURES','ZERO_COHORT'}]
    partial = [r for r in done if r['state']=='ZERO_COHORT']
    on_time = [r for r in done if r['observation_timing']=='ON_TIME']
    late = [r for r in done if r['observation_timing']=='LATE']
    return {'bangkok_now': local.isoformat(), 'canonical_slots': details,
            'schedule_version': schedule_version(day), 'schedule_effective_day': SCHEDULE_EFFECTIVE_DAY,
            'on_time_slots':len(on_time),'late_slots':len(late),'partial_scope_slots':len(partial),
            'on_time_coverage_fraction':round(len(on_time)/len(elapsed),3) if elapsed else None,
            'expected_elapsed_slots': len(elapsed), 'observed_slots': len(done),
            'missing_elapsed_slots': len(elapsed)-len(done),
            'coverage_fraction': round(len(done)/len(elapsed), 3) if elapsed else None,
            'collection_state': 'NOT_DUE' if not elapsed else 'DEGRADED_SCOPE' if partial else 'COMPLETE' if len(on_time) == len(elapsed) else 'DEGRADED_TIMING' if len(done)==len(elapsed) else 'DEGRADED',
            'recovered_slots': [r['target_time'] for r in details if r['recovered']],
            'missed_slots': [r['target_time'] for r in details if r['state'] == 'MISSED']}
