from __future__ import annotations

import json
from pathlib import Path

from .breadth_data import BIG5_DIVISIONS, download_and_normalize_big5
from .hierarchical_backtest import build_hierarchical_report
from .joint_audit import build_joint_audit
from .normalize import write_csv
from .three_way_audit import build_three_way_audit, write_three_way_audit


def run(root: Path) -> dict:
    raw_path = root / "data/raw/big5_matches.csv"
    norm_path = root / "data/normalized/big5_multimarket_history.csv"
    report_dir = root / "reports/breadth"
    report_dir.mkdir(parents=True, exist_ok=True)

    rows = download_and_normalize_big5(raw_path)
    write_csv(rows, norm_path)
    test_seasons = {"2324", "2425"}

    global_report = build_hierarchical_report(rows, test_seasons=test_seasons, min_n=50)
    global_audit = build_joint_audit(global_report, min_train_n=150, min_test_n=60, fdr_alpha=0.10)
    (report_dir / "global_patterns.json").write_text(json.dumps(global_report, indent=2), encoding="utf-8")
    (report_dir / "global_audit.json").write_text(json.dumps(global_audit, indent=2), encoding="utf-8")

    three_way = build_three_way_audit(rows)
    write_three_way_audit(three_way, report_dir / "three_way_audit.json")

    league_summary = {}
    for div in sorted(BIG5_DIVISIONS):
        league_rows = [r for r in rows if r["division"] == div]
        rep = build_hierarchical_report(league_rows, test_seasons=test_seasons, min_n=20)
        audit = build_joint_audit(rep, min_train_n=60, min_test_n=30, fdr_alpha=0.10)
        (report_dir / f"{div}_patterns.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
        (report_dir / f"{div}_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
        league_summary[div] = {
            "rows": len(league_rows),
            "paired_tests": audit["paired_tests"],
            "robust": audit["robust_candidate_count"],
            "watchlist": audit["watchlist_count"],
        }

    summary = {
        "schema_version": "1.1",
        "engine": "BIG5_DATA_BREADTH_AUDIT",
        "rows": len(rows),
        "divisions": sorted(BIG5_DIVISIONS),
        "seasons": sorted({r["season"] for r in rows}),
        "test_seasons": sorted(test_seasons),
        "global": {
            "paired_tests": global_audit["paired_tests"],
            "robust": global_audit["robust_candidate_count"],
            "watchlist": global_audit["watchlist_count"],
        },
        "three_way": {
            "tested_patterns": three_way["tested_patterns"],
            "global_robust": three_way["global_robust_count"],
            "league_specific_or_unstable": three_way["league_specific_or_unstable_count"],
            "watchlist": three_way["watchlist_count"],
            "split": three_way["split"],
        },
        "leagues": league_summary,
        "source": "pjc-codes/football-data (derived from Football-Data.co.uk)",
        "capability_note": "Big-5 breadth source has variable Asian Handicap line and O/U 2.5 only; alternate goal lines remain a separate provider requirement.",
    }
    (report_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    print(json.dumps(run(Path("."))))


if __name__ == "__main__":
    main()
