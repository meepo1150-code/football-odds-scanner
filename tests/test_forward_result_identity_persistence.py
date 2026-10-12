import json
from datetime import datetime,timezone,timedelta
from pathlib import Path
from test_v2_mainline_observer import _catalog,_fixture
from odds_scanner.v2_mainline_observer import extract_mainline_snapshot
from odds_scanner import daily_fixture_result_sync as sync
from odds_scanner.daily_fixture_result_backfill import select_candidates


def test_exact_external_result_id_survives_quote_to_local_fixture_candidate(tmp_path,monkeypatch):
    now=datetime.now(timezone.utc);f=_fixture();f['startTime']=(now+timedelta(hours=1)).isoformat()
    f['externalProviders']={'flashscoreId':'AbCd1234'}
    snap,reason=extract_mainline_snapshot(f,_catalog(),observed_at=now,tournament_meta={'country':'England','tournament_name':'Premier League'})
    assert reason=='OK' and snap['flashscore_id']=='AbCd1234'
    snap['football_day']=now.astimezone(sync.BANGKOK).date().isoformat()
    path=tmp_path/'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl';path.parent.mkdir(parents=True)
    path.write_text(json.dumps(snap)+'\n')
    monkeypatch.setenv('FIXTURE_SYNC_MODE','LOCAL_ONLY')
    def forbidden(*a,**kw):raise AssertionError('local metadata sync requested provider')
    monkeypatch.setattr(sync,'_get',forbidden);sync.run(tmp_path)
    refs=[json.loads(l) for l in (tmp_path/sync.FIXTURES_PATH).read_text().splitlines()]
    assert refs[0]['flashscore_id']=='AbCd1234'
    candidates=select_candidates(refs,set(),now=now+timedelta(hours=5),priority_ids={snap['fixture_id']})
    assert candidates[0]['external_providers']=={'flashscoreId':'AbCd1234'}


def test_conflicting_external_ids_are_not_guessed():
    f=_fixture();f['flashscoreId']='AbCd1234';f['externalProviders']={'flashscoreId':'ZzYy9876'}
    snap,_=extract_mainline_snapshot(f,_catalog(),observed_at=datetime(2026,9,10,tzinfo=timezone.utc))
    assert snap['flashscore_identity_conflict'] is True and 'flashscore_id' not in snap


def test_exact_id_ft_poll_has_no_six_hour_gate_and_keeps_request_cap():
    text=Path('.github/workflows/research-v2-free-result-backfill.yml').read_text()
    step=text.split('      - name: Backfill matured Research V2 results without OddsPapi requests',1)[1].split('      - name:',1)[0]
    assert 'if:' not in step and 'max_requests=20' in step
