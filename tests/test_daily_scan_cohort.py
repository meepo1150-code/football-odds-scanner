import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from odds_scanner import daily_scan_cohort as cohort
from odds_scanner import master_schedule_plan as planner
from odds_scanner import europe_pinnacle_discovery as collector
from odds_scanner.research_v2_slots import completed, read_ledger, read_snapshots
from test_collector_observation_contract import setup


def baseline(root, fixture, monkeypatch):
    monkeypatch.setattr(planner, 'registry', lambda: [
        {'tournament_id':17,'country':'England','tournament_name':'Premier League'},
        {'tournament_id':98,'country':'Norway','tournament_name':'Norwegian First Division'}])
    fixture.update(fixtureId='baseline', startTime='2026-10-14T20:00:00Z', participant1Id=146, participant2Id=147)
    p=root/'data/master/provider_mappings.csv';p.parent.mkdir(parents=True,exist_ok=True);p.write_text('master mode')
    import odds_scanner.master_mapping as mapping
    monkeypatch.setattr(mapping,'load_mappings',lambda: {('oddspapi','competition','17'):'ENG-0001',('oddspapi','club','146'):'ENG-LFC',('oddspapi','club','147'):'ENG-ARS'})
    planner.retain(root,'/fixtures',{'from':'2026-10-14T05:00:00+00:00','to':'2026-10-14T23:00:00+00:00'},[fixture,{'fixtureId':'new','tournamentId':98,'startTime':'2026-10-14T21:00:00Z','statusId':0}],datetime.fromisoformat('2026-10-14T08:01:00+00:00'))
    collector._record_slot(root/collector.SLOT_LEDGER_PATH, {'scheduled_target_at':'2026-10-14T15:00:00+07:00','football_day':'2026-10-14','actual_observed_at':'2026-10-14T15:02:00+07:00','generated_at':'2026-10-14T08:02:00+00:00','request_completed_at':'2026-10-14T08:02:00+00:00','coverage_tournament_ids':[17],'status':'RESEARCH_V2_OBSERVED','requests_used':2,'strict_snapshots_this_run':1,'master_competitions_considered':92},'OBSERVED')


@pytest.mark.parametrize('hour',[11,14,17])
def test_followups_only_query_and_persist_frozen_fixture_ids(tmp_path,monkeypatch,hour):
    clock,f=setup(tmp_path,monkeypatch,now=f'2026-10-14T{hour:02}:03:00+00:00')
    baseline(tmp_path,f,monkeypatch)
    calls=[]
    extra={**f,'fixtureId':'not-in-setup'}
    def get(endpoint,key,params=None,*args):
        calls.append((endpoint,params))
        if endpoint=='/account':return {}
        assert endpoint=='/odds-by-tournaments' and params['tournamentIds']=='17'
        return [f,extra]
    monkeypatch.setattr(collector,'_get',get)
    monkeypatch.delenv('RESEARCH_QUOTA_DURABLE',raising=False)
    result=collector.run(tmp_path)
    assert result['status']=='RESEARCH_V2_OBSERVED'
    assert result['daily_cohort_query_complete'] is True
    assert result['daily_cohort_fixture_count']==1
    assert result['daily_cohort_fixtures'][0]['reason']=='OBSERVED_CORE_ODDS'
    assert result['excluded_outside_daily_cohort']==1
    assert {r['fixture_id'] for r in read_snapshots(tmp_path)}=={'baseline'}
    assert completed(datetime.fromisoformat(result['scheduled_target_at']),clock.current,read_ledger(tmp_path),read_snapshots(tmp_path))


def test_already_started_setup_fixture_is_reported_without_provider_calls(tmp_path,monkeypatch):
    clock,f=setup(tmp_path,monkeypatch,now='2026-10-14T17:03:00+00:00')
    baseline(tmp_path,f,monkeypatch)
    f['startTime']='2026-10-14T16:00:00Z'
    # Retained setup is immutable; use another retained setup with this kickoff.
    path=tmp_path/planner.RAW_PATH
    saved=json.loads(path.read_text());saved['payload'][0]['startTime']=f['startTime'];path.write_text(json.dumps(saved)+'\n')
    monkeypatch.setattr(collector,'_get',lambda *a: pytest.fail('past kickoff must not query'))
    result=collector.run(tmp_path)
    assert result['daily_cohort_fixtures'][0]['reason']=='KICKOFF_PASSED'
    assert result['daily_cohort_query_complete'] and result['requests_used']==0


