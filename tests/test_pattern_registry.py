import json
from pathlib import Path

from odds_scanner.pattern_registry import build_pattern_registry
from odds_scanner.scanner import scan


def test_registry_only_promotes_global_robust_patterns():
    audit = {
        "engine": "THREE_WAY_CROSS_LEAGUE_AUDIT",
        "source_rows": 1000,
        "split": {"holdout": ["2425"]},
        "patterns": [
            {
                "status": "GLOBAL_ROBUST_RESEARCH_CANDIDATE",
                "market": "AH",
                "pattern": "AH_LINE|H|AH=-0.50",
                "family": "AH_LINE",
                "train_n": 500,
                "validation_n": 200,
                "holdout_n": 100,
                "train_roi": 0.04,
                "validation_roi": 0.03,
                "holdout_roi": 0.02,
                "q_validation_bh": 0.05,
                "cross_league_holdout": {"stable": True},
            },
            {
                "status": "WATCHLIST",
                "market": "AH",
                "pattern": "AH_LINE|A|AH=+0.00",
                "family": "AH_LINE",
                "train_n": 500,
                "validation_n": 200,
                "holdout_n": 100,
                "train_roi": 0.04,
                "validation_roi": 0.03,
                "holdout_roi": 0.02,
                "q_validation_bh": 0.50,
                "cross_league_holdout": {"stable": False},
            },
        ],
    }
    registry = build_pattern_registry(audit)
    assert registry["pattern_count"] == 1
    assert registry["patterns"][0]["pattern"] == "AH_LINE|H|AH=-0.50"


def test_scanner_fails_closed_when_registry_is_empty(tmp_path: Path):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "pattern_registry.json").write_text(json.dumps({"patterns": [], "pattern_count": 0}), encoding="utf-8")
    out = scan(tmp_path)
    assert out["status"] == "NO_VALIDATED_PATTERNS"
    assert out["qualifying"] == 0
    assert out["candidates"] == []
    assert out["message"] == "NO QUALIFYING BETS"
