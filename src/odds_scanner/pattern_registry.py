from __future__ import annotations

import json
from pathlib import Path

PROMOTABLE_STATUS = "GLOBAL_ROBUST_RESEARCH_CANDIDATE"


def build_pattern_registry(three_way_audit: dict) -> dict:
    patterns = []
    for row in three_way_audit.get("patterns", []):
        if row.get("status") != PROMOTABLE_STATUS:
            continue
        patterns.append({
            "pattern_id": f"{row['market']}::{row['pattern']}",
            "pattern": row["pattern"],
            "pattern_key": row.get("pattern_key", {}),
            "family": row["family"],
            "market": row["market"],
            "train_n": row["train_n"],
            "validation_n": row["validation_n"],
            "holdout_n": row["holdout_n"],
            "train_roi": row["train_roi"],
            "validation_roi": row["validation_roi"],
            "holdout_roi": row["holdout_roi"],
            "settlement_distributions": row.get("settlement_distributions", {}),
            "q_validation_bh": row["q_validation_bh"],
            "cross_league_holdout": row["cross_league_holdout"],
        })
    return {
        "schema_version": "1.2",
        "registry_type": "FROZEN_VALIDATED_PATTERNS",
        "promotion_rule": PROMOTABLE_STATUS,
        "source_engine": three_way_audit.get("engine"),
        "source_rows": three_way_audit.get("source_rows", 0),
        "split": three_way_audit.get("split", {}),
        "pattern_count": len(patterns),
        "patterns": patterns,
        "warning": "Only patterns that passed the frozen three-way and cross-league gates may enter production scanning.",
    }


def write_pattern_registry(registry: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
