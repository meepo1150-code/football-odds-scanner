"""Network-free, fail-closed identity review; never writes production mappings."""
import csv
import hashlib
import importlib.util
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
DESIGNATORS = {'fc', 'cf', 'fk', 'nk', 'sk', 'sc', 'ac', 'afc', 'pfc',
               'hfk', 'hnk', 'gnk', 'kf', 'fkc', 'ofk'}
START = '2026-10-01T00:00:00Z'
END = '2026-11-01T00:00:00Z'


def spelling(value):
    # Fold Latin accents, but retain meaningful Thai vowel/tone marks.
    chars = []; latin = False
    for char in unicodedata.normalize('NFKD', value.casefold()):
        mark = unicodedata.category(char).startswith('M')
        if mark and latin:
            continue
        if not mark:
            latin = 'LATIN' in unicodedata.name(char, '')
        chars.append(char if char.isalnum() or mark else ' ')
    tokens = ''.join(chars).split()
    while tokens and tokens[0] in DESIGNATORS:
        tokens.pop(0)
    while tokens and tokens[-1] in DESIGNATORS:
        tokens.pop()
    return ''.join(tokens)


def rows(path):
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def json_file(path):
    return json.loads(path.read_text())


def in_window(value, earliest=START):
    try:
        moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return (moment.tzinfo is not None and
                datetime.fromisoformat(earliest.replace('Z', '+00:00')) <= moment <
                datetime.fromisoformat(END.replace('Z', '+00:00')))
    except (ValueError, TypeError, AttributeError):
        return False


