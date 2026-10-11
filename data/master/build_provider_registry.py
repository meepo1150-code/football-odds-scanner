#!/usr/bin/env python3
"""Rebuild reviewed provider identities offline; never discovers or guesses IDs."""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from odds_scanner.master_identity import club_spelling

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def rows(name):
    with (ROOT / name).open() as handle:
        return list(csv.DictReader(handle))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    raw_path = REPO / 'reports/master_provider_snapshot.json'
    raw = json.loads(raw_path.read_text())
    if raw['status'] != 'SNAPSHOT_AVAILABLE_REQUIRES_IDENTITY_REVIEW':
        raise ValueError('Provider snapshot is not available')
    bindings = json.loads((ROOT / 'research/provider_competition_bindings.json').read_text())
    catalogue = {str(r['tournamentId']): r for r in raw['tournaments']}
    for binding in bindings:
        provider = catalogue[binding['provider_id']]
        assert provider['tournamentName'] == binding['provider_name']
        assert provider['categoryName'] == binding['provider_country']
    source = REPO / 'reports/master_provider_tournaments.json'
    write(source, dict(generated_at=raw.get('tournaments_reused_from', raw['generated_at']), provider='oddspapi', candidates=[dict(tournament_id=r['tournamentId'], tournament_name=r['tournamentName'], country=r['categoryName'], provider_verified=True) for r in raw['tournaments']], raw_source=str(raw_path.relative_to(REPO)), raw_sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest()))
    reverse = {int(r['provider_id']): r['internal_id'] for r in bindings}
    clubs = {r['club_id']: r for r in rows('uefa_clubs_canonical.csv')}
    roster = defaultdict(set)
    for r in rows('uefa_verified_memberships_2026.csv'):
        roster[r['competition_id']].add(r['club_id'])
    active = set().union(*roster.values())
    member_comp = {club: comp for comp, members in roster.items() for club in members}
    registered_cups = {r['competition_id'] for r in rows('cup_competition_registry_2026.csv')}
    binding_by_comp = {r['internal_id']: r for r in bindings}
    raw_tournaments = {r['tournamentId']: r for r in raw['tournaments']}
    names = defaultdict(set)
    for r in rows('research/club_assignments.csv'):
        names[r['club_id']].add(r['source_name'])
    for club, r in clubs.items():
        names[club].add(r['canonical_name'])
    reviews = json.loads((ROOT / 'research/provider_club_alias_reviews_2026_10_09.json').read_text())
    review_date = max(r['checked_at'] for r in reviews + bindings)
    explicit = set()
    official_aliases = set()
    for r in reviews:
        assert clubs[r['club_id']]['canonical_name'] == r['canonical_name']
        names[r['club_id']].add(r['provider_name'])
        explicit.add((r['club_id'], r['provider_id'], r['provider_name']))
        if r.get('official_identity_url'):
            official_aliases.add((r['club_id'], r['provider_id'], r['provider_name']))
    observations = defaultdict(list)
    for f in raw['fixtures']:
        comp = reverse.get(f.get('tournamentId'))
        context = 'LEAGUE'
        candidates = roster.get(comp, set())
        if comp in registered_cups:
            context = 'REGISTERED_CUP'
            candidates = active
        elif not candidates:
            from odds_scanner.oddspapi_tournament_universe import classify, excluded
            tournament = raw_tournaments.get(f.get('tournamentId'), {})
            label, country = tournament.get('tournamentName', ''), tournament.get('categoryName', '')
            if classify(label, country) != 'DOMESTIC_CUP' or excluded(label):
                continue
            context = 'OFFICIAL_ALIAS_DOMESTIC_CUP'
            candidates = {club for league, members in roster.items() if binding_by_comp[league]['provider_country'] == country for club in members}
        for i in (1, 2):
            pid, name = str(f.get(f'participant{i}Id', '')), f.get(f'participant{i}Name', '')
            if raw['participants'].get(pid) != name:
                continue
            spelling = club_spelling(name, designators=True)
            matches = [club for club in candidates if spelling in {club_spelling(n, designators=True) for n in names[club]}]
            if context == 'OFFICIAL_ALIAS_DOMESTIC_CUP':
                matches = [club for club in matches if (club, pid, name) in official_aliases]
            if len(matches) == 1:
                club = matches[0]
                observation = dict(provider_id=pid, provider_name=name, competition_id=comp or member_comp[club], fixture_id=f['fixtureId'], fixture_start=f['startTime'])
                if context != 'LEAGUE':
                    observation.update(fixture_context=context, membership_competition_id=member_comp[club], provider_tournament_id=str(f['tournamentId']))
                observations[club].append(observation)
    proofs = []
    for club, obs in sorted(observations.items()):
        if len({r['provider_id'] for r in obs}) != 1 or len({r['provider_name'] for r in obs}) != 1:
            continue
        pid, name = obs[0]['provider_id'], obs[0]['provider_name']
        reviewed = (club, pid, name) in explicit
        proofs.append(dict(internal_id=club, provider_id=pid, provider_name=name, checked_at=review_date, normalization='EXPLICIT_REVIEWED_ALIAS' if reviewed else 'LEGAL_DESIGNATORS_ONLY', basis='Unique reviewed current-league roster alias, exact fixture competition and corroborated provider participant ID; no fuzzy or name-only runtime joins.', observations=sorted(obs, key=lambda r:(r['fixture_id'],r['competition_id']))))
    id_counts = defaultdict(int)
    for r in proofs:
        id_counts[r['provider_id']] += 1
    proofs = [r for r in proofs if id_counts[r['provider_id']] == 1]
    unmatched = sorted(active - {r['internal_id'] for r in proofs})
    audit = dict(checked_at='2026-10-09', source_path=str(source.relative_to(REPO)), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), source_generated_at=raw.get('tournaments_reused_from', raw['generated_at']), live_verification=True, mappings=bindings, unmapped_competition_ids=[], unmapped_reason='', club_mapping_status='PARTIAL_EXACT_FIXTURE_VERIFIED' if unmatched else 'VERIFIED_EXACT_FIXTURE_COMPLETE', club_mapping_reason='Unresolved identities require additional official/provider alias or fixture corroboration; quota is available.', health_source=str(raw_path.relative_to(REPO)), club_mappings=proofs, raw_source=str(raw_path.relative_to(REPO)), raw_sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest(), unmapped_active_club_ids=unmatched, unresolved_clubs=[dict(club_id=c, canonical_name=clubs[c]['canonical_name'], country_id=clubs[c]['country_id'], reason='NO_CORROBORATED_EXACT_PROVIDER_IDENTITY_IN_BOUNDED_SAMPLE', resolution='Official/provider alias confirmation or exact current-league fixture; preserve IDs and leave unresolved.') for c in unmatched])
    audit['checked_at'] = review_date
    if not unmatched:
        audit['club_mapping_reason'] = 'All active scoped club identities have exact provider participant and fixture corroboration; this is identity coverage, not live odds availability.'
    write(ROOT / 'research/provider_mapping_audit_2026_10_09.json', audit)
    with (ROOT / 'provider_mappings.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['entity_type','internal_id','provider','provider_id','verification_status'], lineterminator='\n')
        writer.writeheader()
        for entity, records in [('competition', bindings), ('club', proofs)]:
            for r in sorted(records, key=lambda x:x['internal_id']):
                writer.writerow(dict(entity_type=entity, internal_id=r['internal_id'], provider='oddspapi', provider_id=r['provider_id'], verification_status='VERIFIED_PROVIDER_SNAPSHOT'))
    print(json.dumps(dict(competitions=len(bindings), clubs=len(proofs), unresolved_clubs=len(unmatched))))


if __name__ == '__main__':
    main()
