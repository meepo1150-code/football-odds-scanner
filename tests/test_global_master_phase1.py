"""Mutation regressions for the isolated global roster dataset."""
import csv
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

REPO=Path(__file__).resolve().parents[1]
STAGING=REPO/'data/research/global_master_phase1'
spec=importlib.util.spec_from_file_location('global_master_audit',STAGING/'validate.py')
validator=importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


@pytest.fixture
def staging(tmp_path):
    target=tmp_path/'dataset'
    shutil.copytree(STAGING,target)
    return target


def mutate(root,name,change):
    p=root/name
    with p.open(encoding='utf-8',newline='') as f:
        reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    change(rows)
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)


def test_verified_staging_is_complete():
    report=validator.audit()
    assert report['errors']==[]
    assert report['competitions']==11 and report['clubs']==217
    assert report['new_countries']==7 and report['reused_countries']==3


@pytest.mark.parametrize('table,key',[
    ('countries.csv','country_id'),('competitions.csv','competition_id'),
    ('clubs_canonical.csv','club_id'),('verified_memberships.csv','club_id')])
def test_duplicate_keys_rejected(staging,table,key):
    mutate(staging,table,lambda rows:rows.append(dict(rows[0])))
    assert any('Duplicate' in e for e in validator.audit(staging,REPO)['errors'])


@pytest.mark.parametrize('field,value',[
    ('club_id','JPN-ZZZ'),('competition_id','JPN-9999'),('season','2025'),
    ('source_url',''),('verification_status','REVIEW'),('source_name','Fabricated club')])
def test_invalid_membership_rejected(staging,field,value):
    mutate(staging,'verified_memberships.csv',lambda rows:rows[0].update({field:value}))
    assert validator.audit(staging,REPO)['status']=='FAIL'


def test_same_club_second_code_rejected(staging):
    def duplicate(rows):
        row=dict(rows[0]);row.update(club_id='JPN-ZZZ',canonical_club_id='JPN-ZZZ');rows.append(row)
    mutate(staging,'clubs_canonical.csv',duplicate)
    assert 'Duplicate normalized club identity' in validator.audit(staging,REPO)['errors']


def test_missing_roster_member_rejected(staging):
    mutate(staging,'verified_memberships.csv',lambda rows:rows.pop())
    assert any('Official roster mismatch' in e for e in validator.audit(staging,REPO)['errors'])


def test_candidate_provider_id_must_have_evidence(staging):
    p=staging/'evidence/provider_candidates.json';data=json.loads(p.read_text())
    data[0]['provider_id']='999999999';p.write_text(json.dumps(data))
    assert 'Unproven provider ID' in validator.audit(staging,REPO)['errors']


def test_unverified_alias_rejected(staging):
    p=staging/'evidence/aliases.json';data=json.loads(p.read_text())
    data[0]['verification_status']='REVIEW';p.write_text(json.dumps(data))
    assert 'Unverified alias evidence' in validator.audit(staging,REPO)['errors']


def test_expected_count_cannot_hide_missing_team(staging):
    p=staging/'evidence/rosters.json';data=json.loads(p.read_text())
    data[0]['expected_teams']=19;p.write_text(json.dumps(data))
    assert any('Expected roster count mismatch' in e for e in validator.audit(staging,REPO)['errors'])


def test_future_mexico_stage_cannot_be_claimed_verified(staging):
    def change(rows):
        next(r for r in rows if r['competition_id']=='MEX-0001')['verified_stages']='Apertura|Clausura'
    mutate(staging,'seasons.csv',change)
    assert 'Unverified season stage' in validator.audit(staging,REPO)['errors']


def test_announced_australia_season_not_claimed_active(staging):
    def change(rows):
        next(r for r in rows if r['competition_id']=='AUS-0001')['temporal_state']='CURRENT'
    mutate(staging,'seasons.csv',change)
    assert 'Wrong season temporal state' in validator.audit(staging,REPO)['errors']


def test_activation_flag_rejected(staging):
    mutate(staging,'competitions.csv',lambda rows:rows[0].update(status='VERIFIED_OFFICIAL'))
    assert 'Staging competition activated' in validator.audit(staging,REPO)['errors']


def test_existing_record_modified_rejected(staging,tmp_path):
    mirror=tmp_path/'repo';shutil.copytree(REPO/'data/master',mirror/'data/master')
    shutil.copytree(REPO/'reports',mirror/'reports')
    mutate(mirror,'data/master/countries.csv',lambda rows:rows[0].update(country_name='Changed'))
    assert 'Baseline changed: data/master/countries.csv' in validator.audit(staging,mirror)['errors']


def test_production_allowlist_does_not_include_staged_competitions():
    from odds_scanner.master_scan_scope import approved_competitions,forward_mappings
    assert not set(validator.ALLOWED_COMPETITIONS)&set(approved_competitions())
    assert not set(validator.ALLOWED_COMPETITIONS)&set(forward_mappings().values())


def test_production_code_has_no_staging_reader():
    for path in (REPO/'src').rglob('*.py'):
        assert 'global_master_phase1' not in path.read_text()
