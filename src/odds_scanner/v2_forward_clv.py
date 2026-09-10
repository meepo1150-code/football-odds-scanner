from __future__ import annotations

import json
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ENTRIES_PATH = Path("data/normalized/v2_forward_entries.jsonl")
SNAPSHOTS_PATH = Path("data/normalized/v2_mainline_snapshots.jsonl")
REPORT_PATH = Path("reports/v2_forward_clv_status.json")


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


def _utc(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def _selection_quote(entry: dict, snap: dict) -> tuple[float | None, float | None]:
    market = entry.get("market")
    if market == "AH":
        side = entry.get("selection")
        ah = snap.get("ah") or {}
        if side == "H":
            return ah.get("home_line"), ah.get("home_price")
        if side == "A":
            return ah.get("away_line"), ah.get("away_price")
        return None, None
    if market == "OU":
        side = entry.get("selection")
        ou = snap.get("ou") or {}
        if side == "U":
            return ou.get("line"), ou.get("under_price")
        if side == "O":
            return ou.get("line"), ou.get("over_price")
    return None, None


def evaluate_entry_clv(entry: dict, snapshots: list[dict]) -> dict:
    fixture_id = str(entry.get("fixture_id") or "")
    entry_at = _utc(entry.get("entry_observed_at"))
    kickoff = _utc(entry.get("kickoff"))
    if not fixture_id or entry_at is None or kickoff is None:
        return {"status": "ENTRY_INVALID", "clv_comparable": False}

    candidates: list[dict] = []
    for snap in snapshots:
        if str(snap.get("fixture_id") or "") != fixture_id:
            continue
        observed_at = _utc(snap.get("observed_at"))
        if observed_at is None or observed_at < entry_at or observed_at >= kickoff:
            continue
        if snap.get("mainline_verified") is not True:
            continue
        if snap.get("source_semantics") != "CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED":
            continue
        candidates.append(snap)
    candidates.sort(key=lambda r: _utc(r.get("observed_at")) or datetime.min.replace(tzinfo=timezone.utc))
    if not candidates:
        return {
            "status": "NO_ADMISSIBLE_POST_ENTRY_SNAPSHOT",
            "clv_comparable": False,
            "closing_label": "LATEST_OBSERVED_PREMATCH_MAINLINE",
        }

    close = candidates[-1]
    close_line, close_price = _selection_quote(entry, close)
    try:
        entry_line = float(entry.get("entry_line"))
        entry_price = float(entry.get("entry_price"))
        close_line_f = float(close_line)
        close_price_f = float(close_price)
    except (TypeError, ValueError):
        return {
            "status": "CLV_NOT_COMPARABLE",
            "clv_comparable": False,
            "latest_observed_at": close.get("observed_at"),
            "closing_label": "LATEST_OBSERVED_PREMATCH_MAINLINE",
        }

    line_move = close_line_f - entry_line
    base = {
        "latest_observed_at": close.get("observed_at"),
        "latest_line": close_line_f,
        "latest_price": close_price_f,
        "entry_line": entry_line,
        "entry_price": entry_price,
        "line_move": line_move,
        "closing_label": "LATEST_OBSERVED_PREMATCH_MAINLINE",
        "perfect_market_close_claim": False,
    }
    if abs(close_line_f - entry_line) > 1e-9:
        return {
            **base,
            "status": "CLV_NOT_COMPARABLE_LINE_CHANGED",
            "clv_comparable": False,
            "price_clv": None,
        }
    return {
        **base,
        "status": "CLV_COMPARABLE",
        "clv_comparable": True,
        "price_clv": (entry_price / close_price_f) - 1.0,
    }


def build_clv_status(root: Path = Path(".")) -> dict:
    generated_at = datetime.now(timezone.utc)
    entries = _jsonl(root / ENTRIES_PATH)
    snapshots = _jsonl(root / SNAPSHOTS_PATH)
    evaluations: list[dict] = []
    for entry in entries:
        result = evaluate_entry_clv(entry, snapshots)
        evaluations.append({
            "candidate_id": entry.get("candidate_id"),
            "fixture_id": entry.get("fixture_id"),
            "league": entry.get("league"),
            "market": entry.get("market"),
            "selection": entry.get("selection"),
            **result,
        })

    by_candidate: dict[str, dict] = {}
    ids = sorted({str(x.get("candidate_id")) for x in entries if x.get("candidate_id")})
    for candidate_id in ids:
        rows = [x for x in evaluations if str(x.get("candidate_id")) == candidate_id]
        comparable = [float(x["price_clv"]) for x in rows if x.get("clv_comparable") and x.get("price_clv") is not None]
        reasons = Counter(str(x.get("status")) for x in rows)
        by_candidate[candidate_id] = {
            "entries": len(rows),
            "comparable_clv": len(comparable),
            "comparable_share": (len(comparable) / len(rows)) if rows else 0.0,
            "mean_clv": statistics.fmean(comparable) if comparable else None,
            "median_clv": statistics.median(comparable) if comparable else None,
            "statuses": dict(sorted(reasons.items())),
        }

    payload = {
        "schema_version": "1.0",
        "classification": "VALIDATION_V2_FORWARD_CLV_STATUS",
        "status": "NO_FORWARD_ENTRIES" if not entries else "COLLECTING_FORWARD_CLV",
        "generated_at": generated_at.isoformat(),
        "entries": len(entries),
        "snapshots": len(snapshots),
        "comparable_clv": sum(1 for x in evaluations if x.get("clv_comparable")),
        "clv_definition": "entry decimal price / latest-observed same-selection same-line price - 1",
        "line_change_policy": "report line move separately and mark price CLV not comparable when the main line changes",
        "closing_label": "LATEST_OBSERVED_PREMATCH_MAINLINE",
        "perfect_market_close_claim": False,
        "by_candidate": by_candidate,
        "evaluations": evaluations,
        "paper_label": "PAPER_RESEARCH_ONLY",
        "production_promotion_allowed": False,
    }
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_clv_status(), ensure_ascii=False))
