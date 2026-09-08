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
