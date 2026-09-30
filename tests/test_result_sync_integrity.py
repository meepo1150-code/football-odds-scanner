import json
from datetime import datetime, timezone
from odds_scanner import fotmob_result_backfill as fotmob
from odds_scanner import local_result_reuse as reuse
from odds_scanner import daily_fixture_result_sync as sync
from odds_scanner import sofascore_coverage_probe as sofa


def write(root,path,rows):
    path=root/path;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(''.join(json.dumps(r)+'\n' for r in rows))


def snapshot(fid):
    return {'fixture_id':fid,'provider':'propline','home':'Alpha','away':'Beta','league':'Test','kickoff':'2026-01-01T12:00:00+00:00','football_day':'2026-01-01'}


def test_fotmob_deduplicates_neighbor_days_and_supports_propline(tmp_path,monkeypatch):
    write(tmp_path,fotmob.SNAP,[snapshot('propline:x')])
    event={'id':123,'home':{'name':'Alpha','score':2},'away':{'name':'Beta','score':1},'status':{'utcTime':'2026-01-01T12:00:00Z','finished':True,'reason':{'short':'FT'}}}
    monkeypatch.setattr(fotmob,'_fetch',lambda day:{'leagues':[{'name':'Test','matches':[event]}]})
    report=fotmob.run(tmp_path)
    assert report['exact_results_added']==1
    assert report['ambiguous_exact_matches_rejected']==0


def test_local_reuse_requires_league_and_unique_full_identity(tmp_path):
    write(tmp_path,reuse.SNAPSHOTS,[snapshot('old'),snapshot('new'),{**snapshot('wrong'),'league':'Other'}])
    write(tmp_path,reuse.RESULTS_PATH,[{'fixture_id':'old','ft_home_goals':1,'ft_away_goals':0,'result_source':'EXACT'}])
    report=reuse.run(tmp_path)
    assert report['results_added']==1 and report['missing_after']==1


def test_sync_preserves_local_state_without_provider(tmp_path,monkeypatch):
    monkeypatch.delenv(sync.ENV_KEY,raising=False)
    today=datetime.now(timezone.utc).astimezone(sync.BANGKOK).date().isoformat()
    write(tmp_path,sync.FIXTURES_PATH,[{**snapshot('known'),'football_day':today,'flashscore_id':'keep'}])
    write(tmp_path,Path('data/normalized/europe_pinnacle_research_v2_snapshots.jsonl'),[{**snapshot('known'),'football_day':today},{**snapshot('new'),'football_day':today}])
    report=sync.run(tmp_path)
    assert report['status']=='LOCAL_FIXTURE_COVERAGE_SYNCED'
    assert report['fixture_requests_used']==0 and not report['discovery_complete']
    assert 'keep' in (tmp_path/sync.FIXTURES_PATH).read_text()


def test_sofascore_rejects_extra_time_current_score(tmp_path,monkeypatch):
    write(tmp_path,sofa.SNAP,[snapshot('pinnwire:x')])
    event={'id':1,'startTimestamp':1767268800,'homeTeam':{'name':'Alpha'},'awayTeam':{'name':'Beta'},'status':{'type':'afterextra'},'homeScore':{'current':3},'awayScore':{'current':2}}
    monkeypatch.setattr(sofa,'_fetch',lambda day:[event])
    assert sofa.backfill(tmp_path)['results_added']==0

from pathlib import Path
