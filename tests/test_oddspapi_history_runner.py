from datetime import datetime, timezone
from io import BytesIO
from urllib.error import HTTPError

import pytest

import odds_scanner.oddspapi_history_runner as runner


def test_discover_finished_big5_uses_minimal_fixture_contract(monkeypatch):
    calls = []

    def fake_get(path, key, params=None):
        calls.append((path, params))
        return [
            {"fixtureId": "ok", "statusId": 2, "hasOdds": True, "tournamentId": 17, "startTime": "2026-01-03T15:00:00Z", "participant1Name": "A", "participant2Name": "B"},
            {"fixtureId": "live", "statusId": 1, "hasOdds": True, "tournamentId": 17},
            {"fixtureId": "noodds", "statusId": 2, "hasOdds": False, "tournamentId": 17, "startTime": "2026-01-04T15:00:00Z", "participant1Name": "C", "participant2Name": "D"},
            {"fixtureId": "other", "statusId": 2, "hasOdds": True, "tournamentId": 999},
        ]

    monkeypatch.setattr(runner, "provider_get", fake_get)
    rows = runner.discover_finished_big5_window(
        "test",
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 10, tzinfo=timezone.utc),
    )

    assert [r["fixtureId"] for r in rows] == ["ok", "noodds"]
    path, params = calls[0]
    assert path == "/fixtures"
    assert params["sportId"] == 10
    assert params["limit"] == 300
    assert "statusId" not in params
    assert "hasOdds" not in params
    assert "bookmakers" not in params


def _http_error(code):
    return HTTPError("https://api.oddspapi.io/v4/test", code, "test", {}, BytesIO(b""))


def test_historical_404_becomes_empty_history(monkeypatch):
    def fake_get(path, key, params=None):
        raise _http_error(404)

    monkeypatch.setattr(runner, "provider_get", fake_get)
    assert runner._history_aware_get("/historical-odds", "test", {"fixtureId": "x"}) == {"bookmakers": {}}


def test_non404_and_nonhistorical_errors_still_propagate(monkeypatch):
    def fake_get(path, key, params=None):
        raise _http_error(429)

    monkeypatch.setattr(runner, "provider_get", fake_get)
    with pytest.raises(HTTPError) as exc:
        runner._history_aware_get("/historical-odds", "test", {"fixtureId": "x"})
    assert exc.value.code == 429

    def fake_404(path, key, params=None):
        raise _http_error(404)

    monkeypatch.setattr(runner, "provider_get", fake_404)
    with pytest.raises(HTTPError):
        runner._history_aware_get("/fixtures", "test", {})
