import json
from datetime import datetime, timedelta, timezone

import odds_scanner.oddspapi_history_archive as archive


def _catalog():
    return [
        {"marketId": 101, "marketName": "Full Time Result", "marketType": "1x2", "sportId": 10, "period": "fulltime", "playerProp": False, "handicap": 0, "outcomes": [{"outcomeId": 101, "outcomeName": "1"}, {"outcomeId": 102, "outcomeName": "X"}, {"outcomeId": 103, "outcomeName": "2"}]},
        {"marketId": 2001, "marketName": "Asian Handicap Full Time", "marketType": "handicap", "sportId": 10, "period": "fulltime", "playerProp": False, "handicap": -0.75, "outcomes": [{"outcomeId": 2001, "outcomeName": "Home"}, {"outcomeId": 2002, "outcomeName": "Away"}]},
        {"marketId": 3001, "marketName": "Over Under Full Time", "marketType": "totals", "sportId": 10, "period": "fulltime", "playerProp": False, "handicap": 2.75, "outcomes": [{"outcomeId": 3001, "outcomeName": "Over"}, {"outcomeId": 3002, "outcomeName": "Under"}]},
    ]


def _ticks(a, b):
    return [
        {"createdAt": "2026-03-01T10:00:00Z", "price": a, "active": True},
        {"createdAt": "2026-03-01T12:00:00Z", "price": b, "active": True},
    ]


def _history():
    return {"bookmakers": {"bet365": {"markets": {
        "101": {"outcomes": {"101": {"players": {"0": _ticks(1.90, 1.85)}}, "102": {"players": {"0": _ticks(3.50, 3.60)}}, "103": {"players": {"0": _ticks(4.10, 4.30)}}}},
        "2001": {"outcomes": {"2001": {"players": {"0": _ticks(1.95, 1.88)}}, "2002": {"players": {"0": _ticks(1.91, 1.98)}}}},
        "3001": {"outcomes": {"3001": {"players": {"0": _ticks(1.93, 1.87)}}, "3002": {"players": {"0": _ticks(1.93, 1.99)}}}},
    }}}}


def _fixture(fid="f1"):
    return {"fixtureId": fid, "tournamentId": 17, "tournamentName": "Premier League", "startTime": "2026-03-01T15:00:00Z", "participant1Name": "Alpha", "participant2Name": "Beta"}


def test_normalize_full_tick_history_preserves_quarter_lines_and_times():
    row = archive.normalize_historical_fixture(_fixture(), _history(), _catalog())
    assert row is not None
    assert row["promotion_eligible"] is False
    assert row["result_join_status"] == "NOT_JOINED"
    assert row["asian_handicap"][0]["line"] == -0.75
    assert row["over_under"][0]["line"] == 2.75
    assert row["asian_handicap"][0]["home"][0]["created_at"] == "2026-03-01T10:00:00Z"
    assert row["asian_handicap"][0]["home"][1]["price"] == 1.88
    assert row["one_x_two"]["home"][1]["price"] == 1.85


def test_non_quarter_line_is_not_rounded_into_archive():
    catalog = _catalog()
    catalog[1]["handicap"] = -0.6
    row = archive.normalize_historical_fixture(_fixture(), _history(), catalog)
    assert row is not None
    assert row["asian_handicap"] == []
    assert row["over_under"][0]["line"] == 2.75


def test_discovery_refresh_is_weekly_or_queue_empty():
    now = datetime(2026, 9, 8, tzinfo=timezone.utc)
    state = {"last_discovery_at": (now - timedelta(days=2)).isoformat(), "fixture_queue": [{"fixtureId": "f1"}]}
    assert archive.discovery_due(state, now) is False
    state["last_discovery_at"] = (now - timedelta(days=8)).isoformat()
    assert archive.discovery_due(state, now) is True
    state = {"last_discovery_at": now.isoformat(), "fixture_queue": []}
    assert archive.discovery_due(state, now) is True


def test_missing_key_writes_fail_closed_state(monkeypatch, tmp_path):
    monkeypatch.delenv(archive.ENV_KEY, raising=False)
    now = datetime(2026, 9, 8, 9, 0, tzinfo=timezone.utc)
    result = archive.run_archive(tmp_path, now_fn=lambda: now, sleep_fn=lambda _: None)
    assert result["status"] == "API_KEY_NOT_CONFIGURED"
    assert result["promotion_eligible"] is False
    saved = json.loads((tmp_path / archive.STATE_PATH).read_text(encoding="utf-8"))
    assert saved["result_join_status"] == "NOT_JOINED"


def test_cached_queue_uses_free_history_without_billable_discovery(monkeypatch, tmp_path):
    monkeypatch.setenv(archive.ENV_KEY, "test-only")
    now = datetime(2026, 9, 8, 9, 0, tzinfo=timezone.utc)
    state_path = tmp_path / archive.STATE_PATH
    state_path.parent.mkdir(parents=True)
    state_path.write_text(json.dumps({
        "last_discovery_at": now.isoformat(),
        "fixture_queue": [_fixture("f1")],
    }), encoding="utf-8")
    catalog_path = tmp_path / archive.CATALOG_PATH
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(json.dumps(_catalog()), encoding="utf-8")
    calls = []

    def fake_get(path, key, params=None):
        calls.append(path)
        if path == "/historical-odds":
            return _history()
        raise AssertionError(path)

    monkeypatch.setattr(archive, "_get", fake_get)
    result = archive.run_archive(tmp_path, max_fixtures=1, now_fn=lambda: now, sleep_fn=lambda _: None)
    assert calls == ["/historical-odds"]
    assert result["billable_requests_this_run"] == 0
    assert result["free_history_requests_this_run"] == 1
    assert result["rows_added_this_run"] == 1
    assert result["archive_rows"] == 1
    assert result["promotion_eligible"] is False
