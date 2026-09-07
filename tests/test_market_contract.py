import pytest

from odds_scanner.market_contract import CurrentMarket, two_way_fair_probs


def test_two_way_fair_probs_devigs_both_sides():
    a, b, margin = two_way_fair_probs(1.90, 2.00)
    assert a + b == pytest.approx(1.0)
    assert margin > 0


def test_two_way_fair_probs_rejects_invalid_decimal_odds():
    with pytest.raises(ValueError):
        two_way_fair_probs(1.0, 2.0)


def test_current_market_contract_is_provider_neutral():
    row = CurrentMarket(
        source="synthetic_current",
        league="TEST",
        date="2026-09-07",
        kickoff="18:00",
        home="Home",
        away="Away",
        ah_home_line=-0.75,
        ah_home_odds=1.92,
        ah_away_line=0.75,
        ah_away_odds=1.96,
        ou_line=2.75,
        over_odds=1.94,
        under_odds=1.94,
        one_x_two_home=1.70,
        one_x_two_draw=3.80,
        one_x_two_away=5.20,
    )
    assert row.source == "synthetic_current"
    assert row.ou_line == 2.75
