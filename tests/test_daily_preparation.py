import json
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from odds_scanner import daily_preparation as prep
from odds_scanner.research_v2_slots import targets, schedule_version
from odds_scanner.web_result_recovery import build_queue
from odds_scanner.result_recovery_lifecycle import SNAP,RETIRED,RESULTS


def write(root,path,rows):
    p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(''.join(json.dumps(r)+'\n' for r in rows))


def test_daily_15_utc_version_cutover_and_remaining_slots():
    assert [s.hour for s in targets('2026-10-12')]==[18,21]
    for d in range(7):
        day=date(2026,10,19)+timedelta(days=d)
        slots=targets(day)
        assert [s.hour for s in slots]==[15,18,21,0]
        assert slots[0].astimezone(timezone.utc).hour==8
    assert schedule_version('2026-10-12')=='BKK_18_SLOTS_V2'
    assert schedule_version('2026-10-13')=='BKK_28_SLOTS_V4'


def test_retired_all_provider_queue_and_missing_names_never_collapse(tmp_path):
    snap={'provider':'oddspapi','home':'A','away':'B','league':'Premier League','kickoff':'2026-09-24T12:00:00Z','observed_at':'2026-09-24T10:00:00Z'}
    raw=[{**snap,'fixture_id':'op:1'},{**snap,'provider':'pinnwire','fixture_id':'pw:1'},
         {**snap,'provider':'api_football','fixture_id':'af:1','home':None,'away':None},
         {**snap,'provider':'api_football','fixture_id':'af:2','home':None,'away':None}]
    write(tmp_path,SNAP,raw);write(tmp_path,RETIRED,[{'fixture_id':'op:1'}])
    before=(tmp_path/SNAP).read_bytes();q=build_queue(tmp_path)
    assert q['unresolved_total']==4 and q['retired_unresolved_total']==1 and q['queued']==3
    assert q['skipped_retired']==0 and q['api_requests_used']==0
    assert sum(r['status']=='MISSING_TEAM_IDENTITY' for r in q['rows'])==2
    assert (tmp_path/SNAP).read_bytes()==before


def test_preparation_batch_previous_day_and_rotation(tmp_path):
    now=datetime(2026,10,13,8,tzinfo=timezone.utc)
    write(tmp_path,SNAP,[{'fixture_id':str(i),'kickoff':f'2026-09-{i:02d}T12:00:00Z'} for i in range(1,15)])
    days,previous,total=prep.recovery_days(tmp_path,now)
    assert previous=='2026-10-12' and {'2026-10-11','2026-10-12','2026-10-13'}<=set(days)
    assert len(days)<=6 and total>3
    nextdays,_,_=prep.recovery_days(tmp_path,now+timedelta(days=1))
    assert set(days)-{'2026-10-11','2026-10-12','2026-10-13'} != set(nextdays)-{'2026-10-12','2026-10-13','2026-10-14'}


def test_source_failure_does_not_skip_other_sources_or_consume_odds(tmp_path,monkeypatch):
    from odds_scanner import web_result_evidence,local_result_reuse,fotmob_result_backfill,espn_result_backfill,daily_fixture_result_backfill
    calls=[]
    monkeypatch.setattr(web_result_evidence,'import_evidence',lambda *a:{})
    monkeypatch.setattr(local_result_reuse,'run',lambda *a:{})
    def failure(*a,**kw):
        assert kw['include_retired'];calls.append('fotmob');raise TimeoutError('source unavailable')
    def success(*a,**kw):
        assert kw['include_retired'] and kw['max_requests']==6;calls.append('espn');return {'requests_used':2}
    monkeypatch.setattr(fotmob_result_backfill,'run',failure)
    monkeypatch.setattr(espn_result_backfill,'run',success)
    monkeypatch.setattr(daily_fixture_result_backfill,'run_backfill',lambda *a,**kw:{})
    monkeypatch.setattr(prep,'review',lambda *a:None)
    r=prep.run(tmp_path,datetime(2026,10,13,8,tzinfo=timezone.utc))
    assert calls==['fotmob','espn'] and r['odds_api_requests_used']==0
    assert r['status']=='PARTIAL_SOURCE_FAILURE' and r['public_requests_used']==2


def test_preparation_jobs_independent_locks_and_zero_odds_result_credentials():
    import yaml
    workflow=yaml.safe_load(Path('.github/workflows/daily-preparation-scan.yml').read_text())
    jobs=workflow['jobs']
    assert jobs['previous-day-results']['concurrency']['group']=='research-v2-result-sync'
    assert jobs['first-odds-snapshot']['concurrency']['group']=='research-v2-collectors'
    assert 'needs' not in jobs['first-odds-snapshot']
    assert 'ODDSPAPI_KEY' not in json.dumps(jobs['previous-day-results'])
    assert any('daily_preparation' in s.get('run','') for s in jobs['previous-day-results']['steps'])
