"""No-network expansion mapping and canonical-slot response coverage regressions."""
import copy
import hashlib
import importlib.util
import json
from datetime import datetime,timezone
from pathlib import Path
import pytest


REPO=Path(__file__).resolve().parents[1]
ROOT=REPO/'data/research/global_expansion_readiness'
_audit_spec=importlib.util.spec_from_file_location('staging_expansion_audit',ROOT/'audit.py')
audit=importlib.util.module_from_spec(_audit_spec);_audit_spec.loader.exec_module(audit)
spec=importlib.util.spec_from_file_location('readiness_builder',ROOT/'build.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
NOW=datetime(2026,10,15,8,5,tzinfo=timezone.utc)
START='2026-10-15T05:00:00+00:00';END='2026-10-15T23:00:00+00:00'

@pytest.fixture(scope='module')
def identity():return json.loads((ROOT/'identity_review.json').read_text())

@pytest.fixture(scope='module')
def members():return audit.memberships(REPO)

@pytest.fixture

def fixture(identity):
    raw=json.loads((REPO/'reports/master_provider_snapshot.json').read_text())
    return copy.deepcopy(next(f for f in raw['fixtures'] if f['tournamentId']==19232 and f['participant1Name']=='Khon Kaen United FC'))


def response(fixture):
    return dict(provider='oddspapi',endpoint='/fixtures',params=dict(sportId=10,limit=1000,
        **{'from':START,'to':END}),observed_at='2026-10-15T08:03:00+00:00',response_id='unit-test-only',payload=[fixture])


def run(tmp_path,identity,members,responses=(),snapshots=()):
    return audit.audit(tmp_path,now=NOW,football_day='2026-10-15',identity=identity,
        responses=list(responses),snapshots=list(snapshots),member_rows=members)


def thai(result):return next(r for r in result['leagues'] if r['competition_id']=='THA-0002')


def test_identity_rebuild_and_preserved_verified_ids(identity):
    assert builder.build()==identity
    assert identity['counts']==dict(competitions=33,clubs=588,
        verified_cached_competition_identities=26,verified_cached_participant_identities=300)
    assert identity['identity_delta']==dict(verified_cached_competition_identities=2,
        verified_cached_participant_identities=30)


@pytest.mark.parametrize('filename,function', [('korean_official_aliases.json',builder.aliases),
    ('matchday_official_aliases.json',builder.matchday_aliases)])
def test_tampered_official_evidence_fails_closed(tmp_path,filename,function):
    p=tmp_path/filename;p.write_bytes((ROOT/filename).read_bytes()+b' ')
    with pytest.raises(AssertionError,match='hash mismatch'):function(p)


def test_bilingual_squads_and_legal_designators_remain_distinct():
    a=builder.aliases()
    assert any(r['club_id']=='KOR-GIM' and r['alias']=='Gimcheon Sangmu' for r in a)
    assert any(r['club_id']=='KOR-ULS' and r['alias']=='ULSAN HD' for r in a)
    assert all(r['competition_id']!='KOR-0003' for r in a)
    assert all(r['alias']!='Suwon Bluewings' for r in a) # not supplied by official profile
    rows=builder.matchday_aliases()
    assert next(r for r in rows if r['club_id']=='SAU-AHL')['alias']=='Al Ahli Saudi'
    assert next(r for r in rows if r['club_id']=='THA-AAL')['alias']=='UTTARADIT SAKSIAM FC'


def test_waiting_is_not_success_or_no_matches(tmp_path,identity,members):
    r=run(tmp_path,identity,members)
    assert len(r['leagues'])==33 and r['counts']['clubs']==588
    assert r['counts']['provider_unresolved_clubs']==288
    assert all(x['schedule_status']=='WAITING_1500_FIXTURE_RESPONSE' for x in r['leagues'])
    assert r['full_scope_live_test_gate']['allowed'] is False
    assert r['full_scope_live_test_gate']['minimum_odds_requests']==7
    assert r['provider_requests_used']==0 and not r['activation_allowed'] and not r['phase3_expansion_allowed']


def test_real_shaped_response_matches_both_ids_separately_from_price(tmp_path,identity,members,fixture):
    r=run(tmp_path,identity,members,[response(fixture)])
    assert thai(r)['matched_fixtures']==1
    assert thai(r)['schedule_status']=='RETURNED_FIXTURE_IDENTITIES_MATCHED'
    assert thai(r)['price_status']=='NOT_REQUESTED_FOR_EXPANSION'
    assert r['full_scope_live_test_gate']['allowed'] is False # whole roster still partial


@pytest.mark.parametrize('mutation',['foreign_provider','old_response','wrong_day','future_response','filtered_league','wrong_sport'])
def test_unrelated_receipts_cannot_prove_1500_coverage(tmp_path,identity,members,fixture,mutation):
    x=response(fixture)
    if mutation=='foreign_provider':x['provider']='propline'
    if mutation=='old_response':x['observed_at']='2026-10-15T07:59:59+00:00'
    if mutation=='future_response':x['observed_at']='2026-10-15T08:06:00+00:00'
    if mutation=='wrong_day':x['params']['from']='2026-10-14T05:00:00+00:00'
    if mutation=='filtered_league':x['params']['tournamentId']=19232
    if mutation=='wrong_sport':x['params']['sportId']=1
    assert run(tmp_path,identity,members,[x])['schedule_response_id'] is None


@pytest.mark.parametrize('mutation',['unmapped_id','changed_name','same_id','wrong_tournament_name','missing_fixture_id'])
def test_invalid_fixture_fails_closed(tmp_path,identity,members,fixture,mutation):
    if mutation=='unmapped_id':fixture['participant1Id']='missing'
    if mutation=='changed_name':fixture['participant1Name']='Unreviewed new name'
    if mutation=='same_id':fixture['participant2Id']=fixture['participant1Id']
    if mutation=='wrong_tournament_name':fixture['tournamentName']='Another league'
    if mutation=='missing_fixture_id':fixture.pop('fixtureId')
    r=run(tmp_path,identity,members,[response(fixture)])
    assert thai(r)['matched_fixtures']==0 and thai(r)['schedule_status']=='FIXTURE_MAPPING_BLOCKED'


def test_truncation_prevents_complete_coverage_claim(tmp_path,identity,members,fixture):
    x=response(fixture);x['params']['limit']=1
    r=run(tmp_path,identity,members,[x]);assert not r['schedule_response_complete']
    assert thai(r)['schedule_status']=='PARTIAL_FIXTURE_RESPONSE'


def test_empty_response_does_not_claim_league_has_no_matches(tmp_path,identity,members,fixture):
    x=response(fixture);x['payload']=[]
    r=run(tmp_path,identity,members,[x])
    assert all(y['schedule_status']=='NO_FIXTURES_RETURNED_NOT_PROOF_OF_NO_MATCHES' for y in r['leagues'])


def test_conflicting_fixture_versions_rejected(tmp_path,identity,members,fixture):
    x=response(fixture);other=copy.deepcopy(fixture);other['participant1Id']='conflict';x['payload'].append(other)
    r=run(tmp_path,identity,members,[x]);assert thai(r)['matched_fixtures']==0
    assert 'CONFLICTING_FIXTURE_VERSIONS' in thai(r)['fixture_details'][0]['reasons']


def test_identical_duplicate_fixture_does_not_inflate(tmp_path,identity,members,fixture):
    x=response(fixture);x['payload']*=3
    assert thai(run(tmp_path,identity,members,[x]))['returned_fixtures']==1


def test_foreign_snapshot_namespace_cannot_certify_odds(tmp_path,identity,members,fixture):
    s=dict(fixture_id=fixture['fixtureId'],tournament_id=19232,observed_at='2026-10-15T08:03:30+00:00',
        mainline_verified=True,source_semantics='PROPLINE_PINNACLE_TWO_SIDED_CORE_MAINLINE')
    assert thai(run(tmp_path,identity,members,[response(fixture)],[s]))['valid_odds_fixtures']==0


def test_verified_odds_distinct_from_fixture_match(tmp_path,identity,members,fixture):
    s=dict(fixture_id=fixture['fixtureId'],tournament_id=19232,observed_at='2026-10-15T08:03:30+00:00',
        mainline_verified=True,source_semantics='CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED')
    assert thai(run(tmp_path,identity,members,[response(fixture)],[s]))['price_status']=='VALID_ODDS_OBSERVED'


def test_wrong_scope_and_duplicate_memberships_rejected(tmp_path,identity,members):
    with pytest.raises(ValueError,match='complete and unique'):run(tmp_path,identity,members+members[:1])
    damaged=copy.deepcopy(identity);damaged['clubs'].pop()
    with pytest.raises(ValueError,match='exactly 33'):run(tmp_path,damaged,members)


def test_conflicting_participant_ids_rejected(tmp_path,identity,members):
    damaged=copy.deepcopy(identity);verified=[c for c in damaged['clubs'] if c.get('provider_id')]
    verified[1]['provider_id']=verified[0]['provider_id']
    with pytest.raises(ValueError,match='Conflicting'):run(tmp_path,damaged,members)


def test_workflow_is_read_only_and_cannot_run_from_pr():
    workflow=(REPO/'.github/workflows/global-expansion-readiness.yml').read_text()
    assert 'contents: read' in workflow and 'contents: write' not in workflow
    assert 'secrets.' not in workflow and 'git push' not in workflow
    assert "head_branch == 'main'" in workflow
    assert "head_repository.full_name == github.repository" in workflow
    assert "event != 'pull_request'" in workflow
    assert 'actions/upload-artifact@' in workflow
    assert 'schedule:' not in workflow
