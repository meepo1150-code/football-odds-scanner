from datetime import datetime, timezone

import odds_scanner.oddspapi_discovery as discovery
from odds_scanner.oddspapi_discovery import fixture_query


def test_fixture_query_is_exact_next_24h_prematch_bet365_window():
    now = datetime(2026, 9, 8, 8, 30, 15, tzinfo=timezone.utc)
    q = fixture_query(now)
    assert q == {
        "sportId": 10,
        "from": "2026-09-08T08:30:15Z",
        "to": "2026-09-09T08:30:15Z",
        "statusId": 0,
        "hasOdds": "true",
        "bookmakers": "bet365",
        "language": "en",
    }


def test_fixture_query_normalizes_non_utc_aware_input_to_utc():
    now = datetime.fromisoformat("2026-09-08T15:30:00+07:00")
    q = fixture_query(now, hours=6)
    assert q["from"] == "2026-09-08T08:30:00Z"
    assert q["to"] == "2026-09-08T14:30:00Z"


def test_probe_spaces_successive_requests(monkeypatch):
    monkeypatch.setenv(discovery.ENV_KEY, "test-only")
    calls = []
    sleeps = []

    def fake_get(path, key, params=None):
        calls.append((path, params))
        if path == "/account":
            return {"subscriptions": []}
        return []

    monkeypatch.setattr(discovery, "_get", fake_get)
    payload = discovery.probe_from_env(
        request_spacing_seconds=1.1,
        sleep_fn=lambda seconds: sleeps.append(seconds),
    )

    assert [path for path, _ in calls] == ["/account", "/markets", "/fixtures"]
    assert sleeps == [1.1, 1.1]
    assert payload["status"] == "NO_ROWS"
    assert payload["requests_attempted"] == 3
    assert payload["request_spacing_seconds"] == 1.1


def test_market_diagnostics_keep_schema_metadata_but_not_prices():
    fixture = {"fixtureId": "fx1", "tournamentName": "Premier League", "startTime": "2026-09-08T18:00:00Z"}
    catalog = [{
        "marketId": 101,
        "marketName": "Full Time Result",
        "marketType": "1x2",
        "period": "fulltime",
        "handicap": 0,
        "outcomes": [{"outcomeId": 1, "outcomeName": "1"}, {"outcomeId": 2, "outcomeName": "X"}, {"outcomeId": 3, "outcomeName": "2"}],
    }]
    player = {"price": 1.91, "changedAt": "2026-09-08T10:00:00Z", "bookmakerChangedAt": None, "mainLine": True}
    odds = {"bookmakerOdds": {"bet365": {"bookmakerIsActive": True, "suspended": False, "markets": {
        "101": {"marketActive": True, "outcomes": {"1": {"players": {"0": player}}}}
    }}}}

    summary = discovery.summarize_fixture_odds(fixture, odds, catalog)
    assert summary["bookmaker_present"] is True
    assert summary["market_count"] == 1
    assert summary["catalog_match_count"] == 1
    sample = summary["market_samples"][0]
    assert sample["market_name"] == "Full Time Result"
    assert sample["outcome_labels"] == ["1", "X", "2"]
    assert sample["changed_at_present"] == 1
    assert sample["main_line_true"] == 1
    assert "price" not in sample
