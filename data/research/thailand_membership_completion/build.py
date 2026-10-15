"""Offline Thai roster supplement. Never imports or writes production tables."""
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
API = 'https://competition.tl.prod.c0d1um.io/thaileague/api/'
PINNED = {
    'evidence.json': '6a9c979a474945686776976bb51178b9424a8ec7defacc7795b39503b3868c38',
    'identity_ledger.json': 'a2ba0b95a71687db9a3ed6407f3a587c28e187a6b179fae50b2ee441ccb49b9d',
}
LEAGUES = [('THA-0001', 224, 207, 16, 1), ('THA-0002', 226, 208, 18, 2)]


def read(path):
    return json.loads(path.read_text())


def construct(root=ROOT, repo=REPO):
    for filename, digest in PINNED.items():
        assert hashlib.sha256((root/filename).read_bytes()).hexdigest() == digest, filename+' evidence changed'
    receipts = read(root/'evidence.json')
    evidence = {r['url'].removeprefix(API): r['records'] for r in receipts}
    assert len(evidence) == len(receipts) == 9
    assert all(r['url'].startswith(API) and re.fullmatch('[0-9a-f]{64}', r['raw_sha256'])
               and r['retrieved_at'].startswith('2026-10-15T') for r in receipts)
    seasons = evidence['season-dropdown-public/']
    assert next(s for s in seasons if s['id'] == 33)['year'] == '2026/2027'
    assert next(s for s in seasons if s['id'] == 32)['year'] == '2025/2026'
    tournaments = {t['id']: t for t in evidence['tournament-dropdown-public/?season=33']}
    old_tournaments = {t['id']: t for t in evidence['tournament-dropdown-public/?season=32']}
    ledger = read(root/'identity_ledger.json')
    assert len(ledger) == len({r['club_id'] for r in ledger}) == len({r['official_club_id'] for r in ledger}) == 34
    with (repo/'data/master/competitions.csv').open() as f:
        existing = {r['competition_id']: r for r in csv.DictReader(f)}
    used = set(); existing_names = set()
    for path in [repo/'data/master/teams.csv', repo/'data/master/uefa_clubs_canonical.csv'] + [
            repo/f'data/research/global_master_{phase}/clubs_canonical.csv' for phase in ['phase1', 'phase2']]:
        with path.open() as f:
            for row in csv.DictReader(f):
                used.add(row.get('club_id', row.get('team_id')))
                existing_names.add((row.get('country_id'), row.get('canonical_name', '').casefold()))
    clubs = []; memberships = []; aliases = []; changes = []; competitions = []
    for cid, tid, old_tid, count, division in LEAGUES:
        assert existing[cid]['status'] == 'REVIEW'  # no duplicated or excluded competition
        tournament = tournaments[tid]
        assert tournament['name_en'].endswith('2026/27') and old_tid in old_tournaments
        expected_name = 'BYD SEALION 6 LEAGUE I 2026/27' if division == 1 else 'BYD SEAL 5 LEAGUE II 2026/27'
        assert tournament['name_en'] == expected_name
        source = f'tournament-team-dropdown-public/?tournament={tid}'
        teams = evidence[source]
        standings = evidence[f'stage-standing-public/dashboard/?tournament={tid}']
        assert len(teams) == len(standings) == count
        assert {(r['id'], r['name'], r['name_en']) for r in teams} == {
            (r['tournament_team'], r['tournament_team_name'], r['tournament_team_name_en']) for r in standings}
        assert all(r['stage_name_en'] == tournament['name_en'] for r in standings)
        assignments = {r['official_club_id']: r for r in ledger if r['competition_id'] == cid}
        assert set(assignments) == {r['club_id'] for r in teams}
        competitions.append(dict(competition_id=cid, official_name=tournament['name_en'],
            season='2026/27', expected_teams=count, division=division, existing_competition=True,
            verification_status='VERIFIED_OFFICIAL_CURRENT_ROSTER', activation_allowed=False,
            format_review='Regular-season league evidenced; playoff, licensing and activation rules require separate review'))
        for team in teams:
            club = assignments[team['club_id']]
            assert re.fullmatch(r'THA-[A-Z]{3}', club['club_id']) and club['club_id'] not in used
            assert ('THA', club['canonical_name'].casefold()) not in existing_names
            assert (club['canonical_name'], club['official_name'], club['official_tournament_team_id']) == (team['name_en'], team['name'], team['id'])
            assert club['country_id'] == 'THA' and club['season'] == '2026/27' and club['activation_allowed'] is False
            clubs.append(dict(club_id=club['club_id'], country_id='THA', canonical_name=club['canonical_name'],
                season_membership_status='SOURCE_VERIFIED_CURRENT', canonical_club_id=club['club_id']))
            memberships.append(dict(season='2026/27', country_id='THA', division=division,
                competition_id=cid, competition_name=tournament['name_en'], club_id=club['club_id'],
                source_name=team['name'], source_url=API+source, verification_status='VERIFIED_OFFICIAL', checked_at='2026-10-15'))
            aliases.append(dict(club_id=club['club_id'], alias=team['name'], source_url=API+source,
                verification_status='VERIFIED_OFFICIAL', season='2026/27'))
        old = {r['club_id']: r for r in evidence[f'tournament-team-dropdown-public/?tournament={old_tid}']}
        current = {r['club_id']: r for r in teams}
        for official_id in sorted(old.keys() | current.keys()):
            if official_id not in old or official_id not in current:
                changes.append(dict(competition_id=cid, official_club_id=official_id,
                    name=(current.get(official_id) or old[official_id])['name_en'],
                    status='JOINED_ROSTER' if official_id in current else 'LEFT_ROSTER',
                    previous_season='2025/26', current_season='2026/27',
                    mechanism='REVIEW_NOT_INFERRED_FROM_MEMBERSHIP_CHANGE',
                    previous_source=API+f'tournament-team-dropdown-public/?tournament={old_tid}', current_source=API+source))
    def csv_text(data, key):
        output = io.StringIO(newline='')
        writer = csv.DictWriter(output, fieldnames=list(data[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(sorted(data, key=lambda r:r[key]))
        return output.getvalue()
    payload = dict(competitions=competitions, aliases=aliases, membership_changes=changes,
        new_competitions=0, new_canonical_clubs=34, memberships=34,
        countries_added=0, provider_requests_used=0, activation_allowed=False,
        history_status='Previous and current official roster differences verified; promotion/relegation legal mechanism not certified',
        evidence_hashes=PINNED)
    return {'clubs_canonical.csv': csv_text(clubs, 'club_id'),
            'verified_memberships.csv': csv_text(memberships, 'club_id'),
            'qa.json': json.dumps(payload, ensure_ascii=False, indent=2)+'\n'}


def validate(root=ROOT, repo=REPO):
    expected = construct(root, repo)
    for name, content in expected.items():
        assert (root/name).read_text() == content, name+' differs from deterministic build'
    return {'status': 'PASS', 'new_competitions': 0, 'clubs': 34, 'memberships': 34, 'activation_allowed': False}


if __name__ == '__main__':
    if '--write' in sys.argv:
        for name, content in construct().items():
            (ROOT/name).write_text(content)
    print(json.dumps(validate(), indent=2))
