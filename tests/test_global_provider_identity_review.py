"""Offline fail-closed provider identity and Thai membership regressions."""
import copy
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO/'data/research/global_provider_identity_review'
THAI = REPO/'data/research/thailand_membership_completion'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

reviewer = load('cached_identity_review', ROOT/'review.py')
thai = load('thai_roster_review', THAI/'build.py')

@pytest.fixture(scope='module')
def result():
    return reviewer.review()

def test_deterministic_review_matches_committed_evidence(result):
    assert result == json.loads((ROOT/'review.json').read_text())
    assert result['counts'] == dict(competitions=33, clubs=588,
        verified_cached_competition_identities=22, verified_cached_participant_identities=253)

@pytest.mark.parametrize('field', ['provider_season_stage_verified', 'live_odds_coverage_verified', 'activation_allowed'])
def test_identity_never_certifies_production_readiness(result, field):
    assert result[field] is False
    assert result['provider_requests_used'] == 0
    assert all(c['activation_allowed'] is False for c in result['clubs']+result['competitions'])

def test_verified_participants_have_scoped_two_sided_proof(result):
    selected = {c['competition_id']:c['provider_id'] for c in result['competitions'] if c['provider_id']}
    pids = set()
    for club in result['clubs']:
        if not club['provider_id']: continue
        assert club['provider_id'] not in pids
        pids.add(club['provider_id'])
        assert club['observations']
        for obs in club['observations']:
            assert obs['provider_id'] == club['provider_id']
            assert obs['provider_tournament_id'] == selected[obs['competition_id']]
            assert obs['counterpart']['club_id'] != club['club_id']
            assert obs['counterpart']['provider_id'] != club['provider_id']

def test_source_hashes_and_snapshot_unchanged(result):
    for path, digest in result['source_hashes'].items():
        assert hashlib.sha256((REPO/path).read_bytes()).hexdigest() == digest
    assert result['provider_snapshot_sha256'] == hashlib.sha256((REPO/'reports/master_provider_snapshot.json').read_bytes()).hexdigest()

@pytest.mark.parametrize('left,right,equal', [
    ('FC Zürich', 'Zurich FC', True), ('Port FC', 'Port', True),
    ('Jeonbuk N', 'Jeonbuk', False), ('Club 2', 'Club', False),
    ('ปัตตานี', 'ปตตาน', False), ('강원', '전북', False),
    ('FC', 'SC', True), ('DPMM FC', 'DPMM', True)])
def test_normalization_is_conservative(left, right, equal):
    assert (reviewer.spelling(left) == reviewer.spelling(right)) is equal

@pytest.mark.parametrize('date', ['2026-10-99T00:00:00Z', '2026-10-10', '2026-10-10T01:00:00',
    '2026-09-30T23:59:59Z', '2026-11-01T00:00:00Z', '', None])
def test_invalid_or_outside_dates_fail_closed(date):
    assert not reviewer.in_window(date)

@pytest.fixture
def snapshot():
    raw = json.loads((REPO/'reports/master_provider_snapshot.json').read_text())
    raw['fixtures'] = [f for f in raw['fixtures'] if str(f['tournamentId']) == '28432']
    return raw

def selected(raw):
    result = reviewer.review(snapshot=raw)
    return next(c for c in result['competitions'] if c['competition_id'] == 'CAN-0001')

@pytest.mark.parametrize('mutation', ['no_fixtures', 'one_fixture', 'foreign_opponent', 'missing_fixture_id',
    'catalog_missing', 'catalog_name', 'catalog_country', 'catalog_duplicate', 'participant_catalog',
    'wrong_fixture_tournament_name', 'invalid_date', 'conflicting_fixture_versions', 'empty_names'])
def test_corrupt_or_insufficient_evidence_never_verifies(snapshot, mutation):
    if mutation == 'no_fixtures': snapshot['fixtures'] = []
    elif mutation == 'one_fixture': snapshot['fixtures'] = snapshot['fixtures'][:1]
    elif mutation == 'foreign_opponent':
        for f in snapshot['fixtures']: f['participant2Name'] = 'Unproven Other Club'
    elif mutation == 'missing_fixture_id':
        for f in snapshot['fixtures']: f['fixtureId'] = None
    elif mutation.startswith('catalog_'):
        tournament = next(t for t in snapshot['tournaments'] if str(t['tournamentId']) == '28432')
        if mutation == 'catalog_missing': snapshot['tournaments'].remove(tournament)
        elif mutation == 'catalog_name': tournament['tournamentName'] = 'Another competition'
        elif mutation == 'catalog_country': tournament['categoryName'] = 'Another country'
        else: snapshot['tournaments'].append(copy.deepcopy(tournament))
    elif mutation == 'participant_catalog': snapshot['participants'] = {}
    elif mutation == 'wrong_fixture_tournament_name':
        for f in snapshot['fixtures']: f['tournamentName'] = 'Another league'
    elif mutation == 'invalid_date':
        for f in snapshot['fixtures']: f['startTime'] = '2026-10-99T00:00:00Z'
    elif mutation == 'conflicting_fixture_versions':
        for f in list(snapshot['fixtures']):
            other = copy.deepcopy(f); other['participant1Id'] = 'conflicting'; snapshot['fixtures'].append(other)
    elif mutation == 'empty_names':
        for f in snapshot['fixtures']: f['participant1Name'] = 'FC'
    assert selected(snapshot)['status'] == 'REVIEW'

def test_identical_fixture_duplicates_do_not_inflate_gate(snapshot):
    before = selected(snapshot)
    snapshot['fixtures'] *= 3
    assert selected(snapshot) == before

