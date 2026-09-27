from odds_scanner.sofascore_coverage_probe import _norm, _utc

def test_probe_normalization_stays_exact():
    assert _norm(" Arsenal ") == "arsenal"
    assert _norm("Man Utd") != _norm("Manchester United")

def test_timestamp_is_utc():
    assert _utc(0).isoformat() == "1970-01-01T00:00:00+00:00"
