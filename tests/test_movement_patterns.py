from odds_scanner.hierarchical_backtest import build_hierarchical_report


def _row(season="2223"):
    return {"season":season,"favorite_side":"H","favorite_ah_line":-0.75,"favorite_ah_price":1.92,"favorite_fair_probability":0.60,"ou_line":2.75,"over_price":1.94,"under_price":1.92,"home_goals":3,"away_goals":1,"ah_line_movement":-0.25,"ou_line_movement":0.25}


def test_movement_families_are_explicit_and_quarter_grid_preserved():
    report=build_hierarchical_report([_row()], test_seasons={"2425"}, min_n=1)
    families={b["family"] for b in report["buckets"]}
    assert {"AH_MOVE","OU_MOVE","AH_OU_MOVE"} <= families
    joint=next(b for b in report["buckets"] if b["family"]=="AH_OU_MOVE" and b["pattern_key"]["ou_side"]=="O")
    assert joint["pattern_key"]["ah_line_move"] == -0.25
    assert joint["pattern_key"]["ou_line_move"] == 0.25


def test_missing_movement_never_manufactures_a_movement_pattern():
    row=_row(); row.pop("ah_line_movement"); row.pop("ou_line_movement")
    report=build_hierarchical_report([row], test_seasons={"2425"}, min_n=1)
    assert not any("MOVE" in b["family"] for b in report["buckets"])
