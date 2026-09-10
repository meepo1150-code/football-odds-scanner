import json
from pathlib import Path

from odds_scanner.validation_v2 import build_status, raw_forward_metrics, shrunk_roi


def test_shrinkage_penalizes_small_samples():
    assert shrunk_roi(10.0, 100, 200) == 10.0 / 300.0
    assert shrunk_roi(10.0, 1000, 200) == 10.0 / 1200.0


def test_forward_metrics_reports_risk_and_mde():
    metrics = raw_forward_metrics([0.9, -1.0, -1.0, 0.9, 0.9], prior_strength=200)
    assert metrics["n"] == 5
    assert metrics["minimum_detectable_roi_95"] is not None
    assert metrics["max_drawdown_units"] >= 2.0
    assert metrics["longest_losing_streak"] == 2


def test_historical_replay_never_promotes(tmp_path: Path):
    (tmp_path / "reports").mkdir()
    prereg = {
        "locked_before_future_v2_prospective_evaluation": True,
        "levels": {
            "RESEARCH_CANDIDATE": {
                "minimum_train_n": 120,
                "minimum_oos_n": 100,
                "maximum_single_holdout_loss_roi": -0.03,
                "minimum_positive_league_share": 0.5,
            }
        },
        "shrinkage": {"prior_strength_bets": 200},
    }
    (tmp_path / "reports/validation_v2_preregistration.json").write_text(json.dumps(prereg))
    report = {
        "candidates": [{
            "pattern_id": "X",
            "status": "REJECT",
            "market": "AH",
            "pattern_key": {"ah_line": -0.25},
            "train_n": 200,
            "validation_n": 100,
            "holdout_n": 60,
            "positive_league_share": 0.6,
            "phase_stats": {
                "train": {"roi": 0.02, "profit_units": 4.0},
                "validation": {"roi": 0.03, "profit_units": 3.0},
                "holdout": {"roi": -0.01, "profit_units": -0.6},
            },
        }]
    }
    (tmp_path / "reports/football_data_multiseason_validation.json").write_text(json.dumps(report))
    status = build_status(tmp_path)
    assert status["research_candidates_under_v2_diagnostic"] == 1
    assert status["production_promotion_allowed"] is False
    c = status["universes"][0]["candidates"][0]
    assert c["v2_diagnostic_status"] == "RESEARCH_CANDIDATE"
    assert c["promotion_allowed"] is False
