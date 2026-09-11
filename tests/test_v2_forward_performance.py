import json
from pathlib import Path

from odds_scanner.v2_forward_performance import build_forward_performance, settle_entry


def _jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")


def _entry(fixture_id="fx1", market="AH", selection="H", line=-0.75, price=2.0, candidate="C1", league="L1", kickoff="2026-09-11T12:00:00Z"):
    return {"candidate_id": candidate, "fixture_id": fixture_id, "league": league, "kickoff": kickoff, "entry_observed_at": "2026-09-10T13:30:00Z", "market": market, "selection": selection, "entry_line": line, "entry_price": price}


def _result(fixture_id="fx1", home=1, away=0):
    return {"fixture_id": fixture_id, "ft_home_goals": home, "ft_away_goals": away, "result_source": "EXACT_RESULT", "result_identity": "EXACT_FIXTURE_ID"}


def test_quarter_handicap_settlement_is_preserved():
    row = settle_entry(_entry(line=-0.75, price=2.0), _result(home=1, away=0))
    assert row["settlement"] == "HALF_WIN"
    assert row["profit_units"] == 0.5
    assert row["result_join"] == "EXACT_ODDSPAPI_FIXTURE_ID_ONLY"


def test_under_25_settlement():
    row = settle_entry(_entry(market="OU", selection="U", line=2.5, price=1.9), _result(home=1, away=1))
    assert row["settlement"] == "FULL_WIN"
    assert abs(row["profit_units"] - 0.9) < 1e-12


def test_exact_fixture_identity_is_required():
    try:
        settle_entry(_entry(fixture_id="fx1"), _result(fixture_id="fx2"))
        assert False, "expected exact-id failure"
    except ValueError as exc:
        assert "exact fixture_id" in str(exc)


def test_conflicting_duplicate_results_fail_closed(tmp_path):
    _jsonl(tmp_path / "data/normalized/v2_forward_entries.jsonl", [_entry()])
    _jsonl(tmp_path / "data/normalized/oddspapi_finished_results.jsonl", [_result(home=1, away=0), _result(home=0, away=1)])
    out = build_forward_performance(tmp_path)
    assert out["settled_entries"] == 0
    assert out["ambiguous_result_entries"] == 1
    assert out["status"] == "WAITING_FOR_EXACT_RESULTS"


def test_performance_reports_roi_league_stability_drawdown_and_streak(tmp_path):
    entries = [
        _entry("f1", line=-0.5, price=2.0, kickoff="2026-09-11T12:00:00Z", league="L1"),
        _entry("f2", line=-0.5, price=2.0, kickoff="2026-09-12T12:00:00Z", league="L1"),
        _entry("f3", line=-0.5, price=2.0, kickoff="2026-09-13T12:00:00Z", league="L2"),
        _entry("f4", line=-0.5, price=2.0, kickoff="2026-09-14T12:00:00Z", league="L2"),
    ]
    results = [_result("f1", 1, 0), _result("f2", 0, 1), _result("f3", 2, 0), _result("f4", 0, 0)]
    _jsonl(tmp_path / "data/normalized/v2_forward_entries.jsonl", entries)
    _jsonl(tmp_path / "data/normalized/oddspapi_finished_results.jsonl", results)
    out = build_forward_performance(tmp_path)
    c = out["by_candidate"]["C1"]
    assert c["settled_entries"] == 4
    assert c["distinct_leagues"] == 2
    assert c["settlement_counts"]["FULL_WIN"] == 2
    assert c["settlement_counts"]["FULL_LOSS"] == 2
    assert c["roi"] == 0.0
    assert c["max_drawdown_units"] <= -1.0
    assert c["longest_losing_streak"] == 1
    assert c["bootstrap_roi_ci95_lower"] <= c["bootstrap_roi_ci95_upper"]
    assert out["production_promotion_allowed"] is False
