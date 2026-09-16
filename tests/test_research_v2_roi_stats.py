from odds_scanner.research_v2_roi_stats import _profit


def test_flat_stake_profit_units_follow_asian_settlement():
    assert _profit("FULL_WIN", 1.90) == 0.90
    assert _profit("HALF_WIN", 1.90) == 0.45
    assert _profit("PUSH", 1.90) == 0.0
    assert _profit("HALF_LOSS", 1.90) == -0.5
    assert _profit("FULL_LOSS", 1.90) == -1.0


def test_invalid_price_is_not_counted():
    assert _profit("FULL_WIN", 1.0) is None
    assert _profit("UNKNOWN", 1.90) is None
