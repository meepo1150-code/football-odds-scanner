from odds_scanner.hierarchical_backtest import build_hierarchical_report
from odds_scanner.robust_stats import profit_diagnostics


def _row(i: int):
    return {
        "fixture_id": str(i),
        "season": "2526",
        "division": "Premier League",
        "date": f"2026-08-{(i % 20) + 1:02d}",
        "home": "Alpha",
        "away": "Beta",
        "home_goals": 2 if i % 2 == 0 else 0,
        "away_goals": 0 if i % 2 == 0 else 1,
        "favorite_side": "H",
        "favorite_fair_probability": 0.58,
        "favorite_ah_line": -0.75,
        "favorite_ah_price": 1.92,
        "favorite_ah_other_price": 1.94,
        # Real five_dollar_history field names:
        "ah_line_move": -0.25,
        "ou_line": 2.75,
        "over_price": 1.91,
        "under_price": 1.95,
        "ou_line_move": 0.25,
    }


def test_profit_diagnostics_are_reproducible_and_chronological():
    profits = [1.0, -1.0, -1.0, 0.5, -1.0]
    seasons = ["a", "a", "a", "b", "b"]
    a = profit_diagnostics(profits, seasons, seed_label="same", bootstrap_draws=100, sign_flip_draws=200)
    b = profit_diagnostics(profits, seasons, seed_label="same", bootstrap_draws=100, sign_flip_draws=200)
    assert a == b
    assert a["longest_losing_streak"] == 2
    assert a["max_drawdown_units"] == 2.5
    assert a["worst_season_roi"] == -1 / 3
    assert 0 <= a["sign_flip_p"] <= 1
    assert len(a["bootstrap_ci95"]) == 2


def test_real_archive_movement_names_create_families_without_ah_double_count():
    rows = [_row(i) for i in range(20)]
    report = build_hierarchical_report(rows, test_seasons={"__NONE__"}, min_n=20)
    ah_moves = [b for b in report["buckets"] if b["family"] == "AH_MOVE"]
    assert len(ah_moves) == 1
    assert ah_moves[0]["n"] == 20
    assert ah_moves[0]["pattern_key"]["ah_line_move"] == -0.25
    assert ah_moves[0]["ah_diagnostics"]["n"] == 20
    assert ah_moves[0]["ou_diagnostics"] is None

    ou_moves = [b for b in report["buckets"] if b["family"] == "OU_MOVE"]
    assert len(ou_moves) == 2  # Over and Under are distinct market observations.
    assert all(b["n"] == 20 for b in ou_moves)
    assert {b["pattern_key"]["ou_side"] for b in ou_moves} == {"O", "U"}
    assert all(b["ou_diagnostics"] is not None for b in ou_moves)


def test_empirical_diagnostics_do_not_claim_promotion_gate_change():
    report = build_hierarchical_report([_row(i) for i in range(20)], test_seasons={"__NONE__"}, min_n=20)
    assert report["empirical_diagnostics"]["promotion_gate_changed"] is False
