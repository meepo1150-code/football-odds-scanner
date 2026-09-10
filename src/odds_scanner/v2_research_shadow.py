from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

CATALOG = Path("reports/v2_research_candidates.json")
VALIDATION_STATUS = Path("reports/validation_v2_status.json")
PROSPECTIVE_STATUS = Path("reports/prospective_2026_27_status.json")
OUTPUT = Path("reports/v2_research_shadow_status.json")


def _load(root: Path, rel: Path) -> dict | None:
    path = root / rel
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _diagnostic_ids(validation: dict) -> set[str]:
    ids: set[str] = set()
    for universe in validation.get("universes") or []:
        for candidate in universe.get("candidates") or []:
            if candidate.get("v2_diagnostic_status") == "RESEARCH_CANDIDATE" and candidate.get("pattern_id"):
                ids.add(str(candidate["pattern_id"]))
    return ids


def build_status(root: Path = Path(".")) -> dict:
    catalog = _load(root, CATALOG)
    validation = _load(root, VALIDATION_STATUS)
    prospective = _load(root, PROSPECTIVE_STATUS) or {}
    if catalog is None:
        raise FileNotFoundError(CATALOG)
    if validation is None:
        raise FileNotFoundError(VALIDATION_STATUS)

    candidates = catalog.get("candidates") or []
    if len(candidates) != 3 or int(catalog.get("candidate_count") or 0) != 3:
        raise ValueError("V2 research candidate catalog must contain exactly three frozen candidates")

    catalog_ids = {str(c.get("pattern_id")) for c in candidates}
    diagnostic_ids = _diagnostic_ids(validation)
    if catalog_ids != diagnostic_ids:
        raise ValueError("Frozen candidate catalog does not exactly match validation-v2 research candidates")

    comparison_policy = catalog.get("forward_comparison_policy") or {}
    main_line_required = comparison_policy.get("missing_main_line_behavior") == "NOT_COMPARABLE"
    candidate_rows = []
    for candidate in candidates:
        candidate_rows.append({
            "pattern_id": candidate["pattern_id"],
            "universe": candidate["universe"],
            "market": candidate["market"],
            "pattern_key": candidate["pattern_key"],
            "shadow_status": "WAITING_FOR_COMPARABLE_FORWARD_DATA" if main_line_required else "CONFIGURATION_ERROR",
            "forward_bets": 0,
            "paper_candidate": False,
            "production_candidate": False,
            "promotion_allowed": False,
            "blockers": [
                "ODDSPAPI_MAIN_LINE_MAPPING_NOT_PROVEN",
                "FORWARD_SAMPLE_NOT_EVALUATED"
            ],
        })

    blockers = list(prospective.get("blockers") or [])
    if "ODDSPAPI_MAIN_LINE_MAPPING_NOT_PROVEN" not in blockers:
        blockers.append("ODDSPAPI_MAIN_LINE_MAPPING_NOT_PROVEN")

    return {
        "schema_version": "1.0",
        "classification": "V2_RESEARCH_SHADOW_STATUS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_count": 3,
        "paper_label": "PAPER_RESEARCH_ONLY",
        "production_promotion_allowed": False,
        "production_registry_must_remain_unchanged": True,
        "prospective_season": prospective.get("season", "2026/27"),
        "candidate_source_verified": True,
        "main_line_comparability_proven": False,
        "candidates": candidate_rows,
        "blockers": blockers,
        "next_action": "PROVE_ODDSPAPI_MAIN_LINE_SEMANTICS_BEFORE_FORWARD_MATCHING",
    }


def write_status(root: Path = Path(".")) -> dict:
    payload = build_status(root)
    path = root / OUTPUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(write_status(), ensure_ascii=False))
