from odds_scanner.market_pattern import MarketPatternKey
from odds_scanner.pattern_policy import DEFAULT_POLICY


def test_market_pattern_key_binning():
    key = MarketPatternKey.from_values(
        league_scope="GLOBAL",
        favorite_side="HOME_FAVORITE",
        ah_line=-0.75,
        ah_price=1.94,
        ou_line=2.75,
        ou_side="O",
        ou_price=1.88,
        favorite_fair_probability=0.603,
    )
    assert key.ah_price_band == (1.9, 2.0)
    assert key.ou_price_band == (1.8, 1.9)
    assert key.favorite_fair_probability_band == (0.6, 0.65)
    assert "AH=-0.75" in key.label()
    assert "O2.75" in key.label()


def test_default_production_price_gate():
    assert DEFAULT_POLICY.current_price_is_tradable(1.80)
    assert DEFAULT_POLICY.current_price_is_tradable(2.00)
    assert DEFAULT_POLICY.current_price_is_tradable(2.20)
    assert not DEFAULT_POLICY.current_price_is_tradable(1.79)
    assert not DEFAULT_POLICY.current_price_is_tradable(2.21)
