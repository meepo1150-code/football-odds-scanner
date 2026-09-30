from odds_scanner.openligadb_result_backfill import _score, _norm

def test_unlabelled_result_order_is_not_normal_time_proof():
    m={"matchIsFinished":True,"matchResults":[{"pointsTeam1":1,"pointsTeam2":0,"resultOrderID":1},{"pointsTeam1":2,"pointsTeam2":1,"resultOrderID":2}]}
    assert _score(m) is None

def test_unfinished_is_not_settled():
    assert _score({"matchIsFinished":False,"matchResults":[{"pointsTeam1":1,"pointsTeam2":0,"resultOrderID":2}]}) is None

def test_normalization_is_conservative():
    assert _norm(" Arsenal ")=="arsenal"
    assert _norm("Man Utd") != _norm("Manchester United")


def test_explicit_90_minutes_beats_later_extra_time():
    rows=[{'resultTypeKind':'After90Minutes','pointsTeam1':1,'pointsTeam2':1,'resultOrderID':2},{'resultTypeKind':'AfterExtraTime','pointsTeam1':2,'pointsTeam2':1,'resultOrderID':3}]
    assert _score({'matchIsFinished':True,'matchResults':rows})==(1,1)
    rows.append({'resultTypeKind':'After90Minutes','pointsTeam1':0,'pointsTeam2':0})
    assert _score({'matchIsFinished':True,'matchResults':rows}) is None
