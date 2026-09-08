import json
from datetime import datetime, timezone

import pytest

import odds_scanner.oddspapi_current_provider as current_provider
from odds_scanner.execution_safety import execution_snapshot_status
from odds_scanner.oddspapi_current_provider import OddsPapiCurrentProvider
from odds_scanner.scanner import scan


def _catalog():
    return [
        {"marketId": 101, "marketName": "Full Time Result", "marketType": "1x2", "sportId": 10, "period": "fulltime", "playerProp": False, "handicap": 0, "outcomes": [{"outcomeId": 101, "outcomeName": "1"}, {"outcomeId": 102, "outcomeName": "X"}, {"outcomeId": 103, "outcomeName": "2"}]},
        {"marketId": 2001, "marketName": "Asian Handicap Full Time", "marketType": "handicap", "sportId": 10, "period": "fulltime", "playerProp": False, "handicap": -0.75, "outcomes": [{"outcomeId": 2001, "outcomeName": "Home"}, {"outcomeId": 2002, "outcomeName": "Away"}]},
        {"marketId": 3001, "marketName": "Over Under Full Time", "marketType": "totals", "sportId": 10, "period": "fulltime", "playerProp": False, "handicap": 2.75, "outcomes": [{"outcomeId": 3001, "outcomeName": "Over"}, {"outcomeId": 3002, "outcomeName": "Under"}]},
    ]


def _tournaments():
    return [
        {"categoryName": "England", "tournamentId": 17, "tournamentName": "Premier League", "tournamentSlug": "premier-league"},
        {"categoryName": "France", "tournamentId": 34, "tournamentName": "Ligue 1", "tournamentSlug": "ligue-1"},
        {"categoryName": "Germany", "tournamentId": 35, "tournamentName": "Bundesliga", "tournamentSlug": "bundesliga"},
        {"categoryName": "Italy", "tournamentId": 23, "tournamentName": "Serie A", "tournamentSlug": "serie-a"},
        {"categoryName": "Spain", "tournamentId": 8, "tournamentName": "LaLiga", "tournamentSlug": "laliga"},
    ]


def _p(price, stamp="2026-09-08T06:00:00Z"):
    return {"price": price, "active": True, "changedAt": stamp, "bookmakerChangedAt": None}


def _fixture():
    return {
        "fixtureId": "id1",
        "startTime": "2026-09-09T18:00:00Z",
        "statusId": 0,
        "statusName": "Pre-Game",
        "hasOdds": True,
        "tournamentName": "Premier League",
        "participant1Name": "Alpha",
        "participant2Name": "Beta",
        "bookmakerOdds": {
            "bet365": {
                "bookmakerIsActive": True,
                "suspended": False,
                "markets": {
                    "101": {"marketActive": True, "outcomes": {"101": {"players": {"0": _p(1.80)}}, "102": {"players": {"0": _p(3.80)}}, "103": {"players": {"0": _p(4.80)}}}},
                    "2001": {"marketActive": True, "outcomes": {"2001": {"players": {"0": _p(1.92)}}, "2002": {"players": {"0": _p(1.96)}}}},
                    "3001": {"marketActive": True, "outcomes": {"3001": {"players": {"0": _p(1.94)}}, "3002": {"players": {"0": _p(1.94)}}}},
                },
            }
        },
    }


def test_production_provider_uses_three_paced_requests_and_emits_safe_rows(monkeypatch):
    monkeypatch.setenv(current_provider.ENV_KEY, "test-only")
    calls = []
    sleeps = []

    def fake_get(path, key, params=None):
        calls.append((path, params))
        if path == "/markets":
            return _catalog()
        if path == "/tournaments":
            return _tournaments()
        if path == "/odds-by-tournaments":
            return [_fixture()]
        raise AssertionError(path)

    monkeypatch.setattr(current_provider, "_get", fake_get)
    now = datetime(2026, 9, 8, 9, 30, tzinfo=timezone.utc)
    provider = OddsPapiCurrentProvider(
        sleep_fn=lambda seconds: sleeps.append(seconds),
        now_fn=lambda: now,
    )
    rows = provider.fetch()

    assert [path for path, _ in calls] == ["/markets", "/tournaments", "/odds-by-tournaments"]
    assert sleeps == [1.1, 1.1]
    assert len(rows) == 1
    row = rows[0]
    assert row.current_feed_verified is True
    assert row.observed_at == now.isoformat()
    assert row.price_changed_at == "2026-09-08T06:00:00Z"
    assert execution_snapshot_status(row, now=now) == (True, "EXECUTION_SAFE")


def test_production_provider_requires_key_only_when_fetch_is_called(monkeypatch):
    monkeypatch.delenv(current_provider.ENV_KEY, raising=False)
    with pytest.raises(RuntimeError, match="ODDSPAPI_KEY"):
        OddsPapiCurrentProvider(request_spacing_seconds=0).fetch()


def test_empty_registry_returns_before_provider_fetch_and_spends_zero_quota(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "pattern_registry.json").write_text(json.dumps({"patterns": []}), encoding="utf-8")

    class MustNotFetch:
        provider_id = "must-not-fetch"

        def fetch(self):
            raise AssertionError("provider.fetch must not run when registry is empty")

    result = scan(tmp_path, provider=MustNotFetch())
    assert result["status"] == "NO_VALIDATED_PATTERNS"
    assert result["matches_scanned"] == 0
