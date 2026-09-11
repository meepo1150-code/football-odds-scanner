from odds_scanner.v2_mainline_observer_runner import make_paced_get


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
