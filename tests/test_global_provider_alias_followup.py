"""Proven official labels extend staging identities without weakening any gate."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO/'data/research/global_provider_alias_followup'
spec = importlib.util.spec_from_file_location('alias_followup', ROOT/'build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

@pytest.fixture(scope='module')
def result():
    return builder.build()


def test_deterministic_corrobation_and_actual_delta(result):
    assert result == json.loads((ROOT/'review.json').read_text())
    assert result['counts'] == dict(competitions=33,clubs=588,
        verified_cached_competition_identities=24,verified_cached_participant_identities=270)
    assert result['identity_delta'] == dict(verified_cached_competition_identities=2,
        verified_cached_participant_identities=17)


def test_baseline_verified_ids_preserved(result):
    baseline = builder.reviewer.review()
    for field,key in [('competitions','competition_id'),('clubs','club_id')]:
        after = {c[key]:c for c in result[field]}
        for row in baseline[field]:
            if row['provider_id']:
                assert after[row[key]]['provider_id']==row['provider_id']


@pytest.mark.parametrize('field',['activation_allowed','provider_season_stage_verified','live_odds_coverage_verified'])
def test_no_readiness_inferred(result,field):
    assert result[field] is False
    assert all(c['activation_allowed'] is False for c in result['competitions']+result['clubs'])
    assert result['provider_requests_used']==0


def test_alias_tampering_rejected_before_rebuild(tmp_path):
    data = json.loads((ROOT/'evidence.json').read_text())
    data['apf']['records'][0]['nickname']='Invented club'
    path=tmp_path/'evidence.json';path.write_text(json.dumps(data))
    with pytest.raises(AssertionError,match='hash mismatch'):builder.build(path)


@pytest.mark.parametrize('host',['evil.example','www.apf.org.py.evil.example','www.auf.org.uy'])
def test_apf_source_namespace_cannot_be_substituted(host):
    evidence=json.loads((ROOT/'evidence.json').read_text())['apf']
    evidence['source_url']='https://'+host+'/'
    with pytest.raises(AssertionError):builder.check_source(evidence,'www.apf.org.py')


@pytest.mark.parametrize('cid,club,name', [('PRY-0001','URY-NAC','Club Nacional de Football'),
    ('URY-0001','PRY-NAC','Nacional Asunción'),('PRY-0001','PRY-NAC','FC')])
def test_invalid_scoped_alias_fails_closed(cid,club,name):
    with pytest.raises(ValueError):
        builder.reviewer.review(official_aliases=[dict(competition_id=cid,club_id=club,alias=name)])


def test_missing_fixture_evidence_never_upgrades_with_aliases():
    snapshot=json.loads((REPO/'reports/master_provider_snapshot.json').read_text())
    snapshot['fixtures']=[]
    result=builder.build(snapshot=snapshot)
    assert result['counts']['verified_cached_competition_identities']==0
    assert result['counts']['verified_cached_participant_identities']==0


def test_provider_catalog_mismatch_never_upgrades_with_aliases():
    snapshot=json.loads((REPO/'reports/master_provider_snapshot.json').read_text())
    snapshot['participants']={}
    result=builder.build(snapshot=snapshot)
    assert result['counts']['verified_cached_participant_identities']==0


def test_remaining_work_exact_and_reserve_still_unresolved(result):
    assert sum(len(r['unresolved_club_ids']) for r in result['remaining_work'])==318
    assert sum(r['cached_identity_status']=='REVIEW' for r in result['remaining_work'])==9
    assert all(not r['activation_allowed'] for r in result['remaining_work'])
    reserve=next(c for c in result['clubs'] if c['canonical_name']=='전북현대 N팀')
    assert reserve['provider_id'] is None


def test_only_official_scoped_records_enter_aliases():
    aliases=builder.aliases()
    assert {a['competition_id'] for a in aliases}=={'PRY-0001','URY-0001'}
    assert len({a['club_id'] for a in aliases if a['competition_id']=='PRY-0001'})==12
    torque=next(a for a in aliases if a['club_id']=='URY-MCT')
    assert torque['official_entity_id']=='/montevideo-city-torque-f11/'
