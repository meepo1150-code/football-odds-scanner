import copy
import json
from pathlib import Path
import pytest
from scripts import promote_sep15_17_historical as p

@pytest.fixture
def example(monkeypatch):
    monkeypatch.setattr(p,'EXPECTED_CANDIDATES',1)
    monkeypatch.setattr(p,'EXPECTED_ROWS',1)
    monkeypatch.setattr(p,'EXPECTED_BY_DAY',{'2026-09-15':1})
    times=['2026-09-15T08:00:00+00:00','2026-09-15T11:00:00+00:00','2026-09-15T14:00:00+00:00','2026-09-15T17:00:00+00:00']
    c=dict(fixture_id='exact-id',bookmaker='pinnacle',home='Home',away='Away',league='League',kickoff='2026-09-15T19:00:00+00:00',football_day='2026-09-15',all_requested_rounds=times)
    base={**c,'favorite_side':'H','observed_at':'2026-09-15T10:01:00+00:00','one_x_two':{'home':1.7},'ou':{'line':2.5},'ah':{'home_line':-.25}}
    quote=dict(price=1.95,quote_at_utc='2026-09-15T07:59:00+00:00',active=True)
    selected=dict(fixture_id='exact-id',bookmaker='pinnacle',status='COMPLETE',market='AH',line=-.25,line_selection='BALANCED_LINE',catalog_evidence='Pinned reviewed full-time AH catalog',market_id='1070',raw_record_hash='a'*64,quotes={'home':dict(quote),'away':dict(quote)})
    slots=[dict(slot_utc=t,status='MAINLINE_UNRESOLVED',selected=None) for t in times]
    slots[0].update(status='BALANCED_LINE',selected=selected,official_mainline_verified=False)
    report=dict(status='COMPLETED',errors=[],production_writes=0,production_quota_delta=0,results=[dict(fixture_id='exact-id',bookmaker='pinnacle',slots=slots)])
    return report,{'candidates':[c]},base

def test_original_line_archive_other_dates_unchanged_and_idempotent(example,tmp_path):
    report,manifest,base=example
    original=json.dumps(base,ensure_ascii=False)+'\n'
    outside={**base,'fixture_id':'other','football_day':'2026-09-14'}
    other=json.dumps(outside,separators=(',',':'))+'\n'
    (tmp_path/p.SOURCE).parent.mkdir(parents=True)
    (tmp_path/p.SOURCE).write_text(original+other)
    (tmp_path/p.NATIVE).write_text('')
    (tmp_path/'reports').mkdir()
    before=(tmp_path/p.SOURCE).read_bytes()
    p.promote(report,manifest,tmp_path,dry_run=True)
    assert (tmp_path/p.SOURCE).read_bytes()==before
    receipt=p.promote(report,manifest,tmp_path)
    assert (tmp_path/p.ARCHIVE).read_text()==original
    assert (tmp_path/p.SOURCE).read_text().startswith(other)
    rows=p.read_rows((tmp_path/p.SOURCE).read_bytes());new=rows[-1]
    assert new['observed_at']=='2026-09-15T07:59:00+00:00'
    assert new['scheduled_target_at']=='2026-09-15T08:00:00+00:00'
    assert new['mainline_verified'] is False and new['data_origin']=='BACKFILLED'
    assert new['one_x_two']=={} and new['ou']=={}
    after=(tmp_path/p.SOURCE).read_bytes()
    assert p.promote(report,manifest,tmp_path)['idempotent_noop']
    assert (tmp_path/p.SOURCE).read_bytes()==after
    assert receipt['archived_original_rows']==1

@pytest.mark.parametrize('change',[ 'inactive','future','stale','bad_price','bad_line','foreign_id','official','wrong_slot','identity','unclean'])
def test_fail_closed(example,change):
    report,manifest,base=copy.deepcopy(example)
    slot=report['results'][0]['slots'][0];s=slot['selected'];q=s['quotes']['home']
    if change=='inactive':q['active']=False
    elif change=='future':q['quote_at_utc']='2026-09-15T08:00:01+00:00'
    elif change=='stale':q['quote_at_utc']='2026-09-15T06:59:59+00:00'
    elif change=='bad_price':q['price']=float('nan')
    elif change=='bad_line':s['line']=-.3
    elif change=='foreign_id':s['fixture_id']='different'
    elif change=='official':slot['official_mainline_verified']=True
    elif change=='wrong_slot':slot['slot_utc']='2026-09-15T09:00:00+00:00'
    elif change=='identity':base['away']='Unverified'
    elif change=='unclean':report['production_quota_delta']=1
    with pytest.raises(ValueError):p.plan(report,manifest,[base],[])

def test_giving_side_changes_with_signed_line(example):
    report,manifest,base=example
    report['results'][0]['slots'][0]['selected']['line']=.25
    rows,_,_=p.plan(report,manifest,[base],[])
    assert rows[0]['favorite_side']=='A'
    assert rows[0]['ah']['selected_side_line']==-.25

def test_preserves_level_side_without_inventing_1x2(example):
    report,manifest,base=example
    report['results'][0]['slots'][0]['selected']['line']=0
    rows,_,_=p.plan(report,manifest,[base],[])
    assert rows[0]['favorite_side_basis']=='ORIGINAL_OBSERVED_COHORT_SIDE_LEVEL_AH'
    assert rows[0]['one_x_two']=={}
