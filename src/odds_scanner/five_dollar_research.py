from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from .asian_settlement import settle_asian_handicap, settle_asian_total
from .five_dollar_archive import ARCHIVE_PATH, ATTRIBUTION
from .hierarchical_backtest import build_hierarchical_report

REPORT_PATH = Path("reports/five_dollar_research.json")
MIN_BACKTEST_ROWS = 20


def load_archive(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _dist(values) -> dict[str, int]:
    c = Counter("NA" if v is None else f"{float(v):.2f}" for v in values)
    return dict(sorted(c.items(), key=lambda kv: kv[0]))


def _is_quarter(line) -> bool:
    if line is None:
        return False
    x = float(line)
    return abs(x * 4 - round(x * 4)) < 1e-8 and abs(x * 2 - round(x * 2)) > 1e-8


def _move_bucket(value, *, market: str) -> str:
    if value is None or abs(float(value)) < 1e-9:
        return "FLAT"
    x = float(value)
    if market == "AH":
        # Favorite-side handicap is normalized to the favorite perspective.
        # More negative means the favorite strengthened (e.g. -0.75 -> -1.00).
        return "FAVORITE_STRENGTHENED" if x < 0 else "FAVORITE_WEAKENED"
    return "TOTAL_UP" if x > 0 else "TOTAL_DOWN"


def _summary(profits: list[float], settlements: list[str]) -> dict:
    n = len(profits)
    return {
        "n": n,
        "roi": round(sum(profits) / n, 6) if n else None,
        "settlements": dict(sorted(Counter(settlements).items())),
    }


def _coarse_diagnostics(rows: list[dict]) -> dict:
    ah: dict[str, dict[str, list]] = defaultdict(lambda: {"profits": [], "settlements": []})
    over: dict[str, dict[str, list]] = defaultdict(lambda: {"profits": [], "settlements": []})
    under: dict[str, dict[str, list]] = defaultdict(lambda: {"profits": [], "settlements": []})

    for r in sorted(rows, key=lambda x: (x.get("date", ""), x.get("fixture_id", ""))):
        try:
            hg, ag = int(r["home_goals"]), int(r["away_goals"])
            ah_set = settle_asian_handicap(
                hg, ag, float(r["favorite_ah_line"]), float(r["favorite_ah_price"]), str(r["favorite_side"])
            )
            ah_key = _move_bucket(r.get("ah_line_move"), market="AH")
            ah[ah_key]["profits"].append(ah_set.profit_units)
            ah[ah_key]["settlements"].append(ah_set.settlement.value)

            ou_key = _move_bucket(r.get("ou_line_move"), market="OU")
            over_set = settle_asian_total(hg, ag, float(r["ou_line"]), float(r["over_price"]), "O")
            under_set = settle_asian_total(hg, ag, float(r["ou_line"]), float(r["under_price"]), "U")
            over[ou_key]["profits"].append(over_set.profit_units)
            over[ou_key]["settlements"].append(over_set.settlement.value)
            under[ou_key]["profits"].append(under_set.profit_units)
            under[ou_key]["settlements"].append(under_set.settlement.value)
        except (KeyError, TypeError, ValueError):
            continue

    def finish(groups):
        return {k: _summary(v["profits"], v["settlements"]) for k, v in sorted(groups.items())}

    return {
        "classification": "DESCRIPTIVE_EXPLORATORY_ONLY",
        "promotion_allowed": False,
        "minimum_n_for_inference": None,
        "favorite_ah_opening_settlement_by_line_move": finish(ah),
        "over_opening_settlement_by_total_line_move": finish(over),
        "under_opening_settlement_by_total_line_move": finish(under),
        "warning": "These coarse groups are descriptive summaries of the short rolling archive. ROI is not a validated edge and cannot enter the production registry.",
    }


def build_report(rows: list[dict]) -> dict:
    dates = sorted(r.get("date") for r in rows if r.get("date"))
    leagues = sorted({str(r.get("division")) for r in rows if r.get("division")})
    ou_open = [r.get("ou_line") for r in rows]
    ou_close = [r.get("closing_ou_line") for r in rows]
    ah_open = [r.get("favorite_ah_line") for r in rows]
    ah_close = [r.get("closing_favorite_ah_line") for r in rows]

    movement_ah = sum(1 for r in rows if r.get("ah_line_move") not in (None, 0, 0.0))
    movement_ou = sum(1 for r in rows if r.get("ou_line_move") not in (None, 0, 0.0))
    quarter_ou_open = sum(_is_quarter(v) for v in ou_open)
    quarter_ou_close = sum(_is_quarter(v) for v in ou_close)
    quarter_ah_open = sum(_is_quarter(v) for v in ah_open)
    quarter_ah_close = sum(_is_quarter(v) for v in ah_close)

    coverage = {
        "rows": len(rows),
        "leagues": leagues,
        "date_min": dates[0] if dates else None,
        "date_max": dates[-1] if dates else None,
        "opening_ou_lines": _dist(ou_open),
        "closing_ou_lines": _dist(ou_close),
        "opening_ah_lines": _dist(ah_open),
        "closing_ah_lines": _dist(ah_close),
        "quarter_ou_open_rows": quarter_ou_open,
        "quarter_ou_close_rows": quarter_ou_close,
        "quarter_ah_open_rows": quarter_ah_open,
        "quarter_ah_close_rows": quarter_ah_close,
        "nonzero_ah_line_movement_rows": movement_ah,
        "nonzero_ou_line_movement_rows": movement_ou,
        "opening_and_closing_ou_complete_rows": sum(
            1
            for r in rows
            if all(r.get(k) is not None for k in ("ou_line", "over_price", "under_price", "closing_ou_line", "closing_over_price", "closing_under_price"))
        ),
        "opening_and_closing_ah_complete_rows": sum(
            1
            for r in rows
            if all(r.get(k) is not None for k in ("favorite_ah_line", "favorite_ah_price", "favorite_ah_other_price", "closing_favorite_ah_line", "closing_favorite_ah_price", "closing_favorite_ah_other_price"))
        ),
    }

    report = {
        "schema_version": "1.1",
        "status": "INSUFFICIENT_SAMPLE" if len(rows) < MIN_BACKTEST_ROWS else "EXPLORATORY_BACKTEST_READY",
        "research_classification": "EXPLORATORY_SNAPSHOT_ONLY",
        "source": "5dollarfootballapi_free",
        "attribution": ATTRIBUTION,
        "promotion_allowed": False,
        "promotion_block_reason": "Free history is a short rolling snapshot archive and cannot satisfy the frozen multi-season train-validation-holdout production gate.",
        "minimum_rows_for_exploratory_backtest": MIN_BACKTEST_ROWS,
        "coverage": coverage,
        "coarse_diagnostics": _coarse_diagnostics(rows),
        "hierarchical": None,
        "warning": "This report is for data-coverage and exploratory pattern research only. It must never overwrite or promote reports/pattern_registry.json.",
    }
    if len(rows) >= MIN_BACKTEST_ROWS:
        report["hierarchical"] = build_hierarchical_report(rows, test_seasons={"__NONE__"}, min_n=MIN_BACKTEST_ROWS)
    return report


def write_report(root: Path) -> dict:
    rows = load_archive(root / ARCHIVE_PATH)
    report = build_report(rows)
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    print(write_report(Path(".")))


if __name__ == "__main__":
    main()
