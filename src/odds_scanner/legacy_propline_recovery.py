"""Network-free, fail-closed legacy recovery staging. Never edits raw/canonical data.

Only a verified snapshot at/before the original observation, at most five minutes
old, can stage a replacement. Later prices cannot reconstruct an earlier market.
PinnWire balanced-line observations and Bet365 historical ticks are not evidence
of a verified historical Pinnacle mainline. Staged records require separate review
and promotion; this module intentionally has no canonical write path.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path

SNAPSHOTS = Path('data/normalized/europe_pinnacle_research_v2_snapshots.jsonl')
RECOVERED = Path('data/normalized/legacy_propline_recovery_staged.jsonl')
REPORT = Path('reports/legacy_propline_recovery.json')
MAX_AGE_SECONDS = 300
SEMANTICS = {'PROPLINE_PINNACLE_TWO_SIDED_CORE_MAINLINE', 'CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED'}


def _dt(value):
    try:
        result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return result if result.tzinfo else None
    except (ValueError, TypeError):
        return None


def _norm(value):
    return ' '.join(str(value or '').casefold().split())


def _rows(path):
    if not path.exists():
        return []
    # Malformed forensic input is an error, never silently omitted from counts.
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def is_legacy(row):
    return row.get('provider') == 'propline' and not (
        row.get('mainline_verified') is True and row.get('source_semantics') in SEMANTICS)


def identity(old, candidate):
    # Even an exact ID cannot override conflicting fixture metadata.
    if not all(_norm(old.get(k)) and _norm(old.get(k)) == _norm(candidate.get(k))
               for k in ('home', 'away', 'league')):
        return None
    kickoff = _dt(old.get('kickoff'))
    if not kickoff or kickoff != _dt(candidate.get('kickoff')):
        return None
    return 'EXACT_FIXTURE_ID' if old.get('fixture_id') == candidate.get('fixture_id') else 'EXACT_TEAMS_LEAGUE_KICKOFF_BRIDGE'


def validate_quote(row):
    if _norm(row.get('bookmaker')) != 'pinnacle':
        return 'NOT_PINNACLE'
    if row.get('mainline_verified') is not True or row.get('source_semantics') not in SEMANTICS:
        return 'MAINLINE_SEMANTICS_NOT_VERIFIED'
    observed, kickoff = _dt(row.get('observed_at')), _dt(row.get('kickoff'))
    if not observed or not kickoff or observed >= kickoff:
        return 'TIMESTAMP_NOT_VERIFIED_PREMATCH'
    ah = row.get('ah') or {}
    hl, al, hp, ap = [_number(ah.get(k)) for k in ('home_line', 'away_line', 'home_price', 'away_price')]
    if None in (hl, al, hp, ap) or hp <= 1 or ap <= 1:
        return 'INVALID_TWO_SIDED_PAIR'
    if abs(hl + al) > 1e-9 or abs(hl * 4 - round(hl * 4)) > 1e-9:
        return 'INVALID_OPPOSITE_QUARTER_LINES'
    side = row.get('favorite_side')
    if side not in ('H', 'A') or (hl < 0 and side != 'H') or (hl > 0 and side != 'A'):
        return 'FAVORITE_SIDE_CONFLICT'
    selected_line, selected_price = (hl, hp) if side == 'H' else (al, ap)
    if _number(ah.get('selected_side_line')) != selected_line or _number(ah.get('selected_side_price')) != selected_price:
        return 'SELECTED_PAIR_CONFLICT'
    if not 1.80 <= selected_price <= 2.20:
        return 'OUTSIDE_RESEARCH_CORE_PRICE'
    return None


def recover(old, candidates):
    matches = [(row, identity(old, row), path) for row, path in candidates if identity(old, row)]
    base = {k: old.get(k) for k in ('fixture_id', 'home', 'away', 'league', 'kickoff', 'observed_at')}
    base['original_sha256'] = hashlib.sha256(json.dumps(old, sort_keys=True).encode()).hexdigest()
    base['identity_candidates'] = len(matches)
    eligible, rejected = [], Counter()
    original_time = _dt(old.get('observed_at'))
    if not original_time:
        return {**base, 'status': 'UNAVAILABLE', 'reason': 'ORIGINAL_TIMESTAMP_INVALID'}, None
    for row, match, path in matches:
        reason = validate_quote(row)
        if reason:
            rejected[reason] += 1
            continue
        age = (original_time - _dt(row['observed_at'])).total_seconds()
        if not 0 <= age <= MAX_AGE_SECONDS:
            rejected['LATER_QUOTE_CANNOT_RECONSTRUCT_PAST' if age < 0 else 'HISTORICAL_QUOTE_TOO_OLD'] += 1
            continue
        eligible.append((age, row, match, path))
    base['rejection_counts'] = dict(sorted(rejected.items()))
    if not eligible:
        return {**base, 'status': 'UNAVAILABLE', 'reason': 'NO_DEFENSIBLE_HISTORICAL_PINNACLE_MAINLINE' if matches else 'NO_VERIFIED_IDENTITY_IN_LOCAL_PINNACLE_ARCHIVE'}, None
    nearest = min(x[0] for x in eligible)
    chosen = [x for x in eligible if x[0] == nearest]
    signatures = {json.dumps({'ah': x[1]['ah'], 'favorite_side': x[1]['favorite_side']}, sort_keys=True) for x in chosen}
    if len(signatures) != 1:
        return {**base, 'status': 'AMBIGUOUS', 'reason': 'CONFLICTING_NEAREST_TWO_SIDED_QUOTES'}, None
    age, row, match, path = sorted(chosen, key=lambda x: (x[3], str(x[1].get('fixture_id'))))[0]
    provenance = {'source_path': path, 'source_fixture_id': row['fixture_id'], 'source_observed_at': row['observed_at'], 'source_semantics': row['source_semantics'], 'identity_method': match, 'age_seconds': age, 'source_sha256': hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()}
    # Preserve the source's actual timestamp; never relabel it as the original.
    staged = {'original': base, 'replacement_snapshot': row, 'provenance': provenance, 'status': 'VALIDATED_STAGED_NOT_PROMOTED'}
    return {**base, 'status': 'RECOVERED_STAGED', 'reason': 'VERIFIED_NEAREST_PRIOR_MAINLINE', 'provenance': provenance}, staged


def build(root=Path('.')):
    raw = _rows(root / SNAPSHOTS)
    legacy = [x for x in raw if is_legacy(x)]
    paths = [SNAPSHOTS, Path('data/normalized/v2_mainline_snapshots.jsonl')]
    inventory, candidates = [], []
    for path in paths:
        rows = raw if path == SNAPSHOTS else _rows(root / path)
        inventory.append({'path': str(path), 'rows': len(rows), 'bookmakers': dict(Counter(_norm(x.get('bookmaker')) for x in rows))})
        candidates.extend((row, str(path)) for row in rows if not is_legacy(row))
    # Historical tick files are inventoried explicitly, but no alternate/mainline
    # inference is permitted from their arrays of lines.
    archives = sorted((root / 'data/normalized/oddspapi_history_ticks').glob('*.jsonl'))
    archives += [root / 'data/normalized/oddspapi_history_ticks.jsonl']
    for path in archives:
        rows = _rows(path)
        inventory.append({'path': str(path.relative_to(root)), 'rows': len(rows), 'bookmakers': dict(Counter(_norm(x.get('bookmaker')) for x in rows)), 'eligible_for_recovery': False, 'reason': 'TICK_ARCHIVE_HAS_NO_VERIFIED_PINNACLE_MAINLINE_CONTRACT'})
    records, staged = [], []
    for old in sorted(legacy, key=lambda x: (str(x.get('fixture_id')), str(x.get('observed_at')))):
        record, replacement = recover(old, candidates)
        records.append(record)
        if replacement:
            staged.append(replacement)
    counts = Counter(x['status'] for x in records)
    report = {'schema_version': '1.0', 'status': 'WAITING_EXTERNAL_DATA' if len(staged) != len(legacy) else 'VALIDATED_STAGING_COMPLETE', 'total_legacy_observations': len(legacy), 'recovered': len(staged), 'promoted': 0, 'still_quarantined': len(legacy), 'ambiguous': counts['AMBIGUOUS'], 'unavailable': counts['UNAVAILABLE'], 'source_used': sorted({x['provenance']['source_path'] for x in staged}), 'source_inventory': inventory, 'policy': {'max_prior_quote_age_seconds': MAX_AGE_SECONDS, 'later_quotes_allowed': False, 'canonical_mutation': False, 'network_requests': 0, 'promotion': 'SEPARATE_REVIEW_REQUIRED'}, 'next_automatic_action': 'RECHECK_LOCAL_ARCHIVES_ON_DATA_REBUILD; EXTERNAL_VERIFIED_HISTORICAL_PINNACLE_SOURCE_REQUIRED_FOR_UNAVAILABLE_RECORDS', 'records': records}
    for path in (REPORT, RECOVERED):
        (root / path).parent.mkdir(parents=True, exist_ok=True)
    (root / REPORT).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    (root / RECOVERED).write_text(''.join(json.dumps(x, sort_keys=True) + '\n' for x in staged))
    return report


if __name__ == '__main__':
    result = build()
    print(json.dumps({k: v for k, v in result.items() if k not in ('records', 'source_inventory')}))
