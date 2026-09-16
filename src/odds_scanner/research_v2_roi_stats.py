from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

OUTCOMES = Path("data/normalized/research_v2_pattern_outcomes.jsonl")
REPORT = Path("reports/research_v2_roi_statistics.json")


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _profit(settlement: str, price: float) -> float | None:
    if price <= 1.0:
        return None
    return {
        "FULL_WIN": price - 1.0,
        "HALF_WIN": (price - 1.0) / 2.0,
        "PUSH": 0.0,
        "HALF_LOSS": -0.5,
        "FULL_LOSS": -1.0,
    }.get(settlement)


def _aggregate(rows: list[dict], keys: list[str]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        price = _num(row.get("ah_price"))
        profit = _profit(str(row.get("favorite_ah_settlement")), price) if price is not None else None
        if profit is None:
            continue
        groups[tuple(str(row.get(k, "UNKNOWN")) for k in keys)].append((row, profit))
    result = []
    for values, items in groups.items():
        n = len(items)
        profit = sum(x[1] for x in items)
        result.append({
            **dict(zip(keys, values)),
            "n": n,
            "favorite_flat_stake_profit_units": round(profit, 4),
            "favorite_flat_stake_roi_pct": round(100.0 * profit / n, 2) if n else None,
            "average_decimal_price": round(sum(float(x[0]["ah_price"]) for x in items) / n, 4),
            "research_only": True,
        })
    return sorted(result, key=lambda x: (-x["n"], str(x)))


def build(root: Path = Path(".")) -> dict:
    rows = [r for r in _rows(root / OUTCOMES) if r.get("ah_core_price") is True]
    payload = {
        "schema_version": "1.0",
        "classification": "RESEARCH_V2_AH_FLAT_STAKE_ROI_STATISTICS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "recommendation_semantics": False,
        "stake_definition": "1 unit on favorite at observed AH decimal price",
        "settlement_profit_units": {"FULL_WIN": "price-1", "HALF_WIN": "(price-1)/2", "PUSH": 0, "HALF_LOSS": -0.5, "FULL_LOSS": -1},
        "core_ah_decimal_odds_range": [1.80, 2.20],
        "settled_core_rows": len(rows),
        "by_side_line_price": _aggregate(rows, ["market_side", "ah_line", "ah_price_bucket"]),
        "by_side_line_price_movement": _aggregate(rows, ["market_side", "ah_line", "ah_price_bucket", "movement"]),
        "by_line_price": _aggregate(rows, ["ah_line", "ah_price_bucket"]),
        "warning": "Descriptive historical ROI only. Small samples and repeated research inspection can create false signals; not a validated betting edge.",
    }
    path = root / REPORT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
