from odds_scanner.five_dollar_research import build_report


def _row(i=0, ou=2.75, close_ou=3.0):
    return {
        "fixture_id": str(i),
        "season": "2526",
        "division": "Premier League",
        "date": f"2026-08-{(i % 20) + 1:02d}",
        "home": "A",
        "away": "B",
        "home_goals": 2,
        "away_goals": 1,
        "favorite_side": "H",
        "favorite_fair_probability": 0.58,
        "favorite_ah_line": -0.75,
        "favorite_ah_price": 1.92,
        "favorite_ah_other_price": 1.94,
        "closing_favorite_ah_line": -1.0,
        "closing_favorite_ah_price": 2.02,
        "closing_favorite_ah_other_price": 1.84,
        "ah_line_move": -0.25,
        "ou_line": ou,
        "over_price": 1.91,
        "under_price": 1.95,
        "closing_ou_line": close_ou,
        "closing_over_price": 2.04,
        "closing_under_price": 1.84,
        "ou_line_move": close_ou - ou,
    }


def test_empty_archive_is_insufficient_and_never_promotable():
    r = build_report([])
    assert r["status"] == "INSUFFICIENT_SAMPLE"
    assert r["promotion_allowed"] is False
    assert r["hierarchical"] is None
    assert r["coverage"]["rows"] == 0


def test_coverage_counts_real_quarter_lines_and_movements():
    r = build_report([_row(1)])
    c = r["coverage"]
    assert c["quarter_ou_open_rows"] == 1
    assert c["quarter_ou_close_rows"] == 0
    assert c["quarter_ah_open_rows"] == 1
    assert c["nonzero_ah_line_movement_rows"] == 1
    assert c["nonzero_ou_line_movement_rows"] == 1
    assert c["opening_ou_lines"] == {"2.75": 1}


def test_twenty_rows_enable_exploratory_engine_but_not_registry_promotion():
    r = build_report([_row(i) for i in range(20)])
    assert r["status"] == "EXPLORATORY_BACKTEST_READY"
    assert r["hierarchical"] is not None
    assert r["hierarchical"]["source_rows"] == 20
    assert r["promotion_allowed"] is False
    assert "pattern_registry" in r["warning"]
