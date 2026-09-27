from odds_scanner.openligadb_result_backfill import _score, _norm

def test_score_requires_finished_and_uses_latest_result():
    m={"matchIsFinished":True,"matchResults":[{"pointsTeam1":1,"pointsTeam2":0,"resultOrderID":1},{"pointsTeam1":2,"pointsTeam2":1,"resultOrderID":2}]}
    assert _score(m)==(2,1)

def test_unfinished_is_not_settled():
    assert _score({"matchIsFinished":False,"matchResults":[{"pointsTeam1":1,"pointsTeam2":0,"resultOrderID":2}]}) is None

def test_normalization_is_conservative():
    assert _norm(" Arsenal ")=="arsenal"
    assert _norm("Man Utd") != _norm("Manchester United")
