from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

PREREG_PATH = Path("reports/v2_forward_preregistration.json")
ENTRY_STATUS_PATH = Path("reports/v2_forward_entry_status.json")
CLV_STATUS_PATH = Path("reports/v2_forward_clv_status.json")
PERFORMANCE_PATH = Path("reports/v2_forward_performance.json")
REPORT_PATH = Path("reports/v2_forward_readiness.json")


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return obj if isinstance(obj, dict) else {}


def _gate(name: str, value, threshold, passed: bool | None, status: str | None = None) -> dict:
    if status is None:
        status = "PASS" if passed is True else "FAIL" if passed is False else "PENDING"
    return {"gate": name, "value": value, "threshold": threshold, "status": status}


def _candidate_readiness(candidate_id: str, rules: dict, entries: dict, clv: dict, perf: dict) -> dict:
    minimum_n = int(rules.get("minimum_settled_entries_per_candidate", 150))
    minimum_leagues = int(rules.get("minimum_distinct_leagues_per_candidate", 3))
    minimum_positive_share = float(rules.get("minimum_positive_league_share", 0.60))
    minimum_clv_share = float(rules.get("minimum_comparable_clv_share", 0.70))
    maximum_concentration = float(rules.get("maximum_single_league_share_of_absolute_profit", 0.60))

    entry_n = int((entries.get("entries_by_candidate") or {}).get(candidate_id, 0) or 0)
    cclv = (clv.get("by_candidate") or {}).get(candidate_id) or {}
    cperf = (perf.get("by_candidate") or {}).get(candidate_id) or {}
    settled_n = int(cperf.get("settled_entries", 0) or 0)
    distinct_leagues = int(cperf.get("distinct_leagues", 0) or 0)
    positive_league_share = cperf.get("positive_league_share")
    roi = cperf.get("roi")
    bootstrap_low = cperf.get("bootstrap_roi_ci95_lower")
    concentration = cperf.get("max_single_league_share_of_absolute_profit")
    drawdown = cperf.get("max_drawdown_units")
    losing_streak = cperf.get("longest_losing_streak")
    line_move_reported = bool(cclv.get("entries", 0)) or bool(cperf.get("entry_to_close_line_move_reported", False))
    comparable_share = cclv.get("comparable_share")
    mean_clv = cclv.get("mean_clv")
    median_clv = cclv.get("median_clv")

    minimum_sample_met = settled_n >= minimum_n
    gates = [
        _gate("minimum_settled_entries", settled_n, minimum_n, minimum_sample_met),
        _gate("minimum_distinct_leagues", distinct_leagues, minimum_leagues, distinct_leagues >= minimum_leagues if minimum_sample_met else None),
        _gate("minimum_positive_league_share", positive_league_share, minimum_positive_share, (positive_league_share is not None and float(positive_league_share) >= minimum_positive_share) if minimum_sample_met else None),
        _gate("positive_flat_stake_roi", roi, "> 0", (roi is not None and float(roi) > 0) if minimum_sample_met else None),
        _gate("positive_mean_comparable_clv", mean_clv, "> 0", (mean_clv is not None and float(mean_clv) > 0) if minimum_sample_met else None),
        _gate("positive_median_comparable_clv", median_clv, "> 0", (median_clv is not None and float(median_clv) > 0) if minimum_sample_met else None),
        _gate("bootstrap_roi_ci95_lower_above_zero", bootstrap_low, "> 0", (bootstrap_low is not None and float(bootstrap_low) > 0) if minimum_sample_met else None),
        _gate("maximum_single_league_profit_concentration", concentration, f"<= {maximum_concentration}", (concentration is not None and float(concentration) <= maximum_concentration) if minimum_sample_met else None),
        _gate("empirical_drawdown_report", drawdown, "reported", drawdown is not None if minimum_sample_met else None),
        _gate("longest_losing_streak_report", losing_streak, "reported", losing_streak is not None if minimum_sample_met else None),
        _gate("entry_to_close_line_move_report", line_move_reported, True, line_move_reported if minimum_sample_met else None),
        _gate("minimum_comparable_clv_share", comparable_share, minimum_clv_share, (comparable_share is not None and float(comparable_share) >= minimum_clv_share) if minimum_sample_met else None),
    ]

    if not minimum_sample_met:
        status = "COLLECTING_FORWARD_EVIDENCE"
    elif all(g["status"] == "PASS" for g in gates):
        status = "FORWARD_PAPER_CONFIRMED"
    else:
        status = "FORWARD_NOT_CONFIRMED"

    return {
        "candidate_id": candidate_id,
        "status": status,
        "entries_recorded": entry_n,
        "settled_entries": settled_n,
        "remaining_to_minimum_settled_entries": max(0, minimum_n - settled_n),
        "gates": gates,
        "paper_label": "PAPER_RESEARCH_ONLY",
        "production_edge": False,
        "production_promotion_allowed": False,
    }


def build_readiness(root: Path = Path(".")) -> dict:
    prereg = _load(root / PREREG_PATH)
    entries = _load(root / ENTRY_STATUS_PATH)
    clv = _load(root / CLV_STATUS_PATH)
    perf = _load(root / PERFORMANCE_PATH)
    ids = [str(x) for x in (prereg.get("candidate_ids") or [])]
    generated_at = datetime.now(timezone.utc).isoformat()

    if len(ids) != 3 or prereg.get("paper_label") != "PAPER_RESEARCH_ONLY":
        payload = {
            "schema_version": "1.0",
            "classification": "VALIDATION_V2_FORWARD_READINESS",
            "status": "PREREGISTRATION_UNAVAILABLE_OR_DRIFTED",
            "generated_at": generated_at,
            "production_promotion_allowed": False,
        }
        return _write(root, payload)

    rules = prereg.get("forward_evaluation") or {}
    candidates = [_candidate_readiness(cid, rules, entries, clv, perf) for cid in ids]
    statuses = [c["status"] for c in candidates]
    if all(x == "FORWARD_PAPER_CONFIRMED" for x in statuses):
        overall = "FORWARD_PAPER_CONFIRMED_REQUIRES_SEPARATE_POST_FORWARD_AUDIT"
    elif any(x == "FORWARD_NOT_CONFIRMED" for x in statuses):
        overall = "FORWARD_NOT_CONFIRMED"
    else:
        overall = "COLLECTING_FORWARD_EVIDENCE"

    payload = {
        "schema_version": "1.0",
        "classification": "VALIDATION_V2_FORWARD_READINESS",
        "status": overall,
        "generated_at": generated_at,
        "candidate_count": len(candidates),
        "forward_start": prereg.get("amended_at") or prereg.get("created_at"),
        "scheduled_cadence_hours": (prereg.get("collection_policy") or {}).get("scheduled_cadence_hours"),
        "entry_status": entries.get("status") or "UNAVAILABLE",
        "clv_status": clv.get("status") or "UNAVAILABLE",
        "performance_status": perf.get("status") or "NOT_YET_AVAILABLE",
        "candidates": candidates,
        "all_forward_gates_passed": all(x == "FORWARD_PAPER_CONFIRMED" for x in statuses),
        "separate_post_forward_audit_required": True,
        "separate_untouched_confirmation_required_before_any_production_consideration": True,
        "paper_label": "PAPER_RESEARCH_ONLY",
        "production_edge": False,
        "production_promotion_allowed": False,
    }
    return _write(root, payload)


def _write(root: Path, payload: dict) -> dict:
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_readiness(), ensure_ascii=False))
