from odds_scanner.execution_safety import execution_snapshot_status
from odds_scanner.five_dollar_provider import parse_fixture_odds


def _fixture():
    return {
        "id": 42,
        "league": {"id": 1, "name": "Premier League"},
        "teams": {"home": {"name": "Alpha"}, "away": {"name": "Beta"}},
        "kickoff_utc": "2026-09-07T18:30:00+00:00",
        "status": "scheduled",
    }


def _odds():
    return {
        "success": 1,
        "data": {
            "fixture_id": 42,
            "bookmakers": [{
                "name": "Bet 365",
                "slug": "bet365",
                "odds": {
                    "1x2": {"closing": {"home": 1.70, "draw": 3.80, "away": 5.20}},
                    "asian_handicap": {"closing": {"line": -0.75, "home": 1.92, "away": 1.96}},
                    "goal_line": {"closing": {"line": 2.75, "over": 1.94, "under": 1.94}},
                },
            }],
        },
    }


def test_parser_preserves_quarter_lines_and_two_sided_prices():
    row = parse_fixture_odds(_fixture(), _odds())
    assert row.ah_home_line == -0.75
    assert row.ah_away_line == 0.75
    assert row.ou_line == 2.75
    assert row.ah_home_odds == 1.92
    assert row.ah_away_odds == 1.96
    assert row.over_odds == row.under_odds == 1.94
    assert row.status == "scheduled"
    assert row.tradable is True


def test_summary_row_does_not_fake_quote_freshness():
    row = parse_fixture_odds(_fixture(), _odds())
    assert row.as_of is None
    assert row.stale is None
    safe, reason = execution_snapshot_status(row)
    assert safe is False
    assert reason == "STALE_OR_UNVERIFIED_QUOTE"


def test_missing_bookmaker_fails_closed():
    payload = _odds()
    payload["data"]["bookmakers"] = []
    try:
        parse_fixture_odds(_fixture(), payload)
    except ValueError as exc:
        assert "bookmaker" in str(exc)
    else:
        raise AssertionError("expected missing bookmaker to fail")
