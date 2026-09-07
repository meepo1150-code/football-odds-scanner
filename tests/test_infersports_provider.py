from odds_scanner.infersports_provider import _two_sided


def test_two_sided_asian_handicap_prices():
    assert _two_sided({"market_type": "asian_handicap", "prices": {"home": 1.91, "away": 1.95}})
    assert not _two_sided({"market_type": "asian_handicap", "prices": {"home": 1.91}})


def test_two_sided_totals_prices():
    assert _two_sided({"market_type": "totals", "prices": {"over": 1.88, "under": 2.02}})
    assert not _two_sided({"market_type": "totals", "prices": {"over": 1.88, "under": 1.0}})


def test_three_way_requires_all_prices():
    assert _two_sided({"market_type": "1x2", "prices": {"home": 2.1, "draw": 3.2, "away": 3.4}})
    assert not _two_sided({"market_type": "1x2", "prices": {"home": 2.1, "away": 3.4}})
