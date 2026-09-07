from odds_scanner.scanner import evaluate_candidate
from odds_scanner.settlement_ev import settlement_ev
from odds_scanner.sgodds_provider import CurrentMarket


def _market(ah_odds=1.92):
    return CurrentMarket(
        source="test",
        league="E0",
        date="2026-09-07",
        kickoff="19:30",
        home="Alpha",
        away="Beta",
        ah_home_line=-0.75,
        ah_home_odds=ah_odds,
        ah_away_line=0.75,
        ah_away_odds=1.94,
        ou_line=2.5,
        over_odds=1.91,
        under_odds=1.95,
        one_x_two_home=1.70,
        one_x_two_draw=3.80,
        one_x_two_away=4.60,
    )


def _pattern():
    dist = {"FULL_WIN": 60, "HALF_WIN": 5, "PUSH": 5, "HALF_LOSS": 5, "FULL_LOSS": 25}
    return {
        "pattern_id": "AH::test",
        "pattern": "AH_LINE|H|AH=-0.75",
        "pattern_key": {
            "family": "AH_LINE",
            "favorite_side": "H",
            "ah_line": -0.75,
            "ou_line": None,
            "ou_side": None,
            "ah_price_band": None,
            "ou_price_band": None,
            "favorite_probability_band": None,
        },
        "family": "AH_LINE",
        "market": "AH",
        "train_n": 300,
        "validation_n": 150,
        "holdout_n": 80,
        "q_validation_bh": 0.04,
        "settlement_distributions": {"train": dist, "validation": dist, "holdout": dist},
    }


def test_settlement_ev_reprices_same_outcomes_at_current_odds():
    dist = {"FULL_WIN": 50, "HALF_WIN": 0, "PUSH": 0, "HALF_LOSS": 0, "FULL_LOSS": 50}
    assert round(settlement_ev(dist, 2.10), 6) == 0.05
    assert round(settlement_ev(dist, 1.90), 6) == -0.05


def test_candidate_requires_exact_structure_and_positive_current_ev():
    candidate, reason = evaluate_candidate(_market(), _pattern(), min_ev=0.01)
    assert reason == "ELIGIBLE"
    assert candidate is not None
    assert candidate["line"] == -0.75
    assert candidate["current_odds"] == 1.92
    assert candidate["min_phase_ev"] > 0.01


def test_candidate_rejects_price_outside_tradable_range():
    candidate, reason = evaluate_candidate(_market(1.68), _pattern(), min_ev=0.01)
    assert candidate is None
    assert reason == "PRICE_OUT_OF_RANGE"