def test_unrelated_partial_receipt_cannot_close_followup(tmp_path,monkeypatch):
    clock,f=setup(tmp_path,monkeypatch,now='2026-10-14T11:40:00+00:00');baseline(tmp_path,f,monkeypatch)
    target=datetime.fromisoformat('2026-10-14T18:00:00+07:00')
    wrong={'state':'OBSERVED','scheduled_target_at':target.isoformat(),'actual_observed_at':clock.current.isoformat(),'strict_snapshots':5,'coverage_tournament_ids':[98],'provider':'oddspapi'}
    assert not completed(target,clock.current,read_ledger(tmp_path)+[wrong],[])


def test_quota_skip_keeps_per_fixture_gap_and_no_transport(tmp_path,monkeypatch):
    clock,f=setup(tmp_path,monkeypatch,now='2026-10-14T14:03:00+00:00');baseline(tmp_path,f,monkeypatch)
    monkeypatch.setattr(collector,'summarize_account',lambda _: {'request_remaining':10})
    monkeypatch.setattr(collector,'_get',lambda endpoint,*a:{} if endpoint=='/account' else pytest.fail('no paid request'))
    result=collector.run(tmp_path)
    assert result['status']=='SKIPPED_QUOTA' and not result['daily_cohort_query_complete']
    assert result['daily_cohort_fixtures'][0]['reason']=='SKIPPED_QUOTA'


def test_missing_setup_cannot_substitute_new_competitions(tmp_path,monkeypatch):
    clock,f=setup(tmp_path,monkeypatch,now='2026-10-14T14:03:00+00:00')
    p=tmp_path/'data/master/provider_mappings.csv';p.parent.mkdir(parents=True);p.write_text('master mode')
    monkeypatch.setattr(collector,'_get',lambda *a:pytest.fail('no speculative request'))
    assert collector.run(tmp_path)['status']=='DAILY_COHORT_UNAVAILABLE'


def test_real_provider_failure_keeps_original_cohort_and_does_not_complete(tmp_path,monkeypatch):
    clock,f=setup(tmp_path,monkeypatch,now='2026-10-14T14:03:00+00:00');baseline(tmp_path,f,monkeypatch)
    monkeypatch.delenv('RESEARCH_QUOTA_DURABLE',raising=False)
    def get(endpoint,*a):
        if endpoint=='/account':return {}
        raise TimeoutError('offline fixture')
    monkeypatch.setattr(collector,'_get',get)
    result=collector.run(tmp_path)
    assert result['requests_used']==1 and result['status']=='API_REQUEST_FAILED'
    assert result['daily_cohort_fixtures'][0]['reason']=='API_FAILURE'
    assert not result['daily_cohort_query_complete']


def test_outside_core_quote_is_retained_and_reported_without_forced_price(tmp_path,monkeypatch):
    clock,f=setup(tmp_path,monkeypatch,now='2026-10-14T14:03:00+00:00');baseline(tmp_path,f,monkeypatch)
    f['bookmakerOdds']['pinnacle']['markets']['201']['outcomes']['201']['players']['0']['price']=1.70
    monkeypatch.delenv('RESEARCH_QUOTA_DURABLE',raising=False)
    monkeypatch.setattr(collector,'_get',lambda endpoint,*a:{} if endpoint=='/account' else [f])
    result=collector.run(tmp_path)
    assert result['daily_cohort_query_complete']
    assert result['daily_cohort_fixtures'][0]['reason']=='OBSERVED_OUTSIDE_CORE_PRICE'
    snapshot=json.loads((tmp_path/collector.SNAPSHOT_PATH).read_text())
    assert snapshot['ah']['selected_side_price']==1.70
    assert snapshot['daily_cohort_policy']==cohort.POLICY


def test_wrong_population_receipt_does_not_delay_correct_recovery_for_an_hour(tmp_path,monkeypatch):
    from odds_scanner.research_v2_scan_due import due
    clock,f=setup(tmp_path,monkeypatch,now='2026-10-14T12:10:00+00:00');baseline(tmp_path,f,monkeypatch)
    wrong={'generated_at':'2026-10-14T11:37:00+00:00','actual_observed_at':'2026-10-14T18:37:00+07:00','scheduled_target_at':'2026-10-14T18:00:00+07:00','status':'RESEARCH_V2_OBSERVED','strict_snapshots_this_run':5,'requests_used':1}
    ledger=read_ledger(tmp_path)+[{**wrong,'provider':'oddspapi','state':'OBSERVED'}]
    assert due(clock.current,wrong,ledger_rows=ledger,snapshots=[])
    assert not due(datetime.fromisoformat('2026-10-14T11:40:00+00:00'),wrong,ledger_rows=ledger,snapshots=[])