@pytest.mark.parametrize('field,value', [('provider', 'propline'), ('status', 'UNAVAILABLE')])
def test_namespace_and_unavailable_snapshot_rejected(snapshot, field, value):
    snapshot[field] = value
    with pytest.raises(ValueError): reviewer.review(snapshot=snapshot)

def test_generic_reserve_label_never_resolves_to_first_team(result):
    reserve = next(c for c in result['clubs'] if c['canonical_name'] == '전북현대 N팀')
    assert reserve['status'] == 'UNRESOLVED'
    assert all(o['provider_name'] != '전북현대모터스' for c in result['clubs'] for o in c['observations'])

def test_cross_border_country_retained(result):
    club = next(c for c in result['clubs'] if c['canonical_name'] == 'DPMM FC')
    assert club['country_id'] == 'BRN'

def test_thai_complete_without_new_competitions():
    assert thai.validate() == dict(status='PASS', new_competitions=0, clubs=34, memberships=34, activation_allowed=False)
    qa = json.loads((THAI/'qa.json').read_text())
    assert [c['expected_teams'] for c in qa['competitions']] == [16, 18]
    assert all(c['mechanism'] == 'REVIEW_NOT_INFERRED_FROM_MEMBERSHIP_CHANGE' for c in qa['membership_changes'])

@pytest.mark.parametrize('filename', ['evidence.json', 'identity_ledger.json', 'clubs_canonical.csv', 'verified_memberships.csv', 'qa.json'])
def test_thai_evidence_or_artifact_tampering_fails(tmp_path, filename):
    root = tmp_path/'thai'; shutil.copytree(THAI, root)
    path = root/filename; path.write_text(path.read_text()+' ')
    with pytest.raises(AssertionError): thai.validate(root, REPO)

def test_production_hash_manifest_unchanged():
    baseline = json.loads((REPO/'data/research/global_master_phase2/baseline.json').read_text())
    assert len(baseline['production_hashes']) == 361
    # Scanner workflow files are intentionally changed by the retirement PR.
    # Keep the original hash pins for master evidence, canonical configuration,
    # and application source; workflow retirement is verified independently.
    protected = dict(baseline['continuous_hashes'])
    protected.update({
        p: digest for p, digest in baseline['production_hashes'].items()
        if p.startswith(('src/', 'config/'))
    })
    assert len(protected) >= 35
    # These two files are intentionally modified by the isolated manual-scan PR.
    # Keep every other production hash pin intact.
    manual_scan_changes = {'src/odds_scanner/europe_pinnacle_discovery.py',
                           'src/odds_scanner/research_request_budget.py'}
    # The baseline is an immutable 2026-10-15 evidence snapshot, not a hash
    # manifest of today's production sources. Later reviewed FT/statistics fixes
    # legitimately changed this one source file. Pin the exact reviewed blob,
    # rather than silently skipping its integrity verification.
    approved_evolved_blobs = {
        'src/odds_scanner/research_v2_pattern_stats.py': 'be873b62b72f8a99438f2d686f8b3d1fbf8c2819',
    }
    for path, blob_sha in approved_evolved_blobs.items():
        raw = (REPO/path).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == blob_sha, path
    for path, digest in protected.items():
        if path in approved_evolved_blobs:
            continue
        if path == 'src/odds_scanner/research_v2_slot_recovery.py':
            # The user retired the executable Auto fallback on 18 October.
            assert not (REPO/path).exists()
            continue
        if path in manual_scan_changes:
            continue
        assert hashlib.sha256((REPO/path).read_bytes()).hexdigest() == digest, path


def test_existing_production_competition_conflict_fails_closed(snapshot, monkeypatch):
    original = reviewer.rows
    def read_rows(path):
        data = original(path)
        if path.name == 'provider_mappings.csv':
            data.append(dict(provider='oddspapi', entity_type='competition',
                provider_id='28432', internal_id='OTHER-0001'))
        return data
    monkeypatch.setattr(reviewer, 'rows', read_rows)
    assert selected(snapshot)['status'] == 'REVIEW'


def test_existing_production_participant_conflict_never_overwritten(snapshot, monkeypatch):
    first = snapshot['fixtures'][0]
    pid = str(first['participant1Id'])
    original = reviewer.rows
    def read_rows(path):
        data = original(path)
        if path.name == 'provider_mappings.csv':
            data.append(dict(provider='oddspapi', entity_type='club',
                provider_id=pid, internal_id='OTHER-AAA'))
        return data
    monkeypatch.setattr(reviewer, 'rows', read_rows)
    result = reviewer.review(snapshot=snapshot)
    assert all(c['provider_id'] != pid for c in result['clubs'])


def test_multiple_provider_ids_for_one_club_stay_unresolved(snapshot):
    first = snapshot['fixtures'][0]
    pid = str(first['participant1Id'])
    name = first['participant1Name']
    snapshot['participants']['NEW-PARTICIPANT'] = name
    for fixture in list(snapshot['fixtures']):
        changed = copy.deepcopy(fixture)
        touched = False
        for side in (1, 2):
            if str(changed[f'participant{side}Id']) == pid:
                changed[f'participant{side}Id'] = 'NEW-PARTICIPANT'
                touched = True
        if touched:
            changed['fixtureId'] += '-alternate-id'
            snapshot['fixtures'].append(changed)
    result = reviewer.review(snapshot=snapshot)
    affected = [c for c in result['clubs'] if any(o['provider_id'] == 'NEW-PARTICIPANT' for o in c['observations'])]
    assert affected and all(c['status'] == 'UNRESOLVED' for c in affected)
