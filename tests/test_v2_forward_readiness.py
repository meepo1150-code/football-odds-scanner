import json
from pathlib import Path

from odds_scanner.v2_forward_readiness import build_readiness

IDS = ["FD_AH_4E30F9F2EC34", "FD_AH_1D65F429F6A5", "FD_OU25_D0A17AE7DB9C"]


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _prereg(root: Path) -> None:
    _write(root / "reports/v2_forward_preregistration.json", {
        "paper_label": "PAPER_RESEARCH_ONLY",
        "amended_at": "2026-09-10T13:25:00Z",
        "candidate_ids": IDS,
        "collection_policy": {"scheduled_cadence_hours": 12},
        "forward_evaluation": {
            "minimum_settled_entries_per_candidate": 150,
            "minimum_distinct_leagues_per_candidate": 3,
            "minimum_positive_league_share": 0.60,
            "maximum_single_league_share_of_absolute_profit": 0.60,
            "minimum_comparable_clv_share": 0.70,
        },
    })


def test_before_minimum_sample_is_collecting(tmp_path):
    _prereg(tmp_path)
    _write(tmp_path / "reports/v2_forward_entry_status.json", {"status": "COLLECTING_FORWARD_EVIDENCE", "entries_by_candidate": {x: 10 for x in IDS}})
    _write(tmp_path / "reports/v2_forward_clv_status.json", {"status": "COLLECTING_FORWARD_CLV", "by_candidate": {x: {"entries": 10, "comparable_share": 0.8, "mean_clv": 0.01, "median_clv": 0.01} for x in IDS}})
    out = build_readiness(tmp_path)
    assert out["status"] == "COLLECTING_FORWARD_EVIDENCE"
    assert all(c["status"] == "COLLECTING_FORWARD_EVIDENCE" for c in out["candidates"])
    assert all(c["remaining_to_minimum_settled_entries"] == 150 for c in out["candidates"])
    assert out["production_promotion_allowed"] is False


def test_all_frozen_forward_gates_can_reach_paper_confirmed_only(tmp_path):
    _prereg(tmp_path)
    _write(tmp_path / "reports/v2_forward_entry_status.json", {"status": "COLLECTING_FORWARD_EVIDENCE", "entries_by_candidate": {x: 160 for x in IDS}})
    _write(tmp_path / "reports/v2_forward_clv_status.json", {"status": "COLLECTING_FORWARD_CLV", "by_candidate": {x: {"entries": 160, "comparable_share": 0.80, "mean_clv": 0.01, "median_clv": 0.008} for x in IDS}})
    _write(tmp_path / "reports/v2_forward_performance.json", {"status": "FORWARD_PERFORMANCE_AVAILABLE", "by_candidate": {x: {
        "settled_entries": 155,
        "distinct_leagues": 4,
        "positive_league_share": 0.75,
        "roi": 0.03,
        "bootstrap_roi_ci95_lower": 0.005,
        "max_single_league_share_of_absolute_profit": 0.40,
        "max_drawdown_units": -8.2,
        "longest_losing_streak": 7,
        "entry_to_close_line_move_reported": True,
    } for x in IDS}})
    out = build_readiness(tmp_path)
    assert out["all_forward_gates_passed"] is True
    assert out["status"] == "FORWARD_PAPER_CONFIRMED_REQUIRES_SEPARATE_POST_FORWARD_AUDIT"
    assert all(c["status"] == "FORWARD_PAPER_CONFIRMED" for c in out["candidates"])
    assert all(c["production_edge"] is False for c in out["candidates"])
    assert out["production_promotion_allowed"] is False


def test_gate_failure_after_minimum_sample_is_not_confirmed(tmp_path):
    _prereg(tmp_path)
    _write(tmp_path / "reports/v2_forward_entry_status.json", {"entries_by_candidate": {x: 160 for x in IDS}})
    _write(tmp_path / "reports/v2_forward_clv_status.json", {"by_candidate": {x: {"entries": 160, "comparable_share": 0.80, "mean_clv": 0.01, "median_clv": 0.008} for x in IDS}})
    by = {}
    for x in IDS:
        by[x] = {"settled_entries": 155, "distinct_leagues": 4, "positive_league_share": 0.75, "roi": 0.03, "bootstrap_roi_ci95_lower": 0.005, "max_single_league_share_of_absolute_profit": 0.40, "max_drawdown_units": -8.2, "longest_losing_streak": 7, "entry_to_close_line_move_reported": True}
    by[IDS[1]]["bootstrap_roi_ci95_lower"] = -0.001
    _write(tmp_path / "reports/v2_forward_performance.json", {"by_candidate": by})
    out = build_readiness(tmp_path)
    assert out["status"] == "FORWARD_NOT_CONFIRMED"
    target = next(c for c in out["candidates"] if c["candidate_id"] == IDS[1])
    gate = next(g for g in target["gates"] if g["gate"] == "bootstrap_roi_ci95_lower_above_zero")
    assert gate["status"] == "FAIL"


def test_preregistration_drift_fails_closed(tmp_path):
    _write(tmp_path / "reports/v2_forward_preregistration.json", {"paper_label": "PAPER_RESEARCH_ONLY", "candidate_ids": IDS[:2]})
    out = build_readiness(tmp_path)
    assert out["status"] == "PREREGISTRATION_UNAVAILABLE_OR_DRIFTED"
    assert out["production_promotion_allowed"] is False
