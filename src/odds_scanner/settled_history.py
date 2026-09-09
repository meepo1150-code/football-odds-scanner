from __future__ import annotations

import json
from pathlib import Path
from .asian_settlement import settle_asian_handicap, settle_asian_total

INPUT = Path("data/normalized/oddspapi_prematch_joined.jsonl")
OUTPUT = Path("data/normalized/oddspapi_settled_history.jsonl")
REPORT = Path("reports/oddspapi_settled_history.json")
SEMANTICS = "STRICT_PREMATCH_CREATED_AT_LT_KICKOFF"


def _pack(x):
    return {
        "settlement": x.settlement.value,
        "profit_units": round(x.profit_units, 8),
        "return_units": round(x.return_units, 8),
    }


def _snapshot(side: dict | None, stage: str) -> tuple[float, str] | None:
    if not isinstance(side, dict):
        return None
    prefix = "opening" if stage == "OPENING" else "closing"
    price, quote_at = side.get(f"{prefix}_price"), side.get(f"{prefix}_at")
    if not isinstance(price, (int, float)) or float(price) <= 1 or not isinstance(quote_at, str):
        return None
    return float(price), quote_at


def _fair_share(price: float, opposite: float) -> float:
    a, b = 1.0 / price, 1.0 / opposite
    return round(a / (a + b), 8)


def _base(row: dict) -> dict:
    return {
        "fixture_id": row.get("fixture_id"),
        "league": row.get("league"),
        "kickoff": row.get("kickoff"),
        "home": row.get("home"),
        "away": row.get("away"),
        "bookmaker": row.get("bookmaker"),
        "ft_home_goals": int(row["ft_home_goals"]),
        "ft_away_goals": int(row["ft_away_goals"]),
        "result_source": row.get("result_source"),
        "source_semantics": row.get("snapshot_semantics") or SEMANTICS,
        "promotion_eligible": False,
    }


def _emit_pair(row: dict, market_type: str, line: float, left_name: str, right_name: str,
               left: dict | None, right: dict | None, out: list[dict]) -> None:
    if not isinstance(line, (int, float)):
        return
    line = float(line)
    for stage in ("OPENING", "CLOSING_PREMATCH"):
        ls, rs = _snapshot(left, stage), _snapshot(right, stage)
        if not ls or not rs:
            continue
        for selection, snap, opposite in ((left_name, ls, rs), (right_name, rs, ls)):
            price, quote_at = snap
            opposite_price = opposite[0]
            try:
                if market_type == "AH":
                    selected_line = line if selection == "H" else -line
                    settled = settle_asian_handicap(
                        int(row["ft_home_goals"]), int(row["ft_away_goals"]), selected_line, price, selection
                    )
                else:
                    selected_line = line
                    settled = settle_asian_total(
                        int(row["ft_home_goals"]), int(row["ft_away_goals"]), line, price, selection
                    )
            except (ValueError, TypeError):
                continue
            out.append({
                **_base(row),
                "market_type": market_type,
                "line": line,
                "selected_side_line": selected_line,
                "selection": selection,
                "snapshot_stage": stage,
                "price": price,
                "quote_at": quote_at,
                "opposite_side_price": opposite_price,
                "two_way_fair_share": _fair_share(price, opposite_price),
                **_pack(settled),
            })


def settle_row(row: dict) -> list[dict]:
    """Expand one joined strict-prematch fixture into canonical settled observations."""
    if "ft_home_goals" not in row or "ft_away_goals" not in row:
        return []
    observations: list[dict] = []
    for market in row.get("asian_handicap") or []:
        if isinstance(market, dict):
            _emit_pair(row, "AH", market.get("line"), "H", "A", market.get("home"), market.get("away"), observations)
    for market in row.get("over_under") or []:
        if isinstance(market, dict):
            _emit_pair(row, "OU", market.get("line"), "O", "U", market.get("over"), market.get("under"), observations)
    return observations


def write_settled(root: Path = Path(".")) -> dict:
    observations: list[dict] = []
    joined_rows = 0
    p = root / INPUT
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and "ft_home_goals" in row and "ft_away_goals" in row:
                joined_rows += 1
                observations.extend(settle_row(row))

    out = root / OUTPUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in observations), encoding="utf-8")

    fixtures = len({str(r.get("fixture_id")) for r in observations})
    report = {
        "schema_version": "1.1",
        "classification": "EXPLORATORY_SETTLEMENT_QA_ONLY",
        "source_semantics": SEMANTICS,
        "joined_rows": joined_rows,
        "settled_fixtures": fixtures,
        "settled_observations": len(observations),
        "ah_observations": sum(r["market_type"] == "AH" for r in observations),
        "ou_observations": sum(r["market_type"] == "OU" for r in observations),
        "opening_observations": sum(r["snapshot_stage"] == "OPENING" for r in observations),
        "closing_prematch_observations": sum(r["snapshot_stage"] == "CLOSING_PREMATCH" for r in observations),
        "promotion_allowed": False,
        "promotion_blockers": ["ODDSPAPI_HISTORY_NOT_MULTI_SEASON", "FROZEN_VALIDATION_NOT_RUN"],
    }
    rp = root / REPORT
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
