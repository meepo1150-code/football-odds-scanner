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
