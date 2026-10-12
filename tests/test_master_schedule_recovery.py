import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from odds_scanner import master_schedule_plan as planner
from odds_scanner.research_request_budget import allocation
from odds_scanner import europe_pinnacle_discovery as collector
from test_collector_observation_contract import setup

NOW=datetime(2026,10,12,14,tzinfo=timezone.utc)
START=NOW.replace(hour=5);END=NOW.replace(hour=23)


def fixture(tid,fid,ko='2026-10-12T18:00:00Z'):
    return {'fixtureId':fid,'tournamentId':tid,'startTime':ko,'statusId':0}


def test_entire_registry_including_nordic_top_leagues_is_considered():
    targets=planner.registry()
    assert len(targets)==92
    sweden=next(t for t in targets if t['canonical_competition_id']=='SWE-0001')
    norway=next(t for t in targets if t['canonical_competition_id']=='NOR-0001')
    selected,report=planner.plan([fixture(sweden['tournament_id'],'s'),fixture(norway['tournament_id'],'n')],START,END,NOW,complete=True)
    assert {r['tournament_id'] for r in selected}=={sweden['tournament_id'],norway['tournament_id']}
    assert report['master_competitions_considered']==92 and report['scheduled_approved_fixtures']==2
    assert sum(r['reason']=='NO_MATCHES' for r in report['competition_coverage'])==90
    assert 229 not in {t['tournament_id'] for t in targets}


def test_partial_schedule_cannot_claim_no_matches_and_started_not_backfilled():
    selected,report=planner.plan([fixture(17,'past','2026-10-12T13:00:00Z'),fixture(491,'outside')],START,END,NOW)
    assert selected==[] and report['scheduled_approved_fixtures']==1
    assert next(r for r in report['competition_coverage'] if r['tournament_id']==17)['reason']=='KICKOFF_PASSED_OR_NOT_PREMATCH'
    assert 'NO_MATCHES' not in {r['reason'] for r in report['competition_coverage']}


def test_request_reservation_includes_fixture_discovery_and_failed_usage(tmp_path):
    ledger=tmp_path/'ledger';ids=list(range(30))
    chosen,report=allocation(ledger,ids,NOW,prioritized=True,overhead=1)
    assert chosen==list(range(5)) and report['schedule_requests_reserved']==1
    ledger.write_text(json.dumps({'finalized_at':NOW.isoformat(),'scheduled_target_at':'first','requests_used':4}))
    assert len(allocation(ledger,ids,NOW,prioritized=True,overhead=1,manual=True)[0])==5
    assert allocation(ledger,ids,NOW,prioritized=True,overhead=2,manual=True)[0]==[]


def test_raw_schedule_cache_is_window_specific_and_append_only(tmp_path):
    params={'from':START.isoformat(),'to':END.isoformat()}
    first=planner.retain(tmp_path,'/fixtures',params,[],NOW)
    before=(tmp_path/planner.RAW_PATH).read_bytes()
    planner.retain(tmp_path,'/odds-by-tournaments',{},[fixture(17,'x')],NOW)
    assert (tmp_path/planner.RAW_PATH).read_bytes().startswith(before)
    assert planner.cached_schedule(tmp_path,START,END,NOW)['response_id']==first['response_id']
    assert planner.cached_schedule(tmp_path,START+timedelta(days=1),END+timedelta(days=1),NOW) is None


def test_per_league_reasons_distinguish_budget_market_and_observed():
    _,r=planner.plan([fixture(t,str(t)) for t in (17,23,8)],START,END,NOW,complete=True)
    planner.finish_coverage(r,[17,23],[{'tournament_id':17,'eligibility_status':'MATCH','eligibility_reason':'OK'}])
    states={x['tournament_id']:x['reason'] for x in r['competition_coverage']}
    assert states[17]=='OBSERVED' and states[23]=='NO_MARKET_RESPONSE' and states[8]=='QUOTA_SKIPPED'


def test_full_primary_fetches_schedule_then_only_scheduled_approved_markets(tmp_path,monkeypatch):
    _,f=setup(tmp_path,monkeypatch)
    marker=tmp_path/'data/master/provider_mappings.csv';marker.parent.mkdir(parents=True);marker.write_text('enable whole registry')
    f.update(participant1Id=146,participant2Id=147)
    # Explicit namespaced mappings remain the only canonical authority.
    import odds_scanner.master_mapping as observer
    monkeypatch.setattr(observer,'load_mappings',lambda: {('oddspapi','competition','17'):'ENG-0001',('oddspapi','club','146'):'ENG-LFC',('oddspapi','club','147'):'ENG-ARS'})
    calls=[]
    def get(path,key,params=None,*args):
        calls.append((path,params))
        if path=='/account':return {}
        if path=='/fixtures':return [fixture(17,'scheduled','2026-10-12T15:00:00Z'),fixture(229,'excluded')]
        assert params['tournamentIds']=='17';return [f]
    monkeypatch.setattr(collector,'_get',get)
    r=collector.run(tmp_path)
    assert r['requests_used']==2 and r['strict_snapshots_this_run']==1
    assert r['master_competitions_considered']==92 and r['competition_reason_counts']['OBSERVED']==1
    assert [x[0] for x in calls]==['/account','/fixtures','/odds-by-tournaments']
    assert len((tmp_path/planner.RAW_PATH).read_text().splitlines())==2


def test_missing_club_mapping_never_persists_a_new_statistical_snapshot(tmp_path,monkeypatch):
    _,f=setup(tmp_path,monkeypatch)
    marker=tmp_path/'data/master/provider_mappings.csv';marker.parent.mkdir(parents=True);marker.write_text('whole registry')
    monkeypatch.setattr(collector,'_get',lambda path,*args: {} if path=='/account' else [f])
    r=collector.run(tmp_path)
    assert r['strict_snapshots_this_run']==0
    assert r['rejection_counts']['MASTER_CLUB_UNMAPPED']==1


def test_czech_reviewed_country_alias_passes_scope():
    from odds_scanner.master_scan_scope import scan_scope_reason
    assert scan_scope_reason({'tournamentId':172,'categoryName':'Czech Republic'},provider='oddspapi') is None
    assert scan_scope_reason({'tournamentId':172,'categoryName':'Norway'},provider='oddspapi')=='MASTER_COUNTRY_CONFLICT'


def test_uncovered_fixture_and_oldest_market_request_priority(tmp_path):
    _,report=planner.plan([fixture(t,str(t)) for t in (17,23,8)],START,END,NOW,complete=True)
    report['football_day']='2026-10-12'
    candidates=[r for r in report['competition_coverage'] if r['remaining_prematch_fixtures']]
    p=tmp_path/'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl';p.parent.mkdir(parents=True)
    p.write_text(json.dumps({'fixture_id':'17','football_day':'2026-10-12'})+'\n')
    planner.retain(tmp_path,'/odds-by-tournaments',{'tournamentIds':'8'},[],NOW)
    ordered=planner.prioritize(tmp_path,candidates,report,NOW)
    assert [r['tournament_id'] for r in ordered]==[23,8,17]
    assert report['fixtures_captured_today']==1 and report['scheduled_fixtures_without_snapshot']==2
    assert report['market_requests_required_all_remaining_competitions']==1
