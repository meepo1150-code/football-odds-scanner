from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

PREREG = Path("reports/validation_v2_preregistration.json")
OUTPUT = Path("reports/validation_v2_status.json")
HISTORICAL_REPORTS = (
    ("BIG5_AH", Path("reports/football_data_multiseason_validation.json")),
    ("INDEPENDENT_AH", Path("reports/independent_league_validation.json")),
    ("THIRD_UNIVERSE_OU", Path("reports/third_universe_ou_validation.json")),
)


def shrunk_roi(profit_units: float, n: int, prior_strength: int = 200) -> float:
    if n <= 0:
        return 0.0
    return float(profit_units) / float(n + prior_strength)


def minimum_detectable_roi(profits: list[float], z: float = 1.96) -> float | None:
    """Approximate two-sided MDE around zero for flat-stake unit returns."""
    if len(profits) < 2:
        return None
    sigma = pstdev(profits)
    return z * sigma / math.sqrt(len(profits))


def raw_forward_metrics(profits: list[float], prior_strength: int = 200) -> dict:
    n = len(profits)
    total = sum(profits)
    roi = total / n if n else 0.0
    peak = 0.0
    equity = 0.0
    max_dd = 0.0
    losing = 0
    longest_losing = 0
    for p in profits:
        equity += p
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if p < 0:
            losing += 1
            longest_losing = max(longest_losing, losing)
        else:
            losing = 0
    return {
        "n": n,
        "profit_units": round(total, 8),
        "roi": round(roi, 8),
        "shrunk_roi": round(shrunk_roi(total, n, prior_strength), 8),
        "minimum_detectable_roi_95": None if n < 2 else round(minimum_detectable_roi(profits) or 0.0, 8),
        "max_drawdown_units": round(max_dd, 8),
        "longest_losing_streak": longest_losing,
    }


def _load(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _phase(candidate: dict, name: str) -> dict:
    return (candidate.get("phase_stats") or {}).get(name) or {}


def _diagnose_candidate(candidate: dict, rules: dict) -> dict:
    research = rules["levels"]["RESEARCH_CANDIDATE"]
    train = _phase(candidate, "train")
    validation = _phase(candidate, "validation")
    holdout = _phase(candidate, "holdout")

    train_n = int(candidate.get("train_n") or train.get("n") or 0)
    validation_n = int(candidate.get("validation_n") or validation.get("n") or 0)
    holdout_n = int(candidate.get("holdout_n") or holdout.get("n") or 0)
    oos_n = validation_n + holdout_n
    validation_profit = float(validation.get("profit_units") or 0.0)
    holdout_profit = float(holdout.get("profit_units") or 0.0)
    oos_profit = validation_profit + holdout_profit
    pooled_oos_roi = oos_profit / oos_n if oos_n else 0.0
    holdout_roi = float(holdout.get("roi") or 0.0)
    train_roi = float(train.get("roi") or 0.0)
    positive_league_share = float(candidate.get("positive_league_share") or 0.0)
    shrink = rules["shrinkage"]
    shrunk = shrunk_roi(oos_profit, oos_n, int(shrink["prior_strength_bets"]))

    gates = {
        "train_n": train_n >= int(research["minimum_train_n"]),
        "oos_n": oos_n >= int(research["minimum_oos_n"]),
        "train_roi_positive": train_roi > 0,
        "pooled_oos_roi_positive": pooled_oos_roi > 0,
        "holdout_not_catastrophic": holdout_n == 0 or holdout_roi >= float(research["maximum_single_holdout_loss_roi"]),
        "positive_league_share": positive_league_share >= float(research["minimum_positive_league_share"]),
        "shrunk_oos_roi_positive": shrunk > 0,
    }
    status = "RESEARCH_CANDIDATE" if all(gates.values()) else "RESEARCH_REJECT"

    return {
        "pattern_id": candidate.get("pattern_id"),
        "market": candidate.get("market"),
        "pattern_key": candidate.get("pattern_key"),
        "v1_status": candidate.get("status"),
        "v2_diagnostic_status": status,
        "train_n": train_n,
        "oos_n": oos_n,
        "holdout_n": holdout_n,
        "train_roi": round(train_roi, 8),
        "pooled_oos_roi": round(pooled_oos_roi, 8),
        "holdout_roi": round(holdout_roi, 8),
        "shrunk_oos_roi": round(shrunk, 8),
        "positive_league_share": round(positive_league_share, 8),
        "mde_roi_95": None,
        "mde_note": "Unavailable from aggregate frozen report; raw per-bet returns are required. Future v2 forward evaluation computes MDE directly.",
        "gates": gates,
        "promotion_allowed": False,
    }


def build_status(root: Path = Path(".")) -> dict:
    rules = _load(root / PREREG)
    if not rules:
        raise FileNotFoundError(PREREG)
    if rules.get("locked_before_future_v2_prospective_evaluation") is not True:
        raise ValueError("Validation v2 preregistration must be locked")

    universes = []
    total_candidates = 0
    total_research = 0
    for label, rel in HISTORICAL_REPORTS:
        report = _load(root / rel)
        if not report:
            universes.append({"universe": label, "report": str(rel), "status": "REPORT_MISSING", "candidates": []})
            continue
        diagnosed = [_diagnose_candidate(c, rules) for c in (report.get("candidates") or [])]
        research_count = sum(c["v2_diagnostic_status"] == "RESEARCH_CANDIDATE" for c in diagnosed)
        total_candidates += len(diagnosed)
        total_research += research_count
        universes.append({
            "universe": label,
            "report": str(rel),
            "status": "DIAGNOSTIC_REPLAY_ONLY",
            "candidate_count": len(diagnosed),
            "research_candidate_count": research_count,
            "candidates": diagnosed,
        })

    return {
        "schema_version": "1.0",
        "classification": "VALIDATION_V2_STATUS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "preregistration_locked": True,
        "historical_replay_is_diagnostic_only": True,
        "production_promotion_allowed": False,
        "production_registry_must_remain_unchanged": True,
        "total_historical_candidates_replayed": total_candidates,
        "research_candidates_under_v2_diagnostic": total_research,
        "paper_candidates": 0,
        "paper_note": "Paper status requires new forward observations under the locked v2 rules; viewed historical data cannot qualify.",
        "universes": universes,
    }


def write_status(root: Path = Path(".")) -> dict:
    payload = build_status(root)
    out = root / OUTPUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(write_status(), ensure_ascii=False))
