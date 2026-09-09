from odds_scanner.settled_history import settle_row


def test_settle_nested_ah_and_ou_opening_latest():
    row={"fixture_id":"x","ft_home_goals":2,"ft_away_goals":1,
         "asian_handicap":[{"line":-0.75,"home":[{"created_at":"a","price":1.9},{"created_at":"b","price":2.0}],"away":[{"created_at":"a","price":2.0}]}],
         "over_under":[{"line":2.75,"over":[{"created_at":"a","price":2.0}],"under":[{"created_at":"a","price":1.9}]}]}
    out=settle_row(row)
    assert out["settlement_status"]=="SETTLED"
    by={(m["market"],m["selection"]):m for m in out["settled_markets"]}
    assert by[("AH","HOME")]["opening"]["settlement"]=="HALF_WIN"
    assert by[("AH","HOME")]["opening"]["profit_units"]==0.45
    assert by[("AH","HOME")]["latest"]["profit_units"]==0.5
    assert by[("OU","OVER")]["opening"]["settlement"]=="HALF_WIN"
    assert by[("OU","UNDER")]["opening"]["settlement"]=="HALF_LOSS"
