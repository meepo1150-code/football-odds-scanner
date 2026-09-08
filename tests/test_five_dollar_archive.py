import json
from datetime import date
from pathlib import Path

import odds_scanner.five_dollar_archive as archive


def _fixture(fid=1):
    return {
        "id": fid,
        "status": "finished",
        "kickoff_utc": "2026-08-10T18:00:00+00:00",
        "league": {"name": "Premier League"},
        "teams": {"home": {"name": "Alpha"}, "away": {"name": "Beta"}},
        "goals": {"home": 2, "away": 1},
    }


def _odds():
    return {
        "success": 1,
        "data": {
            "bookmakers": [
                {
                    "slug": "bet365",
                    "odds": {
                        "1x2": {
                            "opening": {"home": 1.70, "draw": 3.8, "away": 4.6},
                            "closing": {"home": 1.65, "draw": 3.9, "away": 4.8},
                        },
                        "asian_handicap": {
                            "opening": {"line": -0.75, "home": 1.92, "away": 1.94},
                            "closing": {"line": -1.0, "home": 2.02, "away": 1.84},
                        },
                        "goal_line": {
                            "opening": {"line": 2.5, "over": 1.91, "under": 1.95},
                            "closing": {"line": 2.75, "over": 2.04, "under": 1.84},
                        },
                    },
                }
            ]
        },
    }


def test_archive_collects_derived_rows_without_raw_payload(monkeypatch, tmp_path: Path):
    def fake_get(path, key, params=None, timeout=15):
        if path == "/fixtures":
            return {"success": 1, "data": [_fixture()]}
        return _odds()

    monkeypatch.setattr(archive, "_get", fake_get)
    state = archive.collect_batch(tmp_path, key="secret", today=date(2026, 9, 8), max_days=1, pace_seconds=0)
    assert state["processed_dates"] == ["2026-06-11"]
    assert state["rows_total"] == 1
    assert state["requests_used"] == 2
    assert state["raw_payloads_stored"] is False
    assert state["pace_seconds"] == 0

    rows = (tmp_path / archive.ARCHIVE_PATH).read_text(encoding="utf-8").splitlines()
    row = json.loads(rows[0])
    assert row["ou_line"] == 2.5
    assert row["closing_ou_line"] == 2.75
    assert row["ou_line_move"] == 0.25
    assert row["ah_line_move"] == -0.25
    assert "bookmakers" not in row


def test_archive_deduplicates_fixture_ids(monkeypatch, tmp_path: Path):
    def fake_get(path, key, params=None, timeout=15):
        if path == "/fixtures":
            return {"success": 1, "data": [_fixture(7)]}
        return _odds()

    monkeypatch.setattr(archive, "_get", fake_get)
    archive.collect_batch(tmp_path, key="secret", today=date(2026, 9, 8), max_days=1, pace_seconds=0)
    state_path = tmp_path / archive.STATE_PATH
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["next_date"] = state["processed_dates"][0]
    state_path.write_text(json.dumps(state), encoding="utf-8")
    archive.collect_batch(tmp_path, key="secret", today=date(2026, 9, 8), max_days=1, pace_seconds=0)
    assert len((tmp_path / archive.ARCHIVE_PATH).read_text(encoding="utf-8").splitlines()) == 1


def test_archive_defers_whole_day_when_budget_cannot_fit(monkeypatch, tmp_path: Path):
    fixtures = [_fixture(i) for i in range(1, 5)]

    def fake_get(path, key, params=None, timeout=15):
        if path == "/fixtures":
            return {"success": 1, "data": fixtures}
        raise AssertionError("odds endpoint should not be called when whole day cannot fit")

    monkeypatch.setattr(archive, "_get", fake_get)
    state = archive.collect_batch(tmp_path, key="secret", today=date(2026, 9, 8), request_budget=4, max_days=1, pace_seconds=0)
    assert state["days_completed_this_run"] == 0
    assert state["next_date"] == "2026-06-11"
    assert state["rows_total"] == 0
    assert any("REQUEST_BUDGET_DEFERRED_DAY" in x for x in state["errors"])
