import json
from pathlib import Path

from odds_scanner.v2_research_shadow import build_status


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fixture_root(tmp_path: Path) -> Path:
    _write(tmp_path / "reports/v2_research_candidates.json", {
        "candidate_count": 3,
        "forward_comparison_policy": {"missing_main_line_behavior": "NOT_COMPARABLE"},
        "candidates": [
            {"pattern_id": "A", "universe": "BIG5_AH", "market": "AH", "pattern_key": {}},
            {"pattern_id": "B", "universe": "BIG5_AH", "market": "AH", "pattern_key": {}},
            {"pattern_id": "C", "universe": "THIRD_UNIVERSE_OU", "market": "OU", "pattern_key": {}},
        ],
    })
    _write(tmp_path / "reports/validation_v2_status.json", {
        "universes": [
            {"candidates": [
                {"pattern_id": "A", "v2_diagnostic_status": "RESEARCH_CANDIDATE"},
                {"pattern_id": "B", "v2_diagnostic_status": "RESEARCH_CANDIDATE"},
            ]},
            {"candidates": [
                {"pattern_id": "C", "v2_diagnostic_status": "RESEARCH_CANDIDATE"},
                {"pattern_id": "D", "v2_diagnostic_status": "RESEARCH_REJECT"},
            ]},
        ]
    })
    _write(tmp_path / "reports/prospective_2026_27_status.json", {
        "season": "2026/27",
        "blockers": ["HISTORICAL_BACKFILL_INCOMPLETE"]
    })
    return tmp_path


def test_shadow_freezes_exact_three_and_fails_closed(tmp_path):
    root = _fixture_root(tmp_path)
    status = build_status(root)
    assert status["candidate_count"] == 3
    assert status["candidate_source_verified"] is True
    assert status["main_line_comparability_proven"] is False
    assert status["production_promotion_allowed"] is False
    assert all(c["shadow_status"] == "WAITING_FOR_COMPARABLE_FORWARD_DATA" for c in status["candidates"])
    assert all(c["forward_bets"] == 0 for c in status["candidates"])
    assert "ODDSPAPI_MAIN_LINE_MAPPING_NOT_PROVEN" in status["blockers"]


def test_shadow_rejects_catalog_drift(tmp_path):
    root = _fixture_root(tmp_path)
    payload = json.loads((root / "reports/v2_research_candidates.json").read_text())
    payload["candidates"][2]["pattern_id"] = "WRONG"
    _write(root / "reports/v2_research_candidates.json", payload)
    try:
        build_status(root)
    except ValueError as exc:
        assert "does not exactly match" in str(exc)
    else:
        raise AssertionError("catalog drift must fail closed")
