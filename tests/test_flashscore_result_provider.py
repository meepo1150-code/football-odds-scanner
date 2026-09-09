from odds_scanner.flashscore_result_provider import parse_exact_result


def _ref():
    return {
        "fixture_id": "id1000000861624378",
        "home": "Deportivo Alaves",
        "away": "Getafe CF",
        "external_providers": {"flashscoreId": "CIrbR4BN"},
    }


def test_parse_exact_result_requires_exact_mid_and_score_suffix():
    html = b'''<html><head>
    <title>Alaves v Getafe 08/02/2026 | Football - Flashscore</title>
    <meta property="og:title" content="Alaves - Getafe 0-2">
    <meta property="og:description" content="SPAIN: LaLiga - Round 23">
    </head></html>'''
    row = parse_exact_result(
        _ref(),
        final_url="https://www.flashscore.com/match/football/alaves/getafe/?mid=CIrbR4BN",
        body=html,
    )
    assert row is not None
    assert row["fixture_id"] == "id1000000861624378"
    assert row["ft_home_goals"] == 0
    assert row["ft_away_goals"] == 2
    assert row["result_source"] == "FLASHSCORE_EXACT_EXTERNAL_ID_OG_TITLE_FINAL_SCORE"
    assert row["promotion_eligible"] is False


def test_parse_exact_result_rejects_wrong_exact_event_id():
    html = b'<meta property="og:title" content="Alaves - Getafe 0-2">'
    assert parse_exact_result(
        _ref(),
        final_url="https://www.flashscore.com/match/other/?mid=WRONG",
        body=html,
    ) is None


def test_parse_exact_result_rejects_page_without_final_score_metadata():
    html = b'<meta property="og:title" content="Alaves - Getafe">'
    assert parse_exact_result(
        _ref(),
        final_url="https://www.flashscore.com/match/football/x/?mid=CIrbR4BN",
        body=html,
    ) is None
