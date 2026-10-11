"""Comparable prematch movement, distinct from source/contract switches."""
from datetime import datetime, timezone
from math import isfinite


def utc(v):
    try:
        d = datetime.fromisoformat(str(v).replace('Z', '+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (TypeError, ValueError):
        return None


def number(v):
    try:
        x = float(v)
        return x if isfinite(x) else None
    except (TypeError, ValueError):
        return None


def contract(r):
    # Changing feeds is explicitly separated even when bookmaker is identical.
    return tuple(r.get(k) for k in ('provider', 'bookmaker', 'source_semantics')) + (r.get('market', 'AH'), r.get('period', 'FT'))


def describe(rows):
    unique = {}
    for r in rows:
        observed, kickoff = utc(r.get('observed_at')), utc(r.get('kickoff'))
        if observed and kickoff and observed < kickoff:
            unique[(contract(r), observed)] = r
    rs = sorted(unique.values(), key=lambda r: utc(r['observed_at']))
    result = {'movement': 'INSUFFICIENT_OBSERVATIONS', 'comparable_observations': 0,
              'source_switch': False, 'line_change': False, 'price_change': False,
              'favorite_switch': False, 'observation_gap_minutes': None,
              'first_minutes_before_kickoff': None, 'last_minutes_before_kickoff': None}
    if len(rs) < 2:
        result['movement'] = 'SINGLE_OBSERVATION' if len(rs) == 1 else 'INSUFFICIENT_OBSERVATIONS'
        return result
    # The latest source's own history is used; never bridge two sources into movement.
    result['source_switch'] = len({contract(r) for r in rs}) > 1
    latest = rs[-1]
    same = [r for r in rs if contract(r) == contract(latest)]
    result['comparable_observations'] = len(same)
    if len(same) < 2:
        result['movement'] = 'SOURCE_SWITCH__INSUFFICIENT_OBSERVATIONS'
        return result
    a, b = same[0], same[-1]
    # IDs must be the same within this source, or an explicit projected bridge.
    if (a.get('source_fixture_id') or a.get('fixture_id')) != (b.get('source_fixture_id') or b.get('fixture_id')) or utc(a.get('kickoff')) != utc(b.get('kickoff')):
        return result
    result.update(first_observed_at=a['observed_at'], last_observed_at=b['observed_at'],
                  observation_gap_minutes=round((utc(b['observed_at'])-utc(a['observed_at'])).total_seconds()/60, 3),
                  first_minutes_before_kickoff=round((utc(a['kickoff'])-utc(a['observed_at'])).total_seconds()/60, 3),
                  last_minutes_before_kickoff=round((utc(b['kickoff'])-utc(b['observed_at'])).total_seconds()/60, 3))
    fa, la = a.get('ah') or {}, b.get('ah') or {}
    fl, ll = number(fa.get('selected_side_line')), number(la.get('selected_side_line'))
    fp, lp = number(fa.get('selected_side_price')), number(la.get('selected_side_price'))
    result['favorite_switch'] = a.get('favorite_side') != b.get('favorite_side')
    result['line_change'] = fl is not None and ll is not None and fl != ll
    result['price_change'] = fp is not None and lp is not None and abs(lp-fp) >= .005
    if result['favorite_switch']:
        result['movement'] = 'FAVORITE_SWITCH'
    elif None in (fl, ll, fp, lp):
        result['movement'] = 'INSUFFICIENT_MARKET_FIELDS'
    else:
        line = 'AH_LINE_UNCHANGED' if ll == fl else 'AH_FAVORITE_LINE_STRONGER' if ll < fl else 'AH_FAVORITE_LINE_WEAKER'
        price = 'PRICE_FLAT' if abs(lp-fp) < .005 else 'PRICE_DOWN' if lp < fp else 'PRICE_UP'
        result['movement'] = line + '__' + price
    return result
