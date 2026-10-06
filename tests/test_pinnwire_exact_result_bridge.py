from datetime import datetime, timezone
from odds_scanner.daily_fixture_result_backfill import _pinnwire_bridge_candidates, _result_match_key

NOW=datetime(2026,9,26,20,0,tzinfo=timezone.utc)

def fixture(fid="o1", flash="FS1", home="Alpha", away="Beta", kickoff="2026-09-26T10:00:00Z"):
    return {"fixture_id":fid,"flashscore_id":flash,"home":home,"away":away,"kickoff":kickoff}

def snap(fid="pinnwire:1", home="Alpha", away="Beta", kickoff="2026-09-26T10:00:00+00:00"):
    return {"fixture_id":fid,"home":home,"away":away,"kickoff":kickoff,"result_match_key":_result_match_key(home,away,kickoff)}

def test_unique_exact_key_bridges_to_flashscore_id():
    rows,amb=_pinnwire_bridge_candidates([fixture()],[snap()],set(),now=NOW)
    assert amb==0 and len(rows)==1
    assert rows[0]["fixture_id"]=="pinnwire:1"
    assert rows[0]["external_providers"]["flashscoreId"]=="FS1"
    assert rows[0]["bridge_source_fixture_id"]=="o1"

def test_ambiguous_exact_key_is_rejected():
    rows,amb=_pinnwire_bridge_candidates([fixture("o1","FS1"),fixture("o2","FS2")],[snap()],set(),now=NOW)
    assert rows==[]
    assert amb==1

def test_nonmatching_team_or_kickoff_is_not_bridged():
    rows,amb=_pinnwire_bridge_candidates([fixture(home="Other")],[snap()],set(),now=NOW)
    assert rows==[] and amb==0
    rows,amb=_pinnwire_bridge_candidates([fixture(kickoff="2026-09-26T10:01:00Z")],[snap()],set(),now=NOW)
    assert rows==[] and amb==0


def test_stale_identity_hash_cannot_override_changed_team():
    s=snap()
    s['away']='Different'
    rows,_=_pinnwire_bridge_candidates([fixture()],[s],set(),now=NOW)
    assert rows==[]


def test_exact_fields_can_bridge_without_redundant_hash():
    s=snap(); s.pop('result_match_key')
    rows,_=_pinnwire_bridge_candidates([fixture()],[s],set(),now=NOW)
    assert len(rows)==1


def test_join_settles_prevalidated_web_evidence_by_exact_pinnwire_id(tmp_path):
    import json
    from odds_scanner.pinnwire_result_join import run, SNAPSHOTS_PATH, SETTLEMENTS_PATH
    from odds_scanner.oddspapi_result_cache import RESULTS_PATH
    snap={"provider":"pinnwire","fixture_id":"pinnwire:web1","home":"Alpha","away":"Beta","kickoff":"2026-09-24T12:00:00Z","football_day":"2026-09-24","observed_at":"2026-09-24T10:00:00Z","favorite_side":"home","ah":{"selected_side_line":-0.5,"selected_side_price":1.95}}
    p=tmp_path/SNAPSHOTS_PATH;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(snap)+"\n")
    r=tmp_path/RESULTS_PATH;r.parent.mkdir(parents=True,exist_ok=True);r.write_text(json.dumps({"fixture_id":"pinnwire:web1","ft_home_goals":2,"ft_away_goals":0,"result_source":"WEB_EVIDENCE_TIER_A_OFFICIAL","source_urls":["https://club.example/m"]})+"\n")
    report=run(tmp_path)
    assert report["web_result_matches"]==1
    rows=[json.loads(x) for x in (tmp_path/SETTLEMENTS_PATH).read_text().splitlines()]
    assert rows[0]["ft_home_goals"]==2 and rows[0]["result_source"].startswith("WEB_EVIDENCE")
