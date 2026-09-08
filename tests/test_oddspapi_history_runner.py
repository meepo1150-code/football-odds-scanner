from datetime import datetime, timezone

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

    monkeypatch.setattr(runner, "_get", fake_get)
    rows = runner.discover_finished_big5_window(
        "test",
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 10, tzinfo=timezone.utc),
    )

    # Finished Big-5 fixtures are retained regardless of the current fixture-list
    # hasOdds flag; the historical endpoint decides whether archived prices exist.
    assert [r["fixtureId"] for r in rows] == ["ok", "noodds"]
    path, params = calls[0]
    assert path == "/fixtures"
    assert params["sportId"] == 10
    assert params["limit"] == 300
    assert "statusId" not in params
    assert "hasOdds" not in params
    assert "bookmakers" not in params
