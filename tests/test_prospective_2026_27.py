import json

from odds_scanner.prospective_2026_27 import build_status


def test_prospective_status_is_fail_closed_and_never_promotes(tmp_path):
    (tmp_path / "reports").mkdir()
    prereg = {
        "locked_before_2026_27_outcomes_mature": True,
        "frozen_promotion_gates": {
            "positive_roi_all_phases": True,
            "validation_and_holdout_bootstrap_ci_lower_bound": 0.0,
            "validation_fdr_q_max": 0.10,
            "cross_league_min": 3,
            "positive_league_share_min": 0.60,
            "minimum_current_repriced_ev": 0.01,
            "execution_odds_default_range": [1.8, 2.2],
            "require_positive_forward_clv": True,
            "require_bucket_sensitivity_stability": True,
            "require_no_single_season_or_league_concentration": True,
            "require_empirical_risk_report": True,
        },
    }
    (tmp_path / "reports/prospective_2026_27_preregistration.json").write_text(json.dumps(prereg), encoding="utf-8")
    (tmp_path / "reports/oddspapi_history_state.json").write_text(json.dumps({
        "archive_rows": 218,
        "queued_remaining": 17,
        "backfill_complete": False,
        "coverage_start": "2026-01-01T00:00:00+00:00",
    }), encoding="utf-8")
    (tmp_path / "reports/oddspapi_result_join.json").write_text(json.dumps({
        "joined_fixtures": 50,
        "join_rate": 0.24,
    }), encoding="utf-8")
    (tmp_path / "reports/oddspapi_settled_history.json").write_text(json.dumps({
        "settled_fixtures": 50,
        "settled_observations": 8848,
    }), encoding="utf-8")

    out = build_status(tmp_path)
    assert out["production_promotion_allowed"] is False
    assert out["paper_shadow_status"] == "PAPER_RESEARCH_ONLY_ALLOWED"
    assert "HISTORY_QUEUE_NOT_DRAINED" in out["blockers"]
    assert "2026_27_PROSPECTIVE_SEASON_NOT_COMPLETE" in out["blockers"]


def test_prospective_preregistration_missing_gate_fails_closed(tmp_path):
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports/prospective_2026_27_preregistration.json").write_text(json.dumps({
        "locked_before_2026_27_outcomes_mature": True,
        "frozen_promotion_gates": {},
    }), encoding="utf-8")
    try:
        build_status(tmp_path)
    except ValueError as exc:
        assert "missing frozen gates" in str(exc)
    else:
        raise AssertionError("missing prospective gates must fail closed")
