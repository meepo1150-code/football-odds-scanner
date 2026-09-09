from odds_scanner.oddspapi_result_join import join_rows
from odds_scanner.settled_history import settle_row


def test_exact_join_then_quarter_line_settlement():
    ticks=[{"fixture_id":"f1","asian_handicap":[{"line":-0.75,"home":[{"created_at":"2026-01-01T10:00:00Z","price":1.9}],"away":[{"created_at":"2026-01-01T10:00:00Z","price":2.0}]}],"over_under":[{"line":2.75,"over":[{"created_at":"2026-01-01T10:00:00Z","price":2.0}],"under":[{"created_at":"2026-01-01T10:00:00Z","price":1.9}]}]}]
    results=[{"fixture_id":"f1","ft_home_goals":2,"ft_away_goals":1,"result_source":"explicit"}]
    joined,report=join_rows(ticks,results)
    assert report["join_rate"]==1.0 and report["promotion_allowed"] is False
    settled=settle_row(joined[0])
    assert settled["promotion_eligible"] is False
    by={(m["market"],m["selection"]):m for m in settled["settled_markets"]}
    assert by[("AH","HOME")]["opening"]["settlement"]=="HALF_WIN"
    assert by[("OU","OVER")]["opening"]["settlement"]=="HALF_WIN"
