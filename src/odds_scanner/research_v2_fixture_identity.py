"""Conservative, reproducible cross-feed identities. Never modify raw evidence."""
from collections import defaultdict
from datetime import datetime, timezone
from .research_v2_integrity import trusted_snapshot

# Explicit competition hierarchy observed in both current feeds. No substring,
# fuzzy-team, time-window or inferred external-ID matching.
NATIONS = {'soccer_uefa_nations_league', *(f'UEFA - Nations League {x}' for x in 'ABCD')}


def utc(value):
    try:
        d = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (TypeError, ValueError):
        return None


def identity(row):
    return tuple(row.get(k) for k in ('home', 'away', 'kickoff', 'league'))


def build_bridge(snapshots):
    by_id = defaultdict(list)
    for row in snapshots:
        if row.get('fixture_id') and trusted_snapshot(row):
            by_id[str(row['fixture_id'])].append(row)
    candidates = defaultdict(list)
    rejected = []
    for fid, rows in sorted(by_id.items()):
        if len({identity(r) for r in rows}) != 1:
            rejected.append({'fixture_id': fid, 'reason': 'INCONSISTENT_IDENTITY'})
            continue
        row = rows[0]
        home, away, kickoff, league = identity(row)
        if not all(isinstance(v, str) and v.strip() for v in (home, away, kickoff, league)) or not utc(kickoff):
            continue
        provider = row.get('provider')
        if provider not in ('pinnwire', 'propline') or not fid.startswith(provider + ':'):
            continue
        if any(r.get('provider') != provider or str(r.get('bookmaker')).lower() != 'pinnacle'
               or not utc(r.get('observed_at')) or utc(r['observed_at']) >= utc(kickoff) for r in rows):
            continue
        competition = 'UEFA_NATIONS_LEAGUE' if league in NATIONS else league
        # Team category markers, punctuation and accents remain exact.
        candidates[(home, away, utc(kickoff).isoformat(), competition)].append((fid, row))
    mapping = {}
    bridges = []
    for key, members in sorted(candidates.items()):
        if len(members) < 2:
            continue
        providers = [r['provider'] for _, r in members]
        if len(members) != 2 or set(providers) != {'pinnwire', 'propline'}:
            rejected.append({'fixture_ids': [fid for fid, _ in members], 'reason': 'AMBIGUOUS_PROVIDER_IDENTITY'})
            continue
        canonical = next(fid for fid, r in members if r['provider'] == 'pinnwire')
        evidence = [{'fixture_id': fid, 'provider': r['provider'],
                     **dict(zip(('home', 'away', 'kickoff', 'league'), identity(r)))} for fid, r in members]
        bridges.append({'canonical_fixture_id': canonical, 'members': evidence,
                        'policy': 'EXACT_TEAMS_UTC_KICKOFF_VERIFIED_COMPETITION_UNIQUE_PER_PROVIDER',
                        'competition': key[3], 'bookmaker': 'pinnacle'})
        for fid, _ in members:
            mapping[fid] = canonical
    return mapping, {'schema_version': '1.0', 'bridges': bridges, 'rejected': rejected,
                     'bridged_matches': len(bridges), 'collapsed_provider_ids': sum(k != v for k, v in mapping.items())}


def project(rows, mapping):
    """Derived-only IDs with original provider ID retained for provenance."""
    return [{**r, 'source_fixture_id': r.get('fixture_id'),
             'fixture_id': mapping.get(str(r.get('fixture_id')), r.get('fixture_id'))} for r in rows]
