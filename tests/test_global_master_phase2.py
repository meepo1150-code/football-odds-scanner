"""Staging mutation tests; no network or production table writes."""
import csv
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

REPO=Path(__file__).resolve().parents[1]
STAGING=REPO/'data/research/global_master_phase2'


def load(name):
    spec=importlib.util.spec_from_file_location('phase2_'+name,STAGING/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


validator=load('validate');builder=load('build')


@pytest.fixture
def staging(tmp_path):
    root=tmp_path/'staging';shutil.copytree(STAGING,root);return root


def mutate_csv(root,name,fn):
    p=root/name
    with p.open(newline='',encoding='utf-8') as f:
        reader=csv.DictReader(f);fields=reader.fieldnames;data=list(reader)
    fn(data)
    with p.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(data)


def mutate_json(root,name,fn):
    p=root/name;data=json.loads(p.read_text());fn(data);p.write_text(json.dumps(data,ensure_ascii=False))


def test_official_complete_dataset():
    r=validator.audit();assert r['errors']==[]
    assert (r['competitions'],r['clubs'],r['memberships'])==(20,337,337)
    assert r['provider_verified_competitions']==r['provider_verified_participants']==0
    assert r['production_activation_allowed'] is False


@pytest.mark.parametrize('name',['competitions.csv','clubs_canonical.csv','countries.csv','verified_memberships.csv','seasons.csv'])
def test_duplicate_table_rows_fail(staging,name):
    mutate_csv(staging,name,lambda rows:rows.append(dict(rows[0])))
    assert validator.audit(staging)['status']=='FAIL'


@pytest.mark.parametrize('field,value',[
    ('club_id','JPN-ZZZ'),('competition_id','THA-0001'),('country_id','BRN'),
    ('season','2025'),('source_name','Invented Club'),('verification_status','REVIEW'),
    ('source_url',''),('checked_at','2025-01-01'),('division','99')])
def test_invalid_membership_fails(staging,field,value):
    mutate_csv(staging,'verified_memberships.csv',lambda rows:rows[0].update({field:value}))
    assert validator.audit(staging)['status']=='FAIL'


def test_roster_missing_club_fails(staging):
    mutate_csv(staging,'verified_memberships.csv',lambda rows:rows.pop())
    assert validator.audit(staging)['status']=='FAIL'


@pytest.mark.parametrize('field,value',[
    ('expected_teams',19),('season','2025'),('source_url','https://example.com/fake'),
    ('verification_status','REVIEW'),('activation_allowed',True),
    ('history_review_status','ALL_LEGAL_PROMOTION_HISTORY_VERIFIED')])
def test_unproven_roster_claims_fail(staging,field,value):
    mutate_json(staging,'evidence/rosters.json',lambda rows:rows[0].update({field:value}))
    assert validator.audit(staging)['status']=='FAIL'


def test_cannot_hide_missing_team_by_changing_source_count(staging):
    def change(rows):rows[0]['names'].pop();rows[0]['expected_teams']-=1
    mutate_json(staging,'evidence/rosters.json',change)
    assert validator.audit(staging)['status']=='FAIL'


def test_competition_activation_fails(staging):
    mutate_csv(staging,'competitions.csv',lambda rows:rows[0].update(status='VERIFIED_OFFICIAL'))
    assert validator.audit(staging)['status']=='FAIL'


def test_country_namespace_cannot_hide_cross_border_team(staging):
    mutate_csv(staging,'clubs_canonical.csv',lambda rows:next(r for r in rows if r['country_id']=='BRN').update(country_id='MYS'))
    assert validator.audit(staging)['status']=='FAIL'


def test_reserve_cannot_reuse_parent_first_team(staging):
    def change(rows):
        reserve=next(r for r in rows if r['squad_type']=='RESERVE');reserve['club_id']=reserve['parent_club_id']
    mutate_json(staging,'evidence/identity_ledger.json',change)
    assert validator.audit(staging)['status']=='FAIL'


@pytest.mark.parametrize('field,value',[('provider','propline'),('verification_status','VERIFIED_PROVIDER_SNAPSHOT'),('activation_allowed',True),('source_sha256','fabricated')])
def test_provider_namespace_and_activation_fail(staging,field,value):
    mutate_json(staging,'evidence/provider_candidates.json',lambda rows:rows[0].update({field:value}))
    assert validator.audit(staging)['status']=='FAIL'


def test_unproven_provider_id_fails(staging):
    mutate_json(staging,'evidence/provider_candidates.json',lambda rows:rows[0]['candidates'][0].update(provider_id='999999999'))
    assert validator.audit(staging)['status']=='FAIL'


def test_participant_candidate_never_verified_by_label(staging):
    mutate_json(staging,'evidence/participant_candidates.json',lambda rows:rows[0].update(verification_status='VERIFIED'))
    assert validator.audit(staging)['status']=='FAIL'


def test_season_stage_cannot_be_extended(staging):
    mutate_csv(staging,'seasons.csv',lambda rows:next(r for r in rows if r['competition_id']=='COL-0001').update(verified_stages='Liga I|Liga II'))
    assert validator.audit(staging)['status']=='FAIL'


def test_existing_master_and_exclusions_are_hash_preserved(staging,tmp_path):
    repo=tmp_path/'repo';shutil.copytree(REPO/'data/master',repo/'data/master')
    shutil.copytree(REPO/'data/research/global_master_phase1',repo/'data/research/global_master_phase1')
    (repo/'reports').mkdir();shutil.copy2(REPO/'reports/master_provider_snapshot.json',repo/'reports/master_provider_snapshot.json')
    mutate_csv(repo,'data/master/competitions.csv',lambda rows:next(r for r in rows if r['status']=='EXCLUDED_USER').update(status='VERIFIED_OFFICIAL'))
    r=validator.audit(staging,repo)
    assert r['status']=='FAIL' and 'EXCLUDED_USER changed' in r['errors']


def test_deterministic_projection_and_isolated_build(staging):
    before={p.name:p.read_bytes() for p in staging.glob('*.csv')}
    history={p:p.read_bytes() for p in [REPO/'data/master/memberships.csv',REPO/'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl',REPO/'apps/dashboard/index.html']}
    builder.build(staging);assert before=={p.name:p.read_bytes() for p in staging.glob('*.csv')}
    builder.build(staging);assert before=={p.name:p.read_bytes() for p in staging.glob('*.csv')}
    assert all(p.read_bytes()==b for p,b in history.items())


def test_production_readers_exclude_staging():
    from odds_scanner.master_scan_scope import approved_competitions, forward_mappings
    assert not set(validator.EXPECTED)&set(approved_competitions())
    assert not set(validator.EXPECTED)&set(forward_mappings().values())
    for p in (REPO/'src').rglob('*.py'):
        assert 'global_master_phase2' not in p.read_text()


def test_cached_fixture_identity_must_exist_in_snapshot(staging):
    def change(rows):
        record=next(p for p in rows if p['cached_fixture_evidence'])
        record['cached_fixture_evidence'][0]['participant_id']='999999999'
    mutate_json(staging,'evidence/participant_candidates.json',change)
    assert validator.audit(staging)['status']=='FAIL'


def test_promotion_review_cannot_disagree_with_current_roster(staging):
    mutate_json(staging,'evidence/change_review.json',lambda rows:rows[0]['expected_current_members'].pop())
    assert validator.audit(staging)['status']=='FAIL'


def test_withdrawn_membership_cannot_be_reintroduced(staging):
    def change(rows):
        row=next(c for c in rows if c['competition_id']=='MYS-0001')
        row['excluded_from_current_membership']=['DPMM FC']
    mutate_json(staging,'evidence/change_review.json',change)
    assert validator.audit(staging)['status']=='FAIL'


def test_association_cannot_claim_foreign_competition(staging):
    mutate_json(staging,'evidence/associations.json',lambda rows:rows[0]['competition_ids'].append('CAN-0001'))
    assert validator.audit(staging)['status']=='FAIL'
