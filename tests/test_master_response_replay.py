import json
from pathlib import Path
from datetime import datetime,timezone
from odds_scanner import master_response_replay as replay
from odds_scanner.master_schedule_plan import retain,RAW_PATH


def setup(root,monkeypatch):
    p=root/replay.CATALOG_PATH;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('[]')
    now=datetime(2026,10,12,14,tzinfo=timezone.utc)
    retain(root,'/odds-by-tournaments',{'tournamentIds':'17'},[{'fixtureId':'f','tournamentId':17,'startTime':'2026-10-12T15:00:00Z'}],now)
    snap={'fixture_id':'f','provider':'oddspapi','observed_at':now.isoformat(),'canonical_competition_id':'ENG-0001','home_club_id':'ENG-LFC','away_club_id':'ENG-ARS','home':'Liverpool','away':'Arsenal','kickoff':'2026-10-12T15:00:00Z'}
    monkeypatch.setattr(replay,'extract_mainline_snapshot',lambda *a,**kw:(snap.copy(),'OK'))
    return snap


def test_offline_replay_original_time_idempotent_and_raw_prefix(tmp_path,monkeypatch):
    snap=setup(tmp_path,monkeypatch);raw=(tmp_path/RAW_PATH).read_bytes()
    old={'fixture_id':'old','observed_at':'2026-10-12T13:00:00Z'}
    p=tmp_path/replay.SNAPSHOT_PATH;original=json.dumps(old).encode()+b'\n';p.write_bytes(original)
    first=replay.run(tmp_path)
    assert first['results_added']==1 and first['http_requests']==0
    assert p.read_bytes().startswith(original) and (tmp_path/RAW_PATH).read_bytes()==raw
    added=json.loads(p.read_text().splitlines()[-1]);assert added['observed_at']==snap['observed_at']
    before=p.read_bytes();assert replay.run(tmp_path)['results_added']==0
    assert p.read_bytes()==before


def test_missing_canonical_club_quarantined_without_requery(tmp_path,monkeypatch):
    snap=setup(tmp_path,monkeypatch);snap.pop('home_club_id')
    monkeypatch.setattr(replay,'extract_mainline_snapshot',lambda *a,**kw:(snap,'OK'))
    report=replay.run(tmp_path)
    assert report['results_added']==0 and report['http_requests']==0
    assert report['quarantined'][0]['reason']=='MASTER_CLUB_UNMAPPED'
