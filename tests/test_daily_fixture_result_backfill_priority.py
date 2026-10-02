from datetime import datetime, timezone

from odds_scanner.daily_fixture_result_backfill import select_candidates


def test_research_v2_priority_is_attempted_before_general_fixture():
    fixtures = [
        {"fixture_id":"general","flashscore_id":"g1","kickoff":"2026-09-25T10:00:00+00:00","home":"G1","away":"G2"},
        {"fixture_id":"research","flashscore_id":"r1","kickoff":"2026-09-25T11:00:00+00:00","home":"R1","away":"R2"},
    ]
    rows = select_candidates(fixtures, set(), now=datetime(2026,9,26,tzinfo=timezone.utc), priority_ids={"research"})
    assert [row["fixture_id"] for row in rows] == ["research", "general"]
    assert rows[0]["research_v2_priority"] is True


def test_existing_result_is_not_retried_even_when_priority():
    fixtures = [{"fixture_id":"research","flashscore_id":"r1","kickoff":"2026-09-25T11:00:00+00:00"}]
    rows = select_candidates(fixtures, {"research"}, now=datetime(2026,9,26,tzinfo=timezone.utc), priority_ids={"research"})
    assert rows == []


def test_runner_skips_unrelated_and_conflicted_identities(tmp_path,monkeypatch):
    import json
    import odds_scanner.daily_fixture_result_backfill as m
    def put(p,rows):
        p=tmp_path/p; p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    fixtures=[{'fixture_id':fid,'flashscore_id':fid,'kickoff':'2026-09-25T10:00:00Z'} for fid in ['general','research','blocked']]
    put(m.FIXTURES_PATH,fixtures)
    put(m.SNAPSHOTS_PATH,[{'fixture_id':'research'},{'fixture_id':'blocked'}])
    put(m.RESULTS_PATH.with_suffix('.conflicts.jsonl'),[{'fixture_id':'blocked'}])
    calls=[]
    monkeypatch.setattr(m,'fetch_exact_result',lambda ref:(calls.append(ref['fixture_id']) or (None,{})))
    r=m.run_backfill(tmp_path,now=datetime(2026,9,26,tzinfo=timezone.utc),sleep_seconds=0)
    assert calls==['research']
    assert r['unrelated_candidates_skipped']==1
    assert r['requests_attempted']==1
    put(m.SNAPSHOTS_PATH,[])
    calls.clear()
    assert m.run_backfill(tmp_path,now=datetime(2026,9,26,tzinfo=timezone.utc))['requests_attempted']==0
    assert calls==[]
    put(m.RESULTS_PATH.with_suffix('.conflicts.jsonl'),[{}])
    import pytest
    with pytest.raises(ValueError):m.run_backfill(tmp_path)
    assert calls==[]
