import json
from pathlib import Path

from odds_scanner.v2_forward_entries import build_forward_entries


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _candidate(pid: str, line: float) -> dict:
    return {
        "pattern_id": pid,
        "universe": "BIG5_AH",
        "market": "AH",
        "pattern_key": {
            "favorite_side": "H",
            "ah_line": line,
            "ah_price_band": [1.8, 2.0],
            "favorite_probability_band": [0.4, 0.5] if line == -0.5 else [0.6, 0.7],
        },
    }


def _inputs(root: Path) -> None:
    ids = ["FD_AH_4E30F9F2EC34", "FD_AH_1D65F429F6A5", "FD_OU25_D0A17AE7DB9C"]
    _write(root / "reports/v2_forward_preregistration.json", {"created_at": "2026-09-10T10:03:00Z", "candidate_ids": ids})
    _write(root / "reports/v2_research_candidates.json", {"candidates": [
        _candidate(ids[0], -0.5),
        _candidate(ids[1], -1.25),
        {
            "pattern_id": ids[2], "universe": "THIRD_UNIVERSE_OU", "market": "OU",
            "pattern_key": {"favorite_side": "H", "ah_line": -0.25, "ou_side": "U", "ou_line": 2.5, "ou_price_band": [1.8, 2.0], "favorite_probability_band": [0.4, 0.5]},
        },
    ]})


def _snapshot(observed_at: str, price: float = 1.90) -> dict:
    return {
        "fixture_id": "fx1", "universe": "BIG5_AH", "league": "Premier League", "country": "England",
        "kickoff": "2026-09-11T12:00:00Z", "home": "Home", "away": "Away", "bookmaker": "bet365",
        "observed_at": observed_at, "source_semantics": "CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED", "mainline_verified": True,
        "favorite_side": "H", "favorite_fair_probability": 0.45,
        "ah": {"selected_side_line": -0.5, "selected_side_price": price},
        "ou": {"line": 2.5, "under_price": 1.91, "over_price": 1.95},
    }


def test_first_post_prereg_qualifying_snapshot_becomes_entry(tmp_path):
    _inputs(tmp_path)
    _jsonl(tmp_path / "data/normalized/v2_mainline_snapshots.jsonl", [
        _snapshot("2026-09-10T10:02:00Z", 1.85),
        _snapshot("2026-09-10T10:04:00Z", 1.90),
        _snapshot("2026-09-10T16:04:00Z", 1.95),
    ])
    status = build_forward_entries(tmp_path)
    rows = [json.loads(x) for x in (tmp_path / "data/normalized/v2_forward_entries.jsonl").read_text().splitlines()]
    assert status["entries_total"] == 1
    assert rows[0]["entry_observed_at"] == "2026-09-10T10:04:00Z"
    assert rows[0]["entry_price"] == 1.90
    assert rows[0]["production_eligible"] is False


def test_existing_entry_is_not_rewritten_by_later_or_newly_arriving_snapshot(tmp_path):
    _inputs(tmp_path)
    path = tmp_path / "data/normalized/v2_mainline_snapshots.jsonl"
    _jsonl(path, [_snapshot("2026-09-10T10:10:00Z", 1.90)])
    build_forward_entries(tmp_path)
    _jsonl(path, [
        _snapshot("2026-09-10T10:05:00Z", 1.88),
        _snapshot("2026-09-10T10:10:00Z", 1.90),
        _snapshot("2026-09-10T16:10:00Z", 1.99),
    ])
    status = build_forward_entries(tmp_path)
    row = json.loads((tmp_path / "data/normalized/v2_forward_entries.jsonl").read_text().splitlines()[0])
    assert status["entries_added_this_run"] == 0
    assert row["entry_observed_at"] == "2026-09-10T10:10:00Z"
    assert row["entry_price"] == 1.90


def test_catalog_drift_fails_closed(tmp_path):
    _inputs(tmp_path)
    prereg = json.loads((tmp_path / "reports/v2_forward_preregistration.json").read_text())
    prereg["candidate_ids"].append("UNREGISTERED")
    _write(tmp_path / "reports/v2_forward_preregistration.json", prereg)
    status = build_forward_entries(tmp_path)
    assert status["status"] == "PREREGISTRATION_DRIFT"
    assert status["production_promotion_allowed"] is False
