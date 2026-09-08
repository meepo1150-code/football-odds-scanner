from datetime import datetime, timezone

from odds_scanner.execution_safety import execution_snapshot_status
from odds_scanner import five_dollar_provider as provider_mod
from odds_scanner.five_dollar_provider import FiveDollarCurrentProvider, parse_fixture_odds


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
    row = parse_fixture_odds(_fixture(), _odds(), observed_at="2026-09-08T06:00:00+00:00")
    assert row.as_of is None
    assert row.stale is None
    safe, reason = execution_snapshot_status(row)
    assert safe is False
    assert reason == "STALE_OR_UNVERIFIED_QUOTE"


def test_current_provider_requests_explicit_next_24h_window(monkeypatch):
    calls = []

    def fake_get(path, key, params=None, timeout=15):
        calls.append((path, params))
        if path == "/fixtures":
            return {"success": 1, "data": [_fixture()]}
        return _odds()

    monkeypatch.setattr(provider_mod, "_get", fake_get)
    fixed = datetime(2026, 9, 8, 6, 0, tzinfo=timezone.utc)
    rows = FiveDollarCurrentProvider(
        "key",
        limit=3,
        pace_seconds=0,
        now_fn=lambda: fixed,
    ).fetch()
    assert len(rows) == 1
    params = calls[0][1]
    assert params["status"] == "scheduled"
    assert params["start_time"] == int(fixed.timestamp())
    assert params["end_time"] - params["start_time"] == 24 * 60 * 60
    assert rows[0].as_of is None
    assert rows[0].stale is None


def test_missing_bookmaker_fails_closed():
    payload = _odds()
    payload["data"]["bookmakers"] = []
    try:
        parse_fixture_odds(_fixture(), payload)
    except ValueError as exc:
        assert "bookmaker" in str(exc)
    else:
        raise AssertionError("expected missing bookmaker to fail")
