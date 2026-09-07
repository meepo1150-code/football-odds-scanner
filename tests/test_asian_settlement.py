from odds_scanner.asian_settlement import Settlement, settle_asian_handicap, settle_asian_total


def test_home_minus_075():
    win_one = settle_asian_handicap(2, 1, -0.75, 1.90, "H")
    assert win_one.settlement == Settlement.HALF_WIN
    assert round(win_one.profit_units, 4) == 0.45

    win_two = settle_asian_handicap(3, 1, -0.75, 1.90, "H")
    assert win_two.settlement == Settlement.FULL_WIN
    assert round(win_two.profit_units, 4) == 0.90

    draw = settle_asian_handicap(1, 1, -0.75, 1.90, "H")
    assert draw.settlement == Settlement.FULL_LOSS
    assert draw.profit_units == -1.0


def test_over_275():
    three_goals = settle_asian_total(2, 1, 2.75, 2.00, "O")
    assert three_goals.settlement == Settlement.HALF_WIN
    assert three_goals.profit_units == 0.5

    four_goals = settle_asian_total(3, 1, 2.75, 2.00, "O")
    assert four_goals.settlement == Settlement.FULL_WIN
    assert four_goals.profit_units == 1.0

    two_goals = settle_asian_total(1, 1, 2.75, 2.00, "O")
    assert two_goals.settlement == Settlement.FULL_LOSS
    assert two_goals.profit_units == -1.0


def test_under_225():
    two_goals = settle_asian_total(1, 1, 2.25, 1.90, "U")
    assert two_goals.settlement == Settlement.HALF_WIN
    assert round(two_goals.profit_units, 4) == 0.45

    three_goals = settle_asian_total(2, 1, 2.25, 1.90, "U")
    assert three_goals.settlement == Settlement.FULL_LOSS


def test_away_plus_025_draw_is_half_win():
    result = settle_asian_handicap(1, 1, 0.25, 1.88, "A")
    assert result.settlement == Settlement.HALF_WIN
    assert round(result.profit_units, 4) == 0.44
