from odds_scanner.oddspapi_result_join import normalize_result,join_rows


def test_normalize_result_requires_finished_and_explicit_score():
    assert normalize_result({"fixtureId":"1","statusId":0,"participant1Score":2,"participant2Score":1}) is None
    assert normalize_result({"fixtureId":"1","statusId":2}) is None
    out=normalize_result({"fixtureId":"1","statusId":2,"participant1Score":2,"participant2Score":1})
    assert out["ft_home_goals"]==2 and out["ft_away_goals"]==1


def test_join_is_fixture_id_only_and_stays_promotion_disabled():
    ticks=[{"fixture_id":"1","home":"A","away":"B"},{"fixture_id":"2","home":"C","away":"D"}]
    results=[{"fixture_id":"1","ft_home_goals":3,"ft_away_goals":2,"result_source":"x"}]
    joined,report=join_rows(ticks,results)
    assert len(joined)==1
    assert joined[0]["ft_home_goals"]==3
    assert joined[0]["result_join_status"]=="JOINED"
    assert joined[0]["promotion_eligible"] is False
    assert report["joined_fixtures"]==1 and report["missing_result_fixtures"]==1
    assert report["promotion_allowed"] is False
