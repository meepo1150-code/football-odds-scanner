from datetime import date

from odds_scanner.api_football_provider import collect, normalize_fixture


def fixture_payload(fixture_id=101, league_id=39, status="FT", home_goals=2, away_goals=1):
    return {
        "fixture": {"id": fixture_id, "date": "2026-09-20T19:00:00+07:00", "status": {"short": status}},
        "league": {"id": league_id, "name": "Premier League", "season": 2026},
        "teams": {"home": {"name": "Home"}, "away": {"name": "Away"}},
        "goals": {"home": home_goals, "away": away_goals},
    }


def test_normalizes_finished_big5_fixture():
    row = normalize_fixture(fixture_payload(), "2026-09-21T00:00:00+00:00")
    assert row["provider_fixture_id"] == "101"
    assert row["finished"] is True
    assert row["ft_home_goals"] == 2
    assert row["identity_semantics"] == "API_FOOTBALL_PROVIDER_FIXTURE_ID_EXACT"


def test_accepts_non_big5_fixture_for_global_result_matching():
    row = normalize_fixture(fixture_payload(league_id=2), "now")
    assert row is not None
    assert row["league_id"] == 2


def test_collect_keeps_provider_namespace_and_reports_quota(tmp_path):
    calls = []

    def fake_get(path, key, params=None):
        calls.append((path, params))
        if path == "/status":
            return {"response": {"requests": {"current": 7, "limit_day": 100}}}
        return {"response": [fixture_payload(fixture_id=100 + len(calls))], "errors": []}

    report = collect(tmp_path, key="secret", today=date(2026, 9, 21), get_fn=fake_get)
    assert report["status"] == "SHADOW_OK"
    assert report["requests_used"] == 3
    assert report["request_remaining"] == 93
    assert report["fixture_rows_observed"] == 2
    rows = (tmp_path / "data/normalized/api_football_fixtures.jsonl").read_text().splitlines()
    assert len(rows) == 2
