import json

from odds_scanner import v2_mainline_observer as observer
from odds_scanner.v2_mainline_observer_runner import _enrich_current_snapshots, make_paced_get


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
