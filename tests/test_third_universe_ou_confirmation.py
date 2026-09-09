from odds_scanner.asian_settlement import Settlement
from odds_scanner.third_universe_ou_confirmation import LEAGUES, _normalize_match, validate


def _row(**overrides):
    row = {
        "Date": "01/08/2025",
        "HomeTeam": "Home",
        "AwayTeam": "Away",
        "FTHG": "2",
        "FTAG": "1",
        "AvgH": "1.80",
        "AvgD": "3.60",
        "AvgA": "4.80",
        "AHh": "-0.75",
        "Avg>2.5": "1.95",
        "Avg<2.5": "1.93",
        "AvgC>2.5": "1.88",
        "AvgC<2.5": "2.02",
    }
    row.update(overrides)
    return row


def test_third_universe_is_disjoint_from_prior_ten_leagues():
    prior = {
        "Premier League", "Bundesliga", "Serie A", "LaLiga", "Ligue 1",
        "EFL Championship", "2. Bundesliga", "LaLiga 2", "Ligue 2", "Serie B",
    }
    assert set(LEAGUES).isdisjoint(prior)
    assert len(LEAGUES) == 5


def test_normalize_emits_exact_over_under_settlements_and_scanner_context():
    rows = _normalize_match(_row(), season="2526", league="Eredivisie")
    assert len(rows) == 2
    by_side = {r["ou_side"]: r for r in rows}
    assert by_side["O"]["ou_line"] == 2.5
    assert by_side["O"]["settlement"] == Settlement.FULL_WIN.value
    assert by_side["U"]["settlement"] == Settlement.FULL_LOSS.value
    assert by_side["O"]["favorite_side"] == "H"
    assert by_side["O"]["ah_line"] == -0.75
    assert by_side["O"]["promotion_eligible"] is False


def test_small_sample_cannot_promote():
    rows = _normalize_match(_row(), season="1920", league="Eredivisie")
    report, registry = validate(rows)
    assert report["promoted_patterns"] == 0
    assert registry["pattern_count"] == 0
