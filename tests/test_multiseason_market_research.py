from odds_scanner.asian_settlement import Settlement
from odds_scanner.multiseason_market_research import _bh, normalize_row, validate


def _base_row(**overrides):
    row = {
        "Date": "01/01/2026",
        "HomeTeam": "Home",
        "AwayTeam": "Away",
        "FTHG": "2",
        "FTAG": "1",
        "AvgH": "1.80",
        "AvgD": "3.60",
        "AvgA": "4.80",
        "AHh": "-0.75",
        "AvgAHH": "1.95",
        "AvgAHA": "1.93",
        "AHCh": "-1.00",
        "AvgCAHH": "2.02",
        "AvgCAHA": "1.86",
        "AvgCH": "1.75",
        "AvgCD": "3.70",
        "AvgCA": "5.00",
    }
    row.update(overrides)
    return row


def test_normalize_home_favorite_uses_selected_side_line_and_actual_quarter_settlement():
    out = normalize_row(_base_row(), season="2526", league="Premier League")
    assert out is not None
    assert out["favorite_side"] == "H"
    assert out["ah_line"] == -0.75
    assert out["settlement"] == Settlement.FULL_WIN.value
    assert out["source_semantics"] == "FOOTBALL_DATA_FIRST_COLLECTED_AFTER_MARKET_OPENING_NOT_TRUE_OPEN"
    assert out["promotion_eligible"] is False


def test_normalize_away_favorite_flips_home_perspective_ah_line():
    row = _base_row(
        FTHG="0", FTAG="1",
        AvgH="5.00", AvgD="3.80", AvgA="1.70",
        AHh="0.75", AvgAHH="1.91", AvgAHA="1.97",
        AHCh="1.00", AvgCAHH="1.84", AvgCAHA="2.04",
        AvgCH="5.20", AvgCD="3.90", AvgCA="1.66",
    )
    out = normalize_row(row, season="2526", league="Serie A")
    assert out is not None
    assert out["favorite_side"] == "A"
    assert out["ah_line"] == -0.75
    assert out["closing_ah_line"] == -1.0
    assert out["settlement"] == Settlement.FULL_WIN.value


def test_normalize_rejects_non_quarter_lines_instead_of_rounding():
    assert normalize_row(_base_row(AHh="-0.60"), season="2526", league="LaLiga") is None


def test_bh_is_monotone_and_bounded():
    q = _bh([("a", 0.01), ("b", 0.03), ("c", 0.20)])
    assert 0 <= q["a"] <= q["b"] <= q["c"] <= 1


def test_small_sample_cannot_promote_even_when_profitable():
    row = normalize_row(_base_row(), season="1920", league="Premier League")
    assert row is not None
    report, registry = validate([row])
    assert report["promoted_patterns"] == 0
    assert registry["pattern_count"] == 0
