from __future__ import annotations
import json, math
from pathlib import Path

from .pattern_policy import DEFAULT_POLICY


def _normal_two_sided_p(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2.0))


def _roi_z(roi: float, n: int, assumed_sd: float = 1.0) -> float:
    return 0.0 if n <= 0 else roi / (assumed_sd / math.sqrt(n))


def _bh_adjust(rows: list[dict], p_field: str, q_field: str) -> None:
    indexed = sorted(enumerate(rows), key=lambda x: x[1][p_field])
    m = len(indexed)
    if not m:
        return
    running = 1.0
    for rank_from_end, (idx, row) in enumerate(reversed(indexed), start=1):
        rank = m - rank_from_end + 1
        q = min(running, row[p_field] * m / rank)
        running = q
        rows[idx][q_field] = round(q, 6)


def _season_stability(bucket: dict, field: str) -> dict:
    seasons = bucket.get("seasons", {})
    eligible = [v for v in seasons.values() if v.get("n", 0) >= 10 and v.get(field) is not None]
    if not eligible:
        return {"eligible_seasons": 0, "positive_share": 0.0, "stable": False}
    positive = sum(1 for v in eligible if float(v[field]) > 0)
    share = positive / len(eligible)
    return {
        "eligible_seasons": len(eligible),
        "positive_share": round(share, 6),
        "stable": share >= DEFAULT_POLICY.min_positive_season_share,
    }


def build_joint_audit(report: dict, *, min_train_n: int = 60, min_test_n: int = 30, fdr_alpha: float = 0.10) -> dict:
    train = {b["pattern"]: b for b in report.get("buckets", []) if b["split"] == "train"}
    test = {b["pattern"]: b for b in report.get("buckets", []) if b["split"] == "test"}
    paired = []
    for pattern in sorted(set(train) & set(test)):
        tr, te = train[pattern], test[pattern]
        if tr["n"] < min_train_n or te["n"] < min_test_n:
            continue
        market_fields = [("AH", "ah_roi")]
        if tr["family"] != "AH_LINE":
            market_fields.append(("OU", "ou_roi"))
        for market, field in market_fields:
            if tr.get(field) is None or te.get(field) is None:
                continue
            tr_roi, te_roi = float(tr[field]), float(te[field])
            z_train = _roi_z(tr_roi, tr["n"])
            z_test = _roi_z(te_roi, te["n"])
            p = max(_normal_two_sided_p(z_train), _normal_two_sided_p(z_test))
            st_train = _season_stability(tr, field)
            st_test = _season_stability(te, field)
            paired.append({
                "pattern": pattern,
                "family": tr["family"],
                "market": market,
                "train_n": tr["n"],
                "test_n": te["n"],
                "train_roi": tr_roi,
                "test_roi": te_roi,
                "z_train": round(z_train, 6),
                "z_test": round(z_test, 6),
                "p_conservative": round(p, 6),
                "train_season_stability": st_train,
                "test_season_stability": st_test,
            })

    _bh_adjust(paired, "p_conservative", "q_bh")
    for row in paired:
        positive_both = row["train_roi"] > 0 and row["test_roi"] > 0
        stable = row["train_season_stability"]["stable"] and row["test_season_stability"]["stable"]
        fdr_pass = row.get("q_bh", 1.0) <= fdr_alpha
        if positive_both and stable and fdr_pass:
            status = "ROBUST_RESEARCH_CANDIDATE"
        elif positive_both:
            status = "WATCHLIST"
        else:
            status = "REJECT"
        row["status"] = status

    paired.sort(key=lambda r: (
        r["status"] == "ROBUST_RESEARCH_CANDIDATE",
        r["status"] == "WATCHLIST",
        -r.get("q_bh", 1.0),
        r["test_roi"],
        r["test_n"],
    ), reverse=True)
    return {
        "schema_version": "1.1",
        "engine": "PAIRED_HIERARCHICAL_PATTERN_AUDIT",
        "source_rows": report.get("source_rows", 0),
        "paired_tests": len(paired),
        "robust_candidate_count": sum(1 for r in paired if r["status"] == "ROBUST_RESEARCH_CANDIDATE"),
        "watchlist_count": sum(1 for r in paired if r["status"] == "WATCHLIST"),
        "fdr_method": "Benjamini-Hochberg",
        "fdr_alpha": fdr_alpha,
        "note": "Normal-approximation screening is deliberately conservative and is not a final significance claim. Bootstrap/permutation and untouched holdout remain required.",
        "patterns": paired,
    }


def write_audit(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
