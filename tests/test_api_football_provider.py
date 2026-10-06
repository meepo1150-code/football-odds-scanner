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
    assert report["requests_used"] == 4
    assert report["request_remaining"] == 93
    assert report["fixture_rows_observed"] == 3
    rows = (tmp_path / "data/normalized/api_football_fixtures.jsonl").read_text().splitlines()
    assert len(rows) == 3


def test_rejects_extra_time_penalties_and_non_integer_goals():
    for status in ('AET', 'PEN', 'LIVE', 'NS'):
        row = normalize_fixture(fixture_payload(status=status), 'now')
        assert row['finished'] is False
        assert row['ft_home_goals'] is None
    for score in (True, -1, 1.5, '2'):
        assert not normalize_fixture(fixture_payload(home_goals=score), 'now')['finished']
    assert normalize_fixture(fixture_payload(home_goals=0, away_goals=0), 'now')['finished']


def test_suspension_stops_requests_and_reuses_original_retry_boundary(tmp_path):
    import json
    from odds_scanner.api_football_provider import collect_missing_pinnwire_days
    calls = []
    def suspended(path, key, params=None):
        calls.append(path)
        return {'errors': {'access': 'Your account is suspended'}, 'response': []}
    report = collect(tmp_path, key='secret', get_fn=suspended)
    assert calls == ['/fixtures']
    assert report['requests_used'] == 1
    assert report['status'] == 'ACCOUNT_SUSPENDED'
    again = collect(tmp_path, key='secret', get_fn=suspended)
    assert again['requests_used'] == 0
    assert again['retry_after'] == report['retry_after']
    targeted = collect_missing_pinnwire_days(tmp_path, key='secret', get_fn=suspended)
    assert targeted['requests_used'] == 0
    assert calls == ['/fixtures']
    # Once expired, the normal collection path resumes automatically.
    path = tmp_path / 'reports/api_football_shadow_health.json'
    again['retry_after'] = '2000-01-01T00:00:00+00:00'
    path.write_text(json.dumps(again))
    assert collect(tmp_path, key='secret', get_fn=suspended)['requests_used'] == 1


def test_join_rejects_one_team_time_nearby_and_legacy_extra_time(tmp_path):
    import json
    from odds_scanner.pinnwire_result_join import run, SNAPSHOTS_PATH, API_FIXTURES_PATH
    def put(path, row):
        dest = tmp_path / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(row)+'\n')
    snap = {'fixture_id':'pinnwire:test','provider':'pinnwire','home':'Home','away':'Away','kickoff':'2026-09-20T12:00:00Z','observed_at':'2026-09-20T10:00:00Z'}
    put(SNAPSHOTS_PATH, snap)
    fixture = normalize_fixture(fixture_payload(), 'now')
    for changes in ({'away':'Different'}, {'kickoff':'2026-09-20T12:00:30Z'}, {'status':'AET'}, {'status':'PEN'}):
        put(API_FIXTURES_PATH, {**fixture, **changes})
        assert run(tmp_path)['finished_exact_matches'] == 0
    put(API_FIXTURES_PATH, fixture)
    assert run(tmp_path)['finished_exact_matches'] == 1


def test_missing_pinnwire_backfill_is_bounded_and_skips_cached_days(tmp_path):
    import json
    from odds_scanner.api_football_provider import collect_missing_pinnwire_days, V2_SNAPSHOT_PATH, FIXTURES_PATH, _write

    snap_path = tmp_path / V2_SNAPSHOT_PATH
    snap_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"provider":"pinnwire","fixture_id":"pinnwire:a","football_day":"2026-09-20"},
        {"provider":"pinnwire","fixture_id":"pinnwire:b","football_day":"2026-09-21"},
        {"provider":"pinnwire","fixture_id":"pinnwire:c","football_day":"2026-09-22"},
        {"provider":"pinnwire","fixture_id":"pinnwire:d","football_day":"2026-09-23"},
    ]
    snap_path.write_text("".join(json.dumps(x)+"\\n" for x in rows))
    _write(tmp_path / FIXTURES_PATH, {"cached": {
        "provider_fixture_id":"cached","kickoff":"2026-09-20T12:00:00Z",
        "home":"Cached","away":"Day","finished":True
    }})
    calls=[]
    def fake_get(path,key,params=None):
        calls.append(params["date"])
        day=params["date"]
        return {"errors":[],"response":[fixture_payload(fixture_id=200+len(calls)) | {"fixture": fixture_payload()["fixture"] | {"id":200+len(calls),"date":day+"T12:00:00+07:00"}}]}
    report=collect_missing_pinnwire_days(tmp_path,key="secret",get_fn=fake_get,max_days=2)
    assert calls == ["2026-09-21","2026-09-22"]
    assert report["requests_used"] == 2
    assert report["covered_days_skipped"] == 1
    assert report["uncovered_days_remaining"] == 1


def test_missing_pinnwire_backfill_stops_after_suspension_response(tmp_path):
    import json
    from odds_scanner.api_football_provider import collect_missing_pinnwire_days, V2_SNAPSHOT_PATH
    snap_path=tmp_path / V2_SNAPSHOT_PATH
    snap_path.parent.mkdir(parents=True,exist_ok=True)
    snap_path.write_text("".join(json.dumps({"provider":"pinnwire","fixture_id":f"pinnwire:{i}","football_day":f"2026-09-{20+i:02d}"})+"\\n" for i in range(3)))
    calls=[]
    def suspended(path,key,params=None):
        calls.append(params["date"])
        return {"errors":{"access":"Your account is suspended"},"response":[]}
    report=collect_missing_pinnwire_days(tmp_path,key="secret",get_fn=suspended,max_days=3)
    assert calls == ["2026-09-20"]
    assert report["status"] == "FAILED"
    assert report["requests_used"] == 3  # planned/capped request count is reported conservatively
