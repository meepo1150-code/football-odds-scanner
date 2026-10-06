import json
from odds_scanner.web_result_recovery import build_queue, validate_evidence
from odds_scanner.pinnwire_result_join import SNAPSHOTS_PATH

def test_web_recovery_queue_uses_zero_api_requests(tmp_path):
    p=tmp_path/SNAPSHOTS_PATH;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps({"provider":"pinnwire","fixture_id":"pinnwire:x","home":"Alpha FC","away":"Beta FC","league":"Premier League","country":"England","kickoff":"2026-09-24T13:30:00Z","football_day":"2026-09-24","observed_at":"2026-09-24T10:00:00Z","bookmaker":"pinnacle","ah":{"home_line":-0.5,"home_price":1.95,"away_line":0.5,"away_price":1.95},"promotion_eligible":False,"research_only":True,"market_type":"AH"})+"\n")
    out=build_queue(tmp_path)
    assert out["api_requests_used"] == 0
    assert out["queued"] == 1
    assert "Alpha FC" in out["rows"][0]["search_query"]

def test_web_evidence_requires_source_and_integer_ft():
    base={"fixture_id":"pinnwire:x","home":"A","away":"B","kickoff":"2026-09-24T13:30:00Z","ft_home_goals":2,"ft_away_goals":1,"source_url":"https://example.com/match","retrieved_at":"2026-10-06T00:00:00Z","status":"FT"}
    assert validate_evidence(base)[0] is True
    assert validate_evidence({**base,"source_url":""})[0] is False
    assert validate_evidence({**base,"ft_home_goals":"2"})[0] is False


def test_web_evidence_rejects_non_final_or_insecure_source():
    from odds_scanner.web_result_recovery import validate_evidence
    base={"fixture_id":"pinnwire:x","home":"A","away":"B","kickoff":"2026-09-24T12:00:00Z","ft_home_goals":1,"ft_away_goals":0,"source_url":"https://example.com/match","retrieved_at":"2026-09-25T00:00:00Z","status":"LIVE"}
    assert validate_evidence(base)[1]=="RESULT_NOT_FINAL"
    base["status"]="FT"; base["source_url"]="http://example.com/match"
    assert validate_evidence(base)[1]=="INVALID_SOURCE_URL"


# Regression: provider IDs are not match identities; corner pseudo-markets are not FT football matches.
def test_web_queue_collapses_duplicate_match_ids_and_skips_corners(tmp_path):
    import json
    from odds_scanner.web_result_recovery import build_queue
    from odds_scanner.pinnwire_result_join import SNAPSHOTS_PATH
    p=tmp_path/SNAPSHOTS_PATH; p.parent.mkdir(parents=True,exist_ok=True)
    base={"provider":"pinnwire","football_day":"2026-09-24","observed_at":"2026-09-24T10:00:00Z","league":"Cup","bookmaker":"pinnacle","ah":{"home_line":-0.5,"home_price":1.95,"away_line":0.5,"away_price":1.95},"promotion_eligible":False,"research_only":True}
    rows=[
      {**base,"fixture_id":"pinnwire:a","home":"Alpha","away":"Beta","kickoff":"2026-09-24T12:00:00Z"},
      {**base,"fixture_id":"pinnwire:b","home":"Alpha","away":"Beta","kickoff":"2026-09-24T12:00:00Z"},
      {**base,"fixture_id":"pinnwire:c","home":"China (Corners)","away":"Maldives (Corners)","kickoff":"2026-09-24T13:00:00Z"},
    ]
    p.write_text("".join(json.dumps(x)+"\n" for x in rows))
    out=build_queue(tmp_path)
    assert out["queued"]==1
    assert out["duplicate_fixture_ids_collapsed"]==1
    assert out["skipped_non_match_market"]==1
    assert out["rows"][0]["fixture_ids"]==["pinnwire:a","pinnwire:b"]
