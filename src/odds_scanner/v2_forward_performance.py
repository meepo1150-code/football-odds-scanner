from __future__ import annotations

import hashlib
import json
import random
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .asian_settlement import settle_asian_handicap, settle_asian_total

ENTRIES_PATH = Path("data/normalized/v2_forward_entries.jsonl")
RESULTS_PATH = Path("data/normalized/oddspapi_finished_results.jsonl")
SETTLEMENTS_PATH = Path("data/normalized/v2_forward_settlements.jsonl")
REPORT_PATH = Path("reports/v2_forward_performance.json")
BOOTSTRAP_ITERATIONS = 10_000


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _valid_score(row: dict) -> tuple[int, int] | None:
    try:
        home = int(row.get("ft_home_goals"))
        away = int(row.get("ft_away_goals"))
    except (TypeError, ValueError):
        return None
    if home < 0 or away < 0:
        return None
    return home, away


def _result_index(rows: list[dict]) -> tuple[dict[str, dict], set[str]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        fixture_id = str(row.get("fixture_id") or "")
        if fixture_id and _valid_score(row) is not None:
            grouped[fixture_id].append(row)

    index: dict[str, dict] = {}
    ambiguous: set[str] = set()
    for fixture_id, items in grouped.items():
        scores = {_valid_score(x) for x in items}
        if len(scores) != 1:
            ambiguous.add(fixture_id)
            continue
        # Exact fixture_id is the only join key. Multiple identical score records are harmless.
        index[fixture_id] = items[-1]
    return index, ambiguous


def settle_entry(entry: dict, result: dict) -> dict:
    fixture_id = str(entry.get("fixture_id") or "")
    if fixture_id != str(result.get("fixture_id") or ""):
        raise ValueError("Settlement requires exact fixture_id identity")
    score = _valid_score(result)
    if score is None:
        raise ValueError("Result score is unavailable")
    home_goals, away_goals = score
    try:
        line = float(entry.get("entry_line"))
        price = float(entry.get("entry_price"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Entry line/price invalid") from exc
    if price <= 1.0:
        raise ValueError("Entry price must be decimal odds > 1")

    market = str(entry.get("market") or "").upper()
    selection = str(entry.get("selection") or "").upper()
    if market == "AH":
        settled = settle_asian_handicap(home_goals, away_goals, line, price, selection)
    elif market == "OU":
        settled = settle_asian_total(home_goals, away_goals, line, price, selection)
    else:
        raise ValueError(f"Unsupported forward market: {market}")

    return {
        "candidate_id": entry.get("candidate_id"),
        "fixture_id": fixture_id,
        "league": entry.get("league"),
        "kickoff": entry.get("kickoff"),
        "entry_observed_at": entry.get("entry_observed_at"),
        "market": market,
        "selection": selection,
        "entry_line": line,
        "entry_price": price,
        "ft_home_goals": home_goals,
        "ft_away_goals": away_goals,
        "settlement": settled.settlement.value,
        "profit_units": settled.profit_units,
        "return_units": settled.return_units,
        "stake_units": 1.0,
        "result_source": result.get("result_source"),
        "result_identity": result.get("result_identity"),
        "result_join": "EXACT_ODDSPAPI_FIXTURE_ID_ONLY",
        "paper_label": "PAPER_RESEARCH_ONLY",
        "production_eligible": False,
    }


def _bootstrap_ci95(profits: list[float], candidate_id: str) -> tuple[float | None, float | None]:
    if not profits:
        return None, None
    if len(profits) == 1:
        return profits[0], profits[0]
    seed = int(hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    n = len(profits)
    estimates = []
    for _ in range(BOOTSTRAP_ITERATIONS):
        estimates.append(sum(profits[rng.randrange(n)] for _ in range(n)) / n)
    estimates.sort()
    lo = estimates[int(0.025 * (BOOTSTRAP_ITERATIONS - 1))]
    hi = estimates[int(0.975 * (BOOTSTRAP_ITERATIONS - 1))]
    return lo, hi


def _drawdown(profits: list[float]) -> float | None:
    if not profits:
        return None
    equity = 0.0
    peak = 0.0
    worst = 0.0
    for p in profits:
        equity += p
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
    return worst


def _longest_losing_streak(profits: list[float]) -> int | None:
    if not profits:
        return None
    longest = current = 0
    for p in profits:
        if p < -1e-12:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _candidate_metrics(candidate_id: str, rows: list[dict]) -> dict:
    ordered = sorted(rows, key=lambda r: (str(r.get("kickoff") or ""), str(r.get("fixture_id") or "")))
    profits = [float(r["profit_units"]) for r in ordered]
    total_profit = sum(profits)
    roi = total_profit / len(profits) if profits else None
    lo, hi = _bootstrap_ci95(profits, candidate_id)

    league_profit: dict[str, float] = defaultdict(float)
    league_n: Counter[str] = Counter()
    for row in ordered:
        league = str(row.get("league") or "UNKNOWN")
        league_profit[league] += float(row["profit_units"])
        league_n[league] += 1
    leagues = sorted(league_profit)
    positive_leagues = sum(1 for league in leagues if league_profit[league] > 0)
    positive_share = positive_leagues / len(leagues) if leagues else None
    abs_denominator = sum(abs(x) for x in league_profit.values())
    concentration = max((abs(x) for x in league_profit.values()), default=0.0) / abs_denominator if abs_denominator > 1e-12 else None

    return {
        "settled_entries": len(ordered),
        "total_profit_units": total_profit,
        "roi": roi,
        "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
        "bootstrap_roi_ci95_lower": lo,
        "bootstrap_roi_ci95_upper": hi,
        "distinct_leagues": len(leagues),
        "positive_leagues": positive_leagues,
        "positive_league_share": positive_share,
        "max_single_league_share_of_absolute_profit": concentration,
        "league_concentration_definition": "max(abs(net league profit)) / sum(abs(net league profit))",
        "max_drawdown_units": _drawdown(profits),
        "longest_losing_streak": _longest_losing_streak(profits),
        "losing_streak_definition": "consecutive settled entries with profit_units < 0; push/non-loss resets streak",
        "settlement_counts": dict(sorted(Counter(str(r.get("settlement")) for r in ordered).items())),
        "league_breakdown": {
            league: {
                "settled_entries": int(league_n[league]),
                "profit_units": league_profit[league],
                "roi": league_profit[league] / league_n[league],
            }
            for league in leagues
        },
    }


def build_forward_performance(root: Path = Path(".")) -> dict:
    generated_at = datetime.now(timezone.utc).isoformat()
    entries = _jsonl(root / ENTRIES_PATH)
    result_rows = _jsonl(root / RESULTS_PATH)
    results, ambiguous_results = _result_index(result_rows)

    settled: list[dict] = []
    invalid_entries = 0
    missing_results = 0
    ambiguous_result_entries = 0
    for entry in entries:
        fixture_id = str(entry.get("fixture_id") or "")
        if fixture_id in ambiguous_results:
            ambiguous_result_entries += 1
            continue
        result = results.get(fixture_id)
        if result is None:
            missing_results += 1
            continue
        try:
            settled.append(settle_entry(entry, result))
        except ValueError:
            invalid_entries += 1

    settlements_path = root / SETTLEMENTS_PATH
    settlements_path.parent.mkdir(parents=True, exist_ok=True)
    settlements_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in settled),
        encoding="utf-8",
    )

    candidate_ids = sorted({str(e.get("candidate_id")) for e in entries if e.get("candidate_id")})
    by_candidate = {
        candidate_id: _candidate_metrics(candidate_id, [r for r in settled if str(r.get("candidate_id")) == candidate_id])
        for candidate_id in candidate_ids
    }
    for candidate_id in candidate_ids:
        entry_n = sum(1 for e in entries if str(e.get("candidate_id")) == candidate_id)
        by_candidate[candidate_id]["entries_recorded"] = entry_n
        by_candidate[candidate_id]["unsettled_entries"] = entry_n - by_candidate[candidate_id]["settled_entries"]

    if not entries:
        status = "NO_FORWARD_ENTRIES"
    elif not settled:
        status = "WAITING_FOR_EXACT_RESULTS"
    else:
        status = "FORWARD_PERFORMANCE_AVAILABLE"

    payload = {
        "schema_version": "1.0",
        "classification": "VALIDATION_V2_FORWARD_PERFORMANCE",
        "status": status,
        "generated_at": generated_at,
        "entry_rows": len(entries),
        "settled_entries": len(settled),
        "missing_result_entries": missing_results,
        "ambiguous_result_entries": ambiguous_result_entries,
        "invalid_entry_rows": invalid_entries,
        "result_join": "EXACT_ODDSPAPI_FIXTURE_ID_ONLY",
        "fuzzy_result_join_allowed": False,
        "result_rows_seen": len(result_rows),
        "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
        "by_candidate": by_candidate,
        "paper_label": "PAPER_RESEARCH_ONLY",
        "production_promotion_allowed": False,
    }
    report = root / REPORT_PATH
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_forward_performance(), ensure_ascii=False))
