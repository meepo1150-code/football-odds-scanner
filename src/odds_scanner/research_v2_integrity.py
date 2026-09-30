"""Shared fail-closed guard for quarantined PropLine AH observations."""
import math
from datetime import datetime


def finite_number(value):
    try:
        number = float(value)
    except (ValueError, TypeError):
        return None
    return number if math.isfinite(number) else None


def trusted_snapshot(row):
    if str(row.get('provider') or '').lower() != 'propline':
        return True
    if (str(row.get('bookmaker') or '').lower() != 'pinnacle'
            or row.get('mainline_verified') is not True
            or row.get('source_semantics') != 'PROPLINE_PINNACLE_TWO_SIDED_CORE_MAINLINE'):
        return False
    ah = row.get('ah') or {}
    if not isinstance(ah, dict):
        return False
    hl, al, hp, ap, sl, sp = (finite_number(ah.get(k)) for k in
                             ('home_line', 'away_line', 'home_price', 'away_price',
                              'selected_side_line', 'selected_side_price'))
    if any(v is None for v in (hl, al, hp, ap, sl, sp)):
        return False
    if abs(hl + al) > 1e-9 or hp <= 1 or ap <= 1 or not 1.8 <= sp <= 2.2:
        return False
    side = str(row.get('favorite_side') or '').upper()
    if side not in ('H', 'A'):
        return False
    if abs(sl - (hl if side == 'H' else al)) > 1e-9 or abs(sp - (hp if side == 'H' else ap)) > 1e-9:
        return False
    if abs(sl * 4 - round(sl * 4)) > 1e-9:
        return False
    try:
        observed = datetime.fromisoformat(str(row.get('observed_at')).replace('Z', '+00:00'))
        kickoff = datetime.fromisoformat(str(row.get('kickoff')).replace('Z', '+00:00'))
        return observed.tzinfo is not None and kickoff.tzinfo is not None and observed < kickoff
    except (ValueError, TypeError):
        return False
