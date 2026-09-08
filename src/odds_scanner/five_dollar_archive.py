from __future__ import annotations

import json
import os
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from .five_dollar_history import normalize_finished_snapshot
from .five_dollar_provider import ENV_KEY, _get

ARCHIVE_PATH = Path("data/normalized/five_dollar_snapshots.jsonl")
STATE_PATH = Path("reports/five_dollar_archive_state.json")
ATTRIBUTION = "Football data by 5DollarFootballAPI — https://5dollarfootballapi.com/"
FREE_HISTORY_DAYS = 90
DEFAULT_REQUEST_BUDGET = 50  # leave headroom below the documented 60 req/hour free limit


def _unix_day_window(day: date) -> tuple[int, int]:
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1) - timedelta(seconds=1)
    return int(start.timestamp()), int(end.timestamp())


def _read_archive(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        fixture_id = str(row.get("fixture_id") or "")
        if fixture_id:
            rows[fixture_id] = row
    return rows


def _write_archive(path: Path, rows: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows.values(), key=lambda r: (r.get("date", ""), r.get("fixture_id", "")))
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in ordered)
    path.write_text(text, encoding="utf-8")


def _load_state(path: Path, *, today: date) -> dict:
    if path.exists():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            if state.get("next_date"):
                return state
        except (ValueError, TypeError):
            pass
    # Free history is documented as the last 3 months. Start conservatively at 89 days back.
    return {
        "schema_version": "1.0",
        "next_date": (today - timedelta(days=89)).isoformat(),
        "completed_through": None,
        "cycles_completed": 0,
    }


def collect_one_day(
    root: Path,
    *,
    key: str | None = None,
    today: date | None = None,
    request_budget: int = DEFAULT_REQUEST_BUDGET,
) -> dict:
    """Collect one UTC day of finished Big-5 snapshot odds without storing raw API payloads.

    The free key only exposes Big-5 data. We deliberately process one day per run so the
    per-fixture odds calls remain comfortably inside the free hourly request budget.
    """
    api_key = key or os.getenv(ENV_KEY)
    if not api_key:
        raise RuntimeError(f"{ENV_KEY} is not configured")
    current_day = today or datetime.now(timezone.utc).date()
    state_path = root / STATE_PATH
    archive_path = root / ARCHIVE_PATH
    state = _load_state(state_path, today=current_day)
    target = date.fromisoformat(state["next_date"])
    latest_finished_day = current_day - timedelta(days=1)

    # Once caught up, roll the cursor to yesterday so future runs refresh the newest day.
    if target > latest_finished_day:
        target = latest_finished_day

    start_ts, end_ts = _unix_day_window(target)
    fixture_payload = _get(
        "/fixtures",
        api_key,
        {"status": "finished", "start_time": start_ts, "end_time": end_ts, "per_page": 50},
    )
    requests_used = 1
    fixtures = fixture_payload.get("data") or []
    existing = _read_archive(archive_path)
    added = 0
    skipped = 0
    errors: list[str] = []

    for fixture in fixtures:
        fixture_id = str(fixture.get("id") or "")
        if not fixture_id:
            skipped += 1
            continue
        # A day can occasionally be busy; never cross our own conservative budget.
        if requests_used >= request_budget:
            errors.append("REQUEST_BUDGET_EXHAUSTED")
            break
        try:
            odds_payload = _get(f"/fixtures/{fixture_id}/odds", api_key)
            requests_used += 1
            row = normalize_finished_snapshot(fixture, odds_payload)
            existing[fixture_id] = row
            added += 1
        except Exception as exc:
            skipped += 1
            errors.append(f"{fixture_id}:{type(exc).__name__}:{exc}")

    _write_archive(archive_path, existing)

    day_complete = "REQUEST_BUDGET_EXHAUSTED" not in errors
    next_date = target + timedelta(days=1) if day_complete else target
    if target >= latest_finished_day and day_complete:
        # Stay near the frontier; the next scheduled run will refresh the latest completed day.
        next_date = current_day
        state["cycles_completed"] = int(state.get("cycles_completed") or 0) + 1

    state.update(
        {
            "schema_version": "1.1",
            "provider": "5dollarfootballapi_free",
            "attribution": ATTRIBUTION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "processed_date": target.isoformat(),
            "next_date": next_date.isoformat(),
            "completed_through": target.isoformat() if day_complete else state.get("completed_through"),
            "fixtures_seen": len(fixtures),
            "rows_added_or_refreshed": added,
            "rows_total": len(existing),
            "requests_used": requests_used,
            "request_budget": request_budget,
            "skipped": skipped,
            "errors": errors[:20],
            "raw_payloads_stored": False,
            "snapshot_semantics": "OPENING_AND_LATEST_OR_FINAL_PREMATCH_ONLY_NO_TICKS",
        }
    )
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def main() -> None:
    root = Path(".")
    try:
        result = collect_one_day(root)
    except Exception as exc:
        result = {
            "schema_version": "1.1",
            "provider": "5dollarfootballapi_free",
            "status": "UNAVAILABLE",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "error": f"{type(exc).__name__}: {exc}",
            "raw_payloads_stored": False,
            "attribution": ATTRIBUTION,
        }
        path = root / STATE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        raise
    print(result)


if __name__ == "__main__":
    main()
