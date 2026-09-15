from odds_scanner.asian_settlement import settle_asian_handicap
from odds_scanner.research_v2_pattern_stats import _price_result, _price_bucket, _core, _movement


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


def test_decimal_price_buckets():
    assert _price_bucket(1.80) == '1.80-1.89'
    assert _price_bucket(1.90) == '1.90-1.99'
    assert _price_bucket(2.00) == '2.00-2.09'
    assert _price_bucket(2.10) == '2.10-2.20'
    assert _price_bucket(2.20) == '2.10-2.20'
    assert _core(1.80) and _core(2.20)
    assert not _core(1.79) and not _core(2.21)


def test_favorite_switch_is_separate_movement_state():
    first={'favorite_side':'H','ah':{'selected_side_line':-0.5,'selected_side_price':1.90}}
    last={'favorite_side':'A','ah':{'selected_side_line':-0.25,'selected_side_price':1.95}}
    assert _movement(first,last) == 'FAVORITE_SWITCH'
