from __future__ import annotations
import argparse, json, math
from pathlib import Path


def _key(b: dict) -> tuple[str, float, float]:
    return b["side"], float(b["odds_low"]), float(b["odds_high"])


def _z_score(bucket: dict) -> float | None:
    n = int(bucket["n"])
    p0 = float(bucket["market_expected"])
    p = float(bucket["win_rate"])
    variance = p0 * (1.0 - p0) / n
    if variance <= 0:
        return None
    return (p - p0) / math.sqrt(variance)


def build_audit(report: dict, min_train_n: int = 60, min_test_n: int = 20) -> dict:
    train = {_key(b): b for b in report.get("buckets", []) if b.get("split") == "train"}
    test = {_key(b): b for b in report.get("buckets", []) if b.get("split") == "test"}
    pairs = []
    for key in sorted(set(train) & set(test)):
        tr, te = train[key], test[key]
        tr_roi, te_roi = float(tr["flat_stake_roi"]), float(te["flat_stake_roi"])
        tr_gap, te_gap = float(tr["calibration_gap_pp"]), float(te["calibration_gap_pp"])
        tr_clv, te_clv = tr.get("avg_clv"), te.get("avg_clv")
        z_train, z_test = _z_score(tr), _z_score(te)
        eligible = int(tr["n"]) >= min_train_n and int(te["n"]) >= min_test_n
        consistent_positive = eligible and tr_roi > 0 and te_roi > 0 and tr_gap > 0 and te_gap > 0
        clv_support = tr_clv is not None and te_clv is not None and float(tr_clv) >= 0 and float(te_clv) >= 0
        statistical_support = z_train is not None and z_test is not None and z_train >= 1.0 and z_test >= 1.0
        if consistent_positive and clv_support and statistical_support:
            status = "STRONG_RESEARCH_CANDIDATE"
        elif consistent_positive:
            status = "CONSISTENT_POSITIVE_RESEARCH_CANDIDATE"
        else:
            status = "NO_GO"
        pairs.append({
            "side": key[0], "odds_low": key[1], "odds_high": key[2],
            "train_n": tr["n"], "test_n": te["n"],
            "train_roi": tr_roi, "test_roi": te_roi,
            "train_gap_pp": tr_gap, "test_gap_pp": te_gap,
            "train_clv": tr_clv, "test_clv": te_clv,
            "train_z": z_train, "test_z": z_test,
            "status": status,
        })
    candidates = [p for p in pairs if p["status"] != "NO_GO"]
    candidates.sort(key=lambda p: (p["status"] == "STRONG_RESEARCH_CANDIDATE", min(p["train_roi"], p["test_roi"]), p["test_n"]), reverse=True)
    return {
        "schema_version": "1.0",
        "source_rows": report.get("rows", 0),
        "test_seasons": report.get("test_seasons", []),
        "criteria": {
            "min_train_n": min_train_n,
            "min_test_n": min_test_n,
            "consistent_positive": "train/test ROI > 0 and calibration gap > 0",
            "strong_extra": "non-negative train/test CLV and z >= 1.0 in both splits",
            "warning": "Screening gate only. Multiple-testing, season instability and market/data-source effects remain unresolved; no candidate is proof of future betting edge."
        },
        "paired_buckets": len(pairs),
        "candidate_count": len(candidates),
        "strong_candidate_count": sum(p["status"] == "STRONG_RESEARCH_CANDIDATE" for p in candidates),
        "candidates": candidates,
    }


def run(report_path: Path, output_path: Path) -> dict:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    audit = build_audit(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return audit


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="reports/backtest.json")
    ap.add_argument("--output", default="reports/audit.json")
    args = ap.parse_args()
    audit = run(Path(args.report), Path(args.output))
    print(json.dumps({"paired_buckets": audit["paired_buckets"], "candidates": audit["candidate_count"], "strong": audit["strong_candidate_count"]}))


if __name__ == "__main__":
    main()
