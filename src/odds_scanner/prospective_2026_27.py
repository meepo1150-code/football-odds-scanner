from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

PREREG = Path("reports/prospective_2026_27_preregistration.json")
HISTORY_STATE = Path("reports/oddspapi_history_state.json")
RESULT_JOIN = Path("reports/oddspapi_result_join.json")
SETTLED = Path("reports/oddspapi_settled_history.json")
OUTPUT = Path("reports/prospective_2026_27_status.json")

REQUIRED_GATES = {
    "positive_roi_all_phases",
    "validation_and_holdout_bootstrap_ci_lower_bound",
    "validation_fdr_q_max",
    "cross_league_min",
    "positive_league_share_min",
    "minimum_current_repriced_ev",
    "execution_odds_default_range",
    "require_positive_forward_clv",
    "require_bucket_sensitivity_stability",
    "require_no_single_season_or_league_concentration",
    "require_empirical_risk_report",
}


def _load(root: Path, rel: Path) -> dict | None:
    p = root / rel
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def build_status(root: Path) -> dict:
    prereg = _load(root, PREREG)
    if prereg is None:
        raise FileNotFoundError(PREREG)
    gates = prereg.get("frozen_promotion_gates") or {}
    missing = sorted(REQUIRED_GATES - set(gates))
    if missing:
        raise ValueError(f"Prospective preregistration missing frozen gates: {missing}")
    if prereg.get("locked_before_2026_27_outcomes_mature") is not True:
        raise ValueError("Prospective preregistration is not locked")

    history = _load(root, HISTORY_STATE) or {}
    join = _load(root, RESULT_JOIN) or {}
    settled = _load(root, SETTLED) or {}

    archive_rows = int(history.get("archive_rows") or 0)
    queued = int(history.get("queued_remaining") or 0)
    settled_fixtures = int(settled.get("settled_fixtures") or 0)
    join_rate = float(join.get("join_rate") or 0.0)

    blockers: list[str] = []
    if history.get("backfill_complete") is not True:
        blockers.append("HISTORICAL_BACKFILL_INCOMPLETE")
    if queued > 0:
        blockers.append("HISTORY_QUEUE_NOT_DRAINED")
    if archive_rows <= 0:
        blockers.append("NO_ARCHIVED_FIXTURES")
    if settled_fixtures <= 0:
        blockers.append("NO_SETTLED_FIXTURES")
    blockers.append("2026_27_PROSPECTIVE_SEASON_NOT_COMPLETE")
    blockers.append("PROSPECTIVE_PHASE_VALIDATION_NOT_RUN")

    return {
        "schema_version": "1.0",
        "classification": "PROSPECTIVE_COLLECTION_STATUS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "preregistration_locked": True,
        "season": "2026/27",
        "production_promotion_allowed": False,
        "production_registry_should_remain_empty_until_all_gates_pass": True,
        "archive": {
            "archive_rows": archive_rows,
            "queued_remaining": queued,
            "backfill_complete": bool(history.get("backfill_complete")),
            "coverage_start": history.get("coverage_start"),
            "discovery_cursor": history.get("discovery_cursor"),
        },
        "results": {
            "joined_fixtures": int(join.get("joined_fixtures") or 0),
            "join_rate": join_rate,
            "settled_fixtures": settled_fixtures,
            "settled_observations": int(settled.get("settled_observations") or 0),
        },
        "frozen_gates_count": len(gates),
        "blockers": blockers,
        "next_action": "CONTINUE_PROSPECTIVE_ARCHIVE_AND_EXACT_RESULT_COLLECTION",
        "paper_shadow_status": "PAPER_RESEARCH_ONLY_ALLOWED",
    }


def write_status(root: Path = Path(".")) -> dict:
    payload = build_status(root)
    p = root / OUTPUT
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(write_status())
