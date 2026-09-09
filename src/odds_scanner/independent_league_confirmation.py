from __future__ import annotations

import json
from pathlib import Path

from . import multiseason_market_research as base

INDEPENDENT_LEAGUES = {
    "EFL Championship": "championship",
    "2. Bundesliga": "bundesliga-2",
    "LaLiga 2": "la-liga-2",
    "Ligue 2": "ligue-2",
    "Serie B": "serie-b",
}
REPORT_PATH = Path("reports/independent_league_validation.json")
CANDIDATE_REGISTRY_PATH = Path("reports/independent_league_pattern_registry_candidate.json")


def run(root: Path, mirror_root: Path) -> dict:
    original = dict(base.LEAGUES)
    try:
        base.LEAGUES = dict(INDEPENDENT_LEAGUES)
        rows, provenance = base.load_mirror(mirror_root)
        report, registry = base.validate(rows)
    finally:
        base.LEAGUES = original

    report["schema_version"] = "2.1"
    report["classification"] = "INDEPENDENT_LEAGUE_MULTI_SEASON_AH_CONFIRMATION"
    report["independent_league_universe"] = INDEPENDENT_LEAGUES
    report["independence_statement"] = (
        "These leagues were excluded from the completed Big-5 holdout evaluation; "
        "their 2025/26 pattern performance was preregistered before this run."
    )
    report["provenance"] = provenance
    report["production_promotion_allowed_by_this_run"] = False
    registry["source"] = (
        "football-data.co.uk via pinned GitHub mirror; independent second-tier league universe; "
        "early odds are first collected after market opening, not true opening"
    )
    registry["promotion_scope"] = "CANDIDATE_ONLY_REQUIRES_SEPARATE_PRODUCTION_AUDIT"

    rp = root / REPORT_PATH
    cp = root / CANDIDATE_REGISTRY_PATH
    rp.parent.mkdir(parents=True, exist_ok=True)
    cp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    cp.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "normalized_rows": len(rows),
        "tested": report["train_positive_patterns_entering_validation"],
        "promoted_candidates": report["promoted_patterns"],
        "mirror_commit": provenance.get("mirror_commit"),
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--mirror-root", type=Path, required=True)
    p.add_argument("--root", type=Path, default=Path("."))
    args = p.parse_args()
    print(run(args.root, args.mirror_root))
