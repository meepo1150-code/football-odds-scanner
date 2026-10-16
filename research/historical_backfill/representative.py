"""Research display selection only; never infer the bookmaker's official mainline."""
from collections import Counter
from copy import deepcopy
from research.historical_backfill.reconstruct import finite, parse_time

POLICY = 'BALANCED_LINE_V1_BOTH_1.80_2.20_MIN_SQUARED_DISTANCE_TO_2'


def rejection(row, *, fixture_id, bookmaker, kickoff, slot, catalog, max_age_seconds=3600):
    if row.get('status') != 'COMPLETE':
        return row.get('status', 'MISSING_STATUS')
    if row.get('fixture_id') != fixture_id or row.get('bookmaker') != bookmaker:
        return 'IDENTITY_MISMATCH'
    if row.get('market') != 'AH':
        return 'MARKET_SCOPE_MISMATCH'
    line = row.get('line')
    if not finite(line) or abs(line * 4 - round(line * 4)) > 1e-8:
        return 'INVALID_QUARTER_LINE'
    meta = [m for m in catalog if str(m['market_id']) == str(row.get('market_id'))]
    if len(meta) != 1 or meta[0]['home_line'] != line:
        return 'CATALOG_LINE_MISMATCH'
    try:
        at, ko = parse_time(slot), parse_time(kickoff)
        if at >= ko or parse_time(row['slot_utc']) != at or parse_time(row['kickoff_utc']) != ko:
            return 'INVALID_SLOT'
        for side in ('home', 'away'):
            q = row.get('quotes', {}).get(side)
            if not q:
                return 'MISSING_SIDE'
            if q.get('active') is not True:
                return 'INACTIVE_OR_UNKNOWN'
            if not finite(q.get('price')) or q['price'] <= 1:
                return 'INVALID_PRICE'
            timestamp = parse_time(q['quote_at_utc'])
            if timestamp > at or timestamp >= ko:
                return 'FUTURE_OR_INPLAY_QUOTE'
            if (at - timestamp).total_seconds() > max_age_seconds:
                return 'STALE_QUOTE'
    except (ValueError, KeyError, TypeError):
        return 'INVALID_TIMESTAMP'
    if not all(1.80 <= row['quotes'][s]['price'] <= 2.20 for s in ('home', 'away')):
        return 'PRICE_OUTSIDE_BALANCED_RANGE'
    return None


def select(rows, *, fixture_id, bookmaker, kickoff, slot, catalog):
    eligible, rejected = [], Counter()
    for r in rows:
        reason = rejection(r, fixture_id=fixture_id, bookmaker=bookmaker,
                           kickoff=kickoff, slot=slot, catalog=catalog)
        if reason:
            rejected[reason] += 1
        else:
            eligible.append(r)
    base = dict(fixture_id=fixture_id, bookmaker=bookmaker, slot_utc=parse_time(slot).isoformat(),
                kickoff_utc=parse_time(kickoff).isoformat(), policy=POLICY,
                official_mainline_verified=False, evaluated_lines=len(rows),
                eligible_lines=len(eligible), rejected_lines=sum(rejected.values()),
                rejection_counts=dict(rejected), selected=None)
    # Reject conflicting duplicates rather than selecting whichever arrived first.
    by_line = {}
    for r in eligible:
        identity = tuple((r['quotes'][s]['price'], r['quotes'][s]['quote_at_utc']) for s in ('home', 'away'))
        if r['line'] in by_line and by_line[r['line']] != identity:
            return {**base, 'status': 'MAINLINE_UNRESOLVED', 'reason': 'CONFLICTING_DUPLICATE_LINE'}
        by_line[r['line']] = identity
    if not eligible:
        return {**base, 'status': 'MAINLINE_UNRESOLVED', 'reason': 'NO_ELIGIBLE_BALANCED_LINE'}
    def score(r):
        h, a = (r['quotes'][s]['price'] for s in ('home', 'away'))
        # Rounded only for ranking arithmetic, never for prices or AH quarter lines.
        return round((h-2)**2 + (a-2)**2, 12), round(abs(h-a), 12), r['line'], str(r['market_id'])
    chosen = deepcopy(min(eligible, key=score))
    chosen.update(home_line=chosen['line'], away_line=-chosen['line'],
                  line_selection='BALANCED_LINE', official_mainline_verified=False)
    return {**base, 'status': 'BALANCED_LINE', 'reason': None, 'selected': chosen}
