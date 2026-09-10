from odds_scanner.v2_forward_clv import evaluate_entry_clv


def _entry(market="AH", selection="H", line=-0.5, price=1.90):
    return {
        "candidate_id": "C1",
        "fixture_id": "fx1",
        "kickoff": "2026-09-11T12:00:00Z",
        "entry_observed_at": "2026-09-10T14:00:00Z",
        "market": market,
        "selection": selection,
        "entry_line": line,
        "entry_price": price,
    }


def _snap(at, *, ah_line=-0.5, ah_home=1.90, ah_away=1.98, ou_line=2.5, over=1.95, under=1.91):
    return {
        "fixture_id": "fx1",
        "observed_at": at,
        "source_semantics": "CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED",
        "mainline_verified": True,
        "ah": {"home_line": ah_line, "home_price": ah_home, "away_line": -ah_line, "away_price": ah_away},
        "ou": {"line": ou_line, "over_price": over, "under_price": under},
    }


def test_uses_latest_same_line_snapshot_before_kickoff():
    result = evaluate_entry_clv(_entry(), [
        _snap("2026-09-10T15:00:00Z", ah_home=1.88),
        _snap("2026-09-11T10:00:00Z", ah_home=1.80),
        _snap("2026-09-11T13:00:00Z", ah_home=1.50),
    ])
    assert result["status"] == "CLV_COMPARABLE"
    assert result["latest_observed_at"] == "2026-09-11T10:00:00Z"
    assert abs(result["price_clv"] - ((1.90 / 1.80) - 1.0)) < 1e-12
    assert result["perfect_market_close_claim"] is False


def test_mainline_change_keeps_line_move_but_rejects_price_clv():
    result = evaluate_entry_clv(_entry(), [_snap("2026-09-11T10:00:00Z", ah_line=-0.75, ah_home=1.92)])
    assert result["status"] == "CLV_NOT_COMPARABLE_LINE_CHANGED"
    assert result["clv_comparable"] is False
    assert result["price_clv"] is None
    assert result["line_move"] == -0.25


def test_under_total_uses_under_price_on_same_total():
    result = evaluate_entry_clv(_entry(market="OU", selection="U", line=2.5, price=1.90), [
        _snap("2026-09-11T10:00:00Z", ou_line=2.5, under=1.80),
    ])
    assert result["status"] == "CLV_COMPARABLE"
    assert abs(result["price_clv"] - ((1.90 / 1.80) - 1.0)) < 1e-12


def test_wrong_semantics_are_not_used():
    snap = _snap("2026-09-11T10:00:00Z")
    snap["source_semantics"] = "HISTORICAL_RECONSTRUCTED"
    result = evaluate_entry_clv(_entry(), [snap])
    assert result["status"] == "NO_ADMISSIBLE_POST_ENTRY_SNAPSHOT"
    assert result["clv_comparable"] is False
