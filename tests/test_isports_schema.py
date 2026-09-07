from odds_scanner.isports_schema import (
    hk_to_decimal,
    is_prematch_execution_eligible,
    normalize_ah,
    normalize_market_records,
    normalize_ou,
    quarter_line,
)


def test_hk_to_decimal_and_quarter_line():
    assert hk_to_decimal("0.85") == 1.85
    assert hk_to_decimal("1.05") == 2.05
    assert quarter_line("2.75") == 2.75
    assert quarter_line("-0.75") == -0.75
    assert quarter_line("2.30") is None


def test_normalize_ah_opening_and_current():
    row = normalize_ah({
        "matchId": "123",
        "companyId": "8",
        "handicapIndex": 1,
        "initialHandicap": "0.75",
        "initialHome": "0.92",
        "initialAway": "0.96",
        "instantHandicap": "1.00",
        "instantHome": "1.05",
        "instantAway": "0.83",
        "close": False,
        "inPlay": False,
        "Odds Type": "2",
        "changeTime": 1788700000,
    })
    assert row.market == "AH"
    assert row.opening_line == 0.75
    assert row.current_line == 1.0
    assert row.opening_side_a_odds == 1.92
    assert row.current_side_a_odds == 2.05
    assert row.line_index == 1


def test_normalize_ou_preserves_quarter_total_and_prices():
    row = normalize_ou({
        "matchId": "123",
        "companyId": "8",
        "handicapIndex": 2,
        "initialHandicap": "2.50",
        "initialOver": "0.90",
        "initialUnder": "0.98",
        "instantHandicap": "2.75",
        "instantOver": "0.91",
        "instantUnder": "0.97",
        "close": False,
        "inPlay": False,
        "Odds Type": "1",
    })
    assert row.opening_line == 2.5
    assert row.current_line == 2.75
    assert row.current_side_a_odds == 1.91
    assert row.current_side_b_odds == 1.97


def test_malformed_line_fails_closed():
    records = [{
        "matchId": "123", "companyId": "8", "handicapIndex": 1,
        "initialHandicap": "2.30", "initialOver": "0.90", "initialUnder": "0.90",
        "instantHandicap": "2.75", "instantOver": "0.90", "instantUnder": "0.90",
    }]
    assert normalize_market_records(records, "OU") == []


def test_execution_eligibility_rejects_live_closed_or_unknown_stage():
    base = {"close": False, "in_play": False, "odds_stage": "2"}
    assert is_prematch_execution_eligible(base)
    assert not is_prematch_execution_eligible({**base, "close": True})
    assert not is_prematch_execution_eligible({**base, "in_play": True})
    assert not is_prematch_execution_eligible({**base, "odds_stage": "3"})
    assert not is_prematch_execution_eligible({**base, "odds_stage": "0"})