def review(repo=REPO, snapshot=None, official_aliases=()):
    raw_path = repo/'reports/master_provider_snapshot.json'
    raw = snapshot if snapshot is not None else json_file(raw_path)
    if raw.get('provider') != 'oddspapi' or raw.get('status') != 'SNAPSHOT_AVAILABLE_REQUIRES_IDENTITY_REVIEW':
        raise ValueError('Unsupported provider namespace or unavailable evidence')
    clubs = {}; rosters = defaultdict(set); names = defaultdict(set)
    sources = {}; candidates = {}; source_hashes = {}
    for phase in ('phase1', 'phase2'):
        root = repo/('data/research/global_master_'+phase)
        for name in ('clubs_canonical.csv', 'verified_memberships.csv',
                     'evidence/rosters.json', 'evidence/aliases.json',
                     'evidence/provider_candidates.json'):
            path = root/name
            source_hashes[str(path.relative_to(repo))] = hashlib.sha256(path.read_bytes()).hexdigest()
        for club in rows(root/'clubs_canonical.csv'):
            clubs[club['club_id']] = club
            names[club['club_id']].add(club['canonical_name'])
        for member in rows(root/'verified_memberships.csv'):
            rosters[member['competition_id']].add(member['club_id'])
            names[member['club_id']].add(member['source_name'])
        for source in json_file(root/'evidence/rosters.json'):
            sources[source['competition_id']] = source
        for alias in json_file(root/'evidence/aliases.json'):
            if alias['verification_status'] == 'VERIFIED_OFFICIAL':
                names[alias['club_id']].add(alias['alias'])
        for binding in json_file(root/'evidence/provider_candidates.json'):
            candidates[binding['competition_id']] = binding.get('candidates') or [
                {key: binding[key] for key in ('provider_id', 'provider_name', 'provider_country')}]

    thai = repo/'data/research/thailand_membership_completion'
    spec = importlib.util.spec_from_file_location('thai_completion', thai/'build.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.validate(thai, repo)
    for filename in ('evidence.json', 'identity_ledger.json', 'clubs_canonical.csv', 'verified_memberships.csv', 'qa.json'):
        path = thai/filename
        source_hashes[str(path.relative_to(repo))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for club in rows(thai/'clubs_canonical.csv'):
        clubs[club['club_id']] = club
        names[club['club_id']].add(club['canonical_name'])
    for member in rows(thai/'verified_memberships.csv'):
        cid = member['competition_id']
        rosters[cid].add(member['club_id'])
        names[member['club_id']].add(member['source_name'])
        sources[cid] = dict(competition_name=member['competition_name'], source_url=member['source_url'])
    # Candidate IDs are read-only catalog observations, not activation mappings.
    for cid, tid, name in [('THA-0001', '1032', 'Thai League 1'), ('THA-0002', '19232', 'Thai League 2')]:
        candidates[cid] = [dict(provider_id=tid, provider_name=name, provider_country='Thailand')]

    # Optional staging evidence is supplied by the separately hash-pinned
    # official alias follow-up. Keep aliases scoped to the proven membership.
    extra_names = defaultdict(set)
    for alias in official_aliases:
        cid, club, name = alias['competition_id'], alias['club_id'], alias['alias']
        if club not in rosters[cid] or not spelling(name):
            raise ValueError('Alias requires an existing scoped membership and nonempty name')
        extra_names[cid, club].add(name)

    catalog = {str(t['tournamentId']): t for t in raw['tournaments']}
    catalog_counts = Counter(str(t['tournamentId']) for t in raw['tournaments'])
    # Conflicting versions of the same fixture cannot prove any identity.
    identities = defaultdict(set)
    for f in raw['fixtures']:
        identities[str(f.get('fixtureId'))].add(tuple(str(f.get(k, '')) for k in
            ('tournamentId', 'startTime', 'participant1Id', 'participant1Name',
             'participant2Id', 'participant2Name')))
    conflicting = {key for key, values in identities.items() if len(values) != 1}
    production = rows(repo/'data/master/provider_mappings.csv')
    existing_pids = defaultdict(set)
    existing_tids = defaultdict(set)
    for row in production:
        if row['provider'] == 'oddspapi':
            target = existing_pids if row['entity_type'] == 'club' else existing_tids
            target[row['provider_id']].add(row['internal_id'])
    competition_reviews = []; club_observations = defaultdict(list)
    for cid, members in sorted(rosters.items()):
        lookup = defaultdict(set)
        for club in members:
            for name in names[club] | extra_names[cid, club]:
                token = spelling(name)
                # The generic KFA label is not an explicit N/B qualifier.
                if cid == 'KOR-0003' and clubs[club]['canonical_name'] == '전북현대 N팀' and token != spelling('전북현대 N팀'):
                    continue
                if token:
                    lookup[token].add(club)
        alternatives = []; proofs_by_id = {}
        for candidate in candidates[cid]:
            tid = candidate['provider_id']; t = catalog.get(tid, {})
            catalog_ok = (catalog_counts[tid] == 1 and t.get('tournamentName') == candidate['provider_name'] and
                          t.get('categoryName') == candidate['provider_country'] and
                          (not existing_tids[tid] or existing_tids[tid] == {cid}))
            pairs = []; seen = set()
            if catalog_ok:
                for f in raw['fixtures']:
                    fid = str(f.get('fixtureId')); date = str(f.get('startTime', ''))
                    earliest = '2026-10-16T00:00:00Z' if cid == 'AUS-0001' else START
                    if (not f.get('fixtureId') or str(f.get('tournamentId')) != tid
                            or f.get('tournamentName') != t.get('tournamentName')
                            or fid in conflicting or fid in seen or not in_window(date, earliest)):
                        continue
                    sides = []
                    for side in (1, 2):
                        pid = str(f.get(f'participant{side}Id', ''))
                        name = f.get(f'participant{side}Name', '')
                        matches = lookup.get(spelling(name), set()) if spelling(name) else set()
                        if len(matches) != 1 or raw['participants'].get(pid) != name:
                            break
                        club = next(iter(matches))
                        if existing_pids[pid] and existing_pids[pid] != {club}:
                            break
                        sides.append(dict(club_id=club, provider_id=pid, provider_name=name))
                    if len(sides) != 2 or len({s['club_id'] for s in sides}) != 2 or len({s['provider_id'] for s in sides}) != 2:
                        continue
                    seen.add(fid)
                    pairs.append(dict(fixture_id=fid, start_time=date,
                                      provider_tournament_id=tid, sides=sides))
            pair_clubs = {side['club_id'] for pair in pairs for side in pair['sides']}
            # Explicit minimum corroboration, not a league-completeness claim.
            eligible = catalog_ok and len(pairs) >= 2 and len(pair_clubs) >= 4
            alternatives.append(dict(**candidate, catalog_verified=catalog_ok,
                                     paired_fixtures=len(pairs), paired_clubs=len(pair_clubs),
                                     meets_identity_gate=eligible))
            proofs_by_id[tid] = pairs
        eligible = [c for c in alternatives if c['meets_identity_gate']]
        selected = eligible[0] if len(eligible) == 1 else None
        if selected:
            for pair in proofs_by_id[selected['provider_id']]:
                for side in pair['sides']:
                    club_observations[side['club_id']].append(dict(
                        competition_id=cid, fixture_id=pair['fixture_id'],
                        start_time=pair['start_time'], provider_tournament_id=selected['provider_id'],
                        provider_id=side['provider_id'], provider_name=side['provider_name'],
                        counterpart=next(s for s in pair['sides'] if s['club_id'] != side['club_id'])))
        competition_reviews.append(dict(competition_id=cid, competition_name=sources[cid]['competition_name'],
            provider='oddspapi', provider_id=selected['provider_id'] if selected else None,
            status='VERIFIED_CACHED_COMPETITION_IDENTITY' if selected else 'REVIEW',
            reason='UNIQUE_CATALOG_AND_PAIRED_CURRENT_ROSTER_OBSERVATIONS' if selected else
                   ('MULTIPLE_ELIGIBLE_STAGE_IDS' if len(eligible)>1 else 'INSUFFICIENT_PAIRED_ROSTER_CORROBORATION'),
            alternatives=alternatives, provider_season_stage_verified=False,
            activation_allowed=False, official_source=sources[cid]['source_url']))

    selected_counts = Counter(c['provider_id'] for c in competition_reviews if c['provider_id'])
    collisions = {tid for tid, count in selected_counts.items() if count > 1}
    for comp in competition_reviews:
        if comp['provider_id'] in collisions:
            comp.update(provider_id=None, status='REVIEW', reason='COMPETITION_PROVIDER_ID_COLLISION')
    for club in club_observations:
        club_observations[club] = [o for o in club_observations[club] if o['provider_tournament_id'] not in collisions]
    owners = defaultdict(set)
    for club, obs in club_observations.items():
        for o in obs:
            owners[o['provider_id']].add(club)
    club_reviews = []
    for club, data in sorted(clubs.items()):
        obs = club_observations.get(club, [])
        pids = {o['provider_id'] for o in obs}
        verified = len(pids) == 1 and all(len(owners[p]) == 1 for p in pids)
        club_reviews.append(dict(club_id=club, canonical_name=data['canonical_name'],
            country_id=data['country_id'], provider='oddspapi',
            provider_id=next(iter(pids)) if verified else None,
            status='VERIFIED_CACHED_PARTICIPANT_IDENTITY' if verified else 'UNRESOLVED',
            reason='OFFICIAL_SCOPED_ALIAS_AND_BOTH_FIXTURE_PARTICIPANTS_CORROBORATED' if verified else
                   ('CONFLICTING_PROVIDER_IDENTITIES' if obs else 'NO_ELIGIBLE_PAIRED_ROSTER_EVIDENCE'),
            observations=obs, activation_allowed=False))
    return dict(schema_version='1.0', reviewed_at='2026-10-15',
        evidence_observed_at=raw['generated_at'], provider_snapshot_sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        source_hashes=source_hashes, fixture_window=dict(start=START,end_exclusive=END),
        normalization='UNICODE_CASE_ACCENT_PUNCTUATION_AND_EDGE_LEGAL_DESIGNATORS_ONLY',
        competition_gate=dict(min_paired_fixtures=2,min_distinct_clubs=4),
        competitions=competition_reviews, clubs=club_reviews,
        counts=dict(competitions=len(competition_reviews),clubs=len(club_reviews),
                    verified_cached_competition_identities=sum(c['status'].startswith('VERIFIED_') for c in competition_reviews),
                    verified_cached_participant_identities=sum(c['status'].startswith('VERIFIED_') for c in club_reviews)),
        provider_season_stage_verified=False, live_odds_coverage_verified=False,
        activation_allowed=False, provider_requests_used=0,
        limitations=['Cached provider identity is not live availability or complete roster/provider coverage.',
                    'No provider season/stage ID is certified by fixture dates alone.',
                    'Generic reserve labels, ambiguous aliases, conflicting fixtures and IDs fail closed.'])


if __name__ == '__main__':
    import sys
    result = review()
    if '--write' in sys.argv:
        (ROOT/'review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    elif json_file(ROOT/'review.json') != result:
        raise SystemExit('FAIL: committed review differs from deterministic evidence rebuild')
    print(json.dumps(result['counts'], indent=2))
