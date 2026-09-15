from odds_scanner.asian_settlement import settle_asian_handicap
from odds_scanner.research_v2_pattern_stats import _price_result


def price_result(line, home, away, odds=1.90):
    return _price_result(settle_asian_handicap(home, away, line, odds, 'H').settlement.value)


def test_home_minus_1_5_wins_match_1_0_but_loses_price():
    assert price_result(-1.5, 1, 0) == 'LOSS'


def test_home_minus_1_0_one_goal_win_is_push():
    assert price_result(-1.0, 1, 0) == 'PUSH'


def test_home_minus_0_75_one_goal_win_is_half_win():
    assert price_result(-0.75, 1, 0) == 'HALF_WIN'


def test_home_minus_0_5_one_goal_win_is_full_price_win():
    assert price_result(-0.5, 1, 0) == 'WIN'


def test_home_minus_1_5_two_goal_win_is_full_price_win():
    assert price_result(-1.5, 2, 0) == 'WIN'
