from odds_scanner.oddspapi_catalog_gap_report import classify_unknown_ids


def test_classifies_unknown_market_ids_without_fallback():
    catalog = [
        {'marketId': 1, 'sportId': 10, 'period': '1sthalf', 'playerProp': False, 'marketName': 'Asian Handicap'},
        {'marketId': 2, 'sportId': 10, 'period': 'fulltime', 'playerProp': True, 'marketName': 'Player Shots'},
        {'marketId': 3, 'sportId': 11, 'period': 'fulltime', 'playerProp': False, 'marketName': 'Spread'},
        {'marketId': 4, 'sportId': 10, 'period': 'fulltime', 'playerProp': False, 'marketName': 'Unknown Type', 'marketType': 'mystery'},
    ]
    out = classify_unknown_ids(catalog, {'1': 5, '2': 4, '3': 3, '4': 2, '999': 1})
    assert out['classification_counts'] == {
        'ABSENT_FROM_RAW_CATALOG': 1,
        'FILTERED_NON_FULLTIME': 1,
        'FILTERED_OTHER_SPORT': 1,
        'FILTERED_PLAYER_PROP': 1,
        'FULLTIME_SOCCER_NON_PLAYER_BUT_NOT_RECOGNIZED': 1,
    }
    assert out['fixture_weighted_occurrences']['FILTERED_NON_FULLTIME'] == 5
    assert out['fixture_weighted_occurrences']['ABSENT_FROM_RAW_CATALOG'] == 1
