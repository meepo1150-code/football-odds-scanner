from __future__ import annotations

import json
import math
from pathlib import Path

from .hierarchical_backtest import build_hierarchical_report
from .pattern_policy import DEFAULT_POLICY

TRAIN_SEASONS = {"1920", "2021", "2122"}
VALIDATION_SEASONS = {"2223", "2324"}
HOLDOUT_SEASONS = {"2425"}


def _normal_two_sided_p(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2.0))


def _roi_z(roi: float, n: int) -> float:
    return 0.0 if n <= 0 else roi * math.sqrt(n)


def _bh(rows: list[dict], p_field: str = "p_validation", q_field: str = "q_validation_bh") -> None:
    ordered = sorted(enumerate(rows), key=lambda x: x[1][p_field])
    m = len(ordered)
    running = 1.0
    for pos in range(m - 1, -1, -1):
        idx, row = ordered[pos]
        rank = pos + 1
        running = min(running, row[p_field] * m / rank)
        rows[idx][q_field] = round(running, 6)


def _phase_buckets(rows: list[dict], seasons: set[str], min_n: int) -> dict[tuple[str, str], dict]:
    selected = [r for r in rows if r["season"] in seasons]
    report = build_hierarchical_report(selected, test_seasons=seasons, min_n=min_n)
    out: dict[tuple[str, str], dict] = {}
    for b in report["buckets"]:
        if b["split"] != "test":
            continue
        markets = [("AH", b["ah_roi"])]
        if b["family"] != "AH_LINE":
            markets.append(("OU", b["ou_roi"]))
        for market, roi in markets:
            if roi is not None:
                out[(b["pattern"], market)] = {**b, "roi": float(roi)}
    return out


def _league_consistency(rows: list[dict], pattern: str, market: str, min_n: int = 20) -> dict:
    leagues = sorted({r["division"] for r in rows})
    details = {}
    positive = 0
    eligible = 0
    for league in leagues:
        league_rows = [r for r in rows if r["division"] == league]
        bucket = _phase_buckets(league_rows, HOLDOUT_SEASONS, min_n).get((pattern, market))
        if not bucket:
            continue
        eligible += 1
        roi = bucket["roi"]
        if roi > 0:
            positive += 1
        details[league] = {"n": bucket["n"], "roi": round(roi, 6)}
    share = positive / eligible if eligible else 0.0
    return {
        "eligible_leagues": eligible,
        "positive_leagues": positive,
        "positive_share": round(share, 6),
        "stable": eligible >= 3 and share >= 0.60,
        "details": details,
    }


def build_three_way_audit(
    rows: list[dict],
    *,
    min_train_n: int = 150,
    min_validation_n: int = 80,
    min_holdout_n: int = 40,
    fdr_alpha: float = 0.10,
) -> dict:
    train = _phase_buckets(rows, TRAIN_SEASONS, min_n=20)
    validation = _phase_buckets(rows, VALIDATION_SEASONS, min_n=20)
    holdout = _phase_buckets(rows, HOLDOUT_SEASONS, min_n=20)

    common = sorted(set(train) & set(validation) & set(holdout))
    tests = []
    for key in common:
        tr, va, ho = train[key], validation[key], holdout[key]
        if tr["n"] < min_train_n or va["n"] < min_validation_n or ho["n"] < min_holdout_n:
            continue
        pattern, market = key
        z_val = _roi_z(va["roi"], va["n"])
        tests.append({
            "pattern": pattern,
            "family": tr["family"],
            "market": market,
            "train_n": tr["n"],
            "train_roi": round(tr["roi"], 6),
            "validation_n": va["n"],
            "validation_roi": round(va["roi"], 6),
            "holdout_n": ho["n"],
            "holdout_roi": round(ho["roi"], 6),
            "z_validation": round(z_val, 6),
            "p_validation": round(_normal_two_sided_p(z_val), 6),
        })

    _bh(tests)
    for row in tests:
        positive_three = row["train_roi"] > 0 and row["validation_roi"] > 0 and row["holdout_roi"] > 0
        fdr_pass = row.get("q_validation_bh", 1.0) <= fdr_alpha
        cross = _league_consistency(rows, row["pattern"], row["market"])
        row["cross_league_holdout"] = cross
        if positive_three and fdr_pass and cross["stable"]:
            row["status"] = "GLOBAL_ROBUST_RESEARCH_CANDIDATE"
        elif positive_three and fdr_pass:
            row["status"] = "LEAGUE_SPECIFIC_OR_UNSTABLE"
        elif positive_three:
            row["status"] = "WATCHLIST"
        else:
            row["status"] = "REJECT"

    priority = {
        "GLOBAL_ROBUST_RESEARCH_CANDIDATE": 3,
        "LEAGUE_SPECIFIC_OR_UNSTABLE": 2,
        "WATCHLIST": 1,
        "REJECT": 0,
    }
    tests.sort(key=lambda r: (priority[r["status"]], r["holdout_roi"], r["holdout_n"]), reverse=True)
    return {
        "schema_version": "1.0",
        "engine": "THREE_WAY_CROSS_LEAGUE_AUDIT",
        "source_rows": len(rows),
        "split": {
            "train": sorted(TRAIN_SEASONS),
            "validation": sorted(VALIDATION_SEASONS),
            "holdout": sorted(HOLDOUT_SEASONS),
        },
        "gates": {
            "min_train_n": min_train_n,
            "min_validation_n": min_validation_n,
            "min_holdout_n": min_holdout_n,
            "validation_fdr_alpha": fdr_alpha,
            "cross_league_min_eligible": 3,
            "cross_league_positive_share": DEFAULT_POLICY.min_positive_season_share,
        },
        "tested_patterns": len(tests),
        "global_robust_count": sum(r["status"] == "GLOBAL_ROBUST_RESEARCH_CANDIDATE" for r in tests),
        "league_specific_or_unstable_count": sum(r["status"] == "LEAGUE_SPECIFIC_OR_UNSTABLE" for r in tests),
        "watchlist_count": sum(r["status"] == "WATCHLIST" for r in tests),
        "note": "Holdout 2024/25 is evaluated once under frozen gates. Do not retune thresholds from holdout outcomes and then reuse the same season as untouched evidence.",
        "patterns": tests,
    }


def write_three_way_audit(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
