import json

from odds_scanner import v2_mainline_observer as observer
from odds_scanner.v2_mainline_observer_runner import _enrich_current_snapshots, make_paced_get, summarize_ah_markers


def test_repeated_odds_batch_waits_after_previous_call_completes():
    now = [100.0]
    sleeps = []
    calls = []

    def clock():
        return now[0]

    def sleeper(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    def delegate(path, key, params=None, timeout=20):
        calls.append(path)
        now[0] += 0.20
        return {"ok": True}

    paced = make_paced_get(delegate, clock=clock, sleeper=sleeper, minimum_cooldown_seconds=1.25)
    paced("/odds-by-tournaments", "k", {})
    paced("/odds-by-tournaments", "k", {})

    assert calls == ["/odds-by-tournaments", "/odds-by-tournaments"]
    assert len(sleeps) == 1
    assert abs(sleeps[0] - 1.25) < 1e-9


def test_different_endpoint_is_not_delayed():
    now = [10.0]
    sleeps = []

    def clock():
        return now[0]

    def sleeper(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    def delegate(path, key, params=None, timeout=20):
        return []

    paced = make_paced_get(delegate, clock=clock, sleeper=sleeper)
    paced("/tournaments", "k", {})
    paced("/account", "k", {})
    assert sleeps == []


def test_no_automatic_retry_is_introduced():
    calls = []

    def delegate(path, key, params=None, timeout=20):
        calls.append(path)
        raise RuntimeError("rate limited")

    paced = make_paced_get(delegate, clock=lambda: 1.0, sleeper=lambda _: None)
    try:
        paced("/odds-by-tournaments", "k", {})
        assert False, "expected delegate failure"
    except RuntimeError:
        pass
    assert calls == ["/odds-by-tournaments"]


def test_exact_external_ids_are_captured_from_same_odds_response_without_extra_call():
    calls = []
    refs = {}

    def delegate(path, key, params=None, timeout=20):
        calls.append(path)
        return [{
            "fixtureId": "fx1",
            "participant1Name": "Home",
            "participant2Name": "Away",
            "startTime": "2026-09-12T12:00:00Z",
            "externalProviders": {"flashscoreId": "abc123", "sofascoreId": 456, "unknownId": "drop-me"},
        }]

    paced = make_paced_get(delegate, clock=lambda: 1.0, sleeper=lambda _: None, exact_refs=refs)
    paced("/odds-by-tournaments", "k", {})
    assert calls == ["/odds-by-tournaments"]
    assert refs["fx1"]["external_providers"] == {"sofascoreId": 456, "flashscoreId": "abc123"}


def test_same_response_fixtures_can_be_captured_for_diagnostics_without_extra_call():
    calls = []
    captured = []

    def delegate(path, key, params=None, timeout=20):
        calls.append(path)
        return [{"fixtureId": "fx1"}, {"fixtureId": "fx2"}]

    paced = make_paced_get(delegate, clock=lambda: 1.0, sleeper=lambda _: None, captured_fixtures=captured)
    paced("/odds-by-tournaments", "k", {})
    assert calls == ["/odds-by-tournaments"]
    assert [x["fixtureId"] for x in captured] == ["fx1", "fx2"]


def test_only_current_run_snapshots_receive_exact_external_ids(tmp_path, monkeypatch):
    path = tmp_path / "snapshots.jsonl"
    rows = [
        {"fixture_id": "fx1", "observed_at": "2026-09-11T01:00:00+00:00"},
        {"fixture_id": "fx1", "observed_at": "2026-09-11T13:00:00+00:00"},
    ]
    path.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
    monkeypatch.setattr(observer, "SNAPSHOTS_PATH", path)
    changed = _enrich_current_snapshots({"fx1": {"external_providers": {"flashscoreId": "abc"}}}, "2026-09-11T13:00:00+00:00")
    stored = [json.loads(x) for x in path.read_text().splitlines()]
    assert changed == 1
    assert "external_providers" not in stored[0]
    assert stored[1]["external_providers"] == {"flashscoreId": "abc"}


def test_ah_marker_summary_exposes_one_side_true_without_promoting_line():
    catalog = [{
        "marketId": 201,
        "sportId": 10,
        "period": "fulltime",
        "playerProp": False,
        "marketName": "Asian Handicap",
        "marketType": "spreads",
        "handicap": -0.5,
        "outcomes": [
            {"outcomeId": 201, "outcomeName": "1"},
            {"outcomeId": 202, "outcomeName": "2"},
        ],
    }]
    fixture = {
        "fixtureId": "fx-marker",
        "tournamentId": 17,
        "startTime": "2026-09-12T12:00:00Z",
        "bookmakerOdds": {"bet365": {"markets": {
            "201": {"marketActive": True, "outcomes": {
                "201": {"players": {"0": {"active": True, "price": 1.90, "mainLine": True}}},
                "202": {"players": {"0": {"active": True, "price": 1.98, "mainLine": False}}},
            }}
        }}},
    }
    out = summarize_ah_markers([fixture], catalog)
    assert out["ah_market_marker_signatures"] == {"H_TRUE__A_FALSE": 1}
    assert out["ah_fixture_shape_counts"] == {"AH_MARKETS_1__BOTH_TRUE_0": 1}
    assert out["ah_marker_samples"][0]["both_true_lines"] == []
