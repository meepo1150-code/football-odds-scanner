from odds_scanner.oddspapi_market_catalog_refresh import summarize_catalog


def test_catalog_requires_strict_market_families():
    rows = [
        {'sportId': 10, 'period': 'fulltime', 'playerProp': False, 'marketId': 101, 'marketName': 'Full Time Result', 'marketType': '1x2'},
        {'sportId': 10, 'period': 'fulltime', 'playerProp': False, 'marketId': 1068, 'marketName': 'Asian Handicap', 'marketType': 'spreads'},
        {'sportId': 10, 'period': 'fulltime', 'playerProp': False, 'marketId': 1010, 'marketName': 'Over Under Full Time', 'marketType': 'totals'},
    ]
    s = summarize_catalog(rows)
    assert s['valid_for_strict_parser'] is True
    assert s['asian_handicap_markets'] == 1
    assert s['over_under_markets'] == 1
    assert s['one_x_two_markets'] == 1


def test_catalog_rejects_missing_ah_without_relaxing_parser():
    rows = [
        {'sportId': 10, 'period': 'fulltime', 'playerProp': False, 'marketId': 101, 'marketName': 'Full Time Result', 'marketType': '1x2'},
        {'sportId': 10, 'period': 'fulltime', 'playerProp': False, 'marketId': 1010, 'marketName': 'Over Under Full Time', 'marketType': 'totals'},
    ]
    s = summarize_catalog(rows)
    assert s['valid_for_strict_parser'] is False
    assert s['asian_handicap_markets'] == 0
