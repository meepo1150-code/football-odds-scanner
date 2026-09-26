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
