import json
from pathlib import Path

from odds_scanner.pattern_registry import build_pattern_registry
from odds_scanner.scanner import scan


def _robust_pattern():
    dist = {"FULL_WIN": 60, "HALF_WIN": 5, "PUSH": 5, "HALF_LOSS": 5, "FULL_LOSS": 25}
    return {
        "status": "GLOBAL_ROBUST_RESEARCH_CANDIDATE",
        "market": "AH",
        "pattern": "AH_LINE|H|AH=-0.50",
        "pattern_key": {"family": "AH_LINE", "favorite_side": "H", "ah_line": -0.5},
        "family": "AH_LINE",
        "train_n": 500,
        "validation_n": 200,
        "holdout_n": 100,
        "train_roi": 0.04,
        "validation_roi": 0.03,
        "holdout_roi": 0.02,
        "settlement_distributions": {"train": dist, "validation": dist, "holdout": dist},
        "q_validation_bh": 0.05,
        "cross_league_holdout": {"stable": True},
    }


def test_registry_only_promotes_global_robust_patterns():
    watchlist = {**_robust_pattern(), "status": "WATCHLIST", "pattern": "AH_LINE|A|AH=+0.00", "q_validation_bh": 0.50, "cross_league_holdout": {"stable": False}}
    audit = {
        "engine": "THREE_WAY_CROSS_LEAGUE_AUDIT",
        "source_rows": 1000,
        "split": {"holdout": ["2425"]},
        "patterns": [_robust_pattern(), watchlist],
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


def test_scanner_requires_true_current_provider_when_registry_has_patterns(tmp_path: Path):
    reports = tmp_path / "reports"
    reports.mkdir()
    registry = build_pattern_registry({
        "engine": "THREE_WAY_CROSS_LEAGUE_AUDIT",
        "source_rows": 1000,
        "split": {"holdout": ["2425"]},
        "patterns": [_robust_pattern()],
    })
    (reports / "pattern_registry.json").write_text(json.dumps(registry), encoding="utf-8")
    out = scan(tmp_path)
    assert out["status"] == "CURRENT_TRADABLE_PROVIDER_REQUIRED"
    assert out["matches_scanned"] == 0
    assert out["qualifying"] == 0
    assert out["message"] == "NO QUALIFYING BETS"
    assert "Opening-only snapshots are not accepted" in out["reason"]
