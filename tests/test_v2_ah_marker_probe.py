from odds_scanner.v2_ah_marker_probe import MIN_BATCH_COOLDOWN_SECONDS, ah_marker_shape


def _player(price, marker="TRUE"):
    row = {"active": True, "price": price}
    if marker != "MISSING":
        row["mainLine"] = marker == "TRUE"
    return row


def _market(home_marker="TRUE", away_marker="TRUE"):
    return {"marketActive": True, "outcomes": {
        "201": {"players": {"0": _player(1.90, home_marker)}},
        "202": {"players": {"0": _player(1.98, away_marker)}},
    }}


def _catalog():
    return [{"marketId": 201, "sportId": 10, "period": "fulltime", "playerProp": False, "marketName": "Asian Handicap", "marketType": "spreads", "handicap": -0.5, "outcomes": [{"outcomeId": 201, "outcomeName": "1"}, {"outcomeId": 202, "outcomeName": "2"}]}]


def _fixture(home_marker="TRUE", away_marker="TRUE"):
    return {"bookmakerOdds": {"bet365": {"markets": {"201": _market(home_marker, away_marker)}}}}


def test_probe_batch_cooldown_exceeds_documented_one_second_minimum():
    assert MIN_BATCH_COOLDOWN_SECONDS > 1.0


def test_both_true_is_diagnostic_main_line():
    shape = ah_marker_shape(_fixture(), _catalog())
    assert shape["signatures"] == {"H_TRUE__A_TRUE": 1}
    assert shape["both_true_lines"] == [-0.5]


def test_home_only_true_is_visible_but_not_promoted_to_both_true():
    shape = ah_marker_shape(_fixture("TRUE", "FALSE"), _catalog())
    assert shape["signatures"] == {"H_TRUE__A_FALSE": 1}
    assert shape["both_true_lines"] == []


def test_away_only_true_is_visible_but_not_promoted_to_both_true():
    shape = ah_marker_shape(_fixture("FALSE", "TRUE"), _catalog())
    assert shape["signatures"] == {"H_FALSE__A_TRUE": 1}
    assert shape["both_true_lines"] == []


def test_missing_marker_is_distinct_from_false():
    shape = ah_marker_shape(_fixture("MISSING", "FALSE"), _catalog())
    assert shape["signatures"] == {"H_MISSING__A_FALSE": 1}
    assert shape["both_true_lines"] == []
