from odds_scanner.multimarket import normalize_multimarket_rows
from odds_scanner.joint_backtest import build_joint_report


def sample_row():
    return {
        "Div": "E0",
        "Date": "2026-01-01",
        "HomeTeam": "Alpha",
        "AwayTeam": "Beta",
        "FTHG": "3",
        "FTAG": "1",
        "AvgH": "1.70",
        "AvgD": "4.00",
        "AvgA": "5.00",
        "AHh": "-0.75",
        "AvgAHH": "1.95",
        "AvgAHA": "1.95",
        "OU_LINE": "2.75",
        "AvgO": "1.90",
        "AvgU": "2.00",
    }


def test_multimarket_normalizes_arbitrary_total_line():
    rows = normalize_multimarket_rows([sample_row()], "2526")
    assert len(rows) == 1
    r = rows[0]
    assert r["favorite_side"] == "H"
    assert r["favorite_ah_line"] == -0.75
    assert r["ou_line"] == 2.75
    assert r["over_price"] == 1.90
    assert r["under_price"] == 2.00


def test_away_favorite_flips_home_handicap_line():
    row = sample_row()
    row.update({"AvgH": "5.00", "AvgA": "1.65", "AHh": "+0.75", "AvgAHH": "1.94", "AvgAHA": "1.96"})
    r = normalize_multimarket_rows([row], "2526")[0]
    assert r["favorite_side"] == "A"
    assert r["favorite_ah_line"] == -0.75
    assert r["favorite_ah_price"] == 1.96


def test_joint_report_uses_asian_settlement_and_train_test_split():
    normalized = normalize_multimarket_rows([sample_row()], "2223")
    normalized += normalize_multimarket_rows([sample_row()], "2526")
    report = build_joint_report(normalized, test_seasons={"2526"}, min_n=1)
    train_over = next(b for b in report["buckets"] if b["split"] == "train" and "|O2.75@" in b["pattern"])
    test_over = next(b for b in report["buckets"] if b["split"] == "test" and "|O2.75@" in b["pattern"])
    assert train_over["n"] == 1
    assert test_over["n"] == 1
    assert train_over["ah_roi"] == 0.95
    assert train_over["ou_roi"] == 0.90
    assert 0.0 < train_over["ou_market_fair_share"] < 1.0
