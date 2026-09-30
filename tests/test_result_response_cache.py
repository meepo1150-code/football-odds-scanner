import json
from datetime import datetime,timedelta,timezone
from odds_scanner.result_response_cache import fetch_day, merge_cache, CACHE
from odds_scanner.fotmob_result_backfill import _events
from odds_scanner.oddspapi_result_cache import merge_normalized_results

NOW=datetime(2026,9,30,5,tzinfo=timezone.utc)


def test_old_day_reused_without_network_and_expires(tmp_path):
    calls=[]
    def get(day):calls.append(day);return {'leagues':[]}
    fetch_day(tmp_path,'2026-09-25',get,NOW)
    _,e=fetch_day(tmp_path,'2026-09-25',get,NOW+timedelta(hours=6))
    assert len(calls)==1 and e['requests']==0
    fetch_day(tmp_path,'2026-09-25',get,NOW+timedelta(hours=25))
    assert len(calls)==2


def test_recent_day_refreshes_hourly_and_outage_preserves_evidence(tmp_path):
    fetch_day(tmp_path,'2026-09-30',lambda d:{'leagues':[]},NOW)
    def fail(day):raise TimeoutError('provider unavailable')
    payload,e=fetch_day(tmp_path,'2026-09-30',fail,NOW+timedelta(hours=2))
    assert payload=={'leagues':[]}
    assert e['source']=='STALE_CACHE_AFTER_REQUEST_FAILURE' and e['requests']==1


def test_stale_writer_cannot_replace_newer_provider_response(tmp_path):
    a,b=tmp_path/'latest',tmp_path/'stage'
    fetch_day(a,'2026-09-25',lambda d:{'leagues':[],'version':2},NOW)
    fetch_day(b,'2026-09-25',lambda d:{'leagues':[],'version':1},NOW-timedelta(hours=1))
    merge_cache(b,a)
    assert json.loads((a/CACHE/'2026-09-25.json').read_text())['payload']['version']==2


def test_fotmob_finished_flag_does_not_make_extra_time_or_awarded_ft():
    def event(short='FT',**flags):
        return {'id':1,'home':{'name':'A','score':2},'away':{'name':'B','score':1},'status':{'utcTime':'2026-09-29T10:00:00Z','finished':True,'reason':{'short':short},**flags}}
    payload={'leagues':[{'name':'Test','matches':[event(),event('AET'),event('Pen'),event(awarded=True),event(cancelled=True)]}]}
    assert [r['finished'] for r in _events(payload)]==[True,False,False,False,False]


def test_existing_conflicting_cache_cannot_be_collapsed_last_write_wins(tmp_path):
    p=tmp_path/'results.jsonl'
    p.write_text('\n'.join(json.dumps({'fixture_id':'exact','ft_home_goals':h,'ft_away_goals':0}) for h in [1,2])+'\n')
    assert merge_normalized_results(p,[])==0
    assert p.read_text()==''
    conflict=json.loads(p.with_suffix('.conflicts.jsonl').read_text())
    assert conflict['existing']['ft_home_goals']==1 and conflict['incoming']['ft_home_goals']==2
