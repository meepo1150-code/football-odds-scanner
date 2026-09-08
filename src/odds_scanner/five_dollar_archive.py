from __future__ import annotations

import json
import os
import time as _time
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from .five_dollar_history import normalize_finished_snapshot
from .five_dollar_provider import ENV_KEY, _get

ARCHIVE_PATH = Path("data/normalized/five_dollar_snapshots.jsonl")
STATE_PATH = Path("reports/five_dollar_archive_state.json")
ATTRIBUTION = "Football data by 5DollarFootballAPI — https://5dollarfootballapi.com/"
FREE_HISTORY_DAYS = 90
DEFAULT_REQUEST_BUDGET = 50
DEFAULT_MAX_DAYS_PER_RUN = 14
DEFAULT_PACE_SECONDS = 3.2  # below the documented 20 requests/minute burst ceiling


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
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in ordered), encoding="utf-8")


def _load_state(path: Path, *, today: date) -> dict:
    if path.exists():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            if state.get("next_date"):
                return state
        except (ValueError, TypeError):
            pass
    return {
        "schema_version": "1.0",
        "next_date": (today - timedelta(days=FREE_HISTORY_DAYS - 1)).isoformat(),
        "completed_through": None,
        "cycles_completed": 0,
    }


def collect_batch(
    root: Path,
    *,
    key: str | None = None,
    today: date | None = None,
    request_budget: int = DEFAULT_REQUEST_BUDGET,
    max_days: int = DEFAULT_MAX_DAYS_PER_RUN,
    pace_seconds: float = DEFAULT_PACE_SECONDS,
    sleep_fn=_time.sleep,
) -> dict:
    """Collect consecutive UTC days of finished Big-5 snapshot odds.

    Raw API responses are never persisted. Calls are paced below the Free/Community
    20-requests-per-minute burst ceiling and total requests are capped per run.
    """
    api_key = key or os.getenv(ENV_KEY)
    if not api_key:
        raise RuntimeError(f"{ENV_KEY} is not configured")
    current_day = today or datetime.now(timezone.utc).date()
    latest_finished_day = current_day - timedelta(days=1)
    state_path = root / STATE_PATH
    archive_path = root / ARCHIVE_PATH
    state = _load_state(state_path, today=current_day)
    target = date.fromisoformat(state["next_date"])
    if target > latest_finished_day:
        target = latest_finished_day

    existing = _read_archive(archive_path)
    requests_used = total_seen = added = skipped = days_completed = 0
    errors: list[str] = []
    processed_dates: list[str] = []
    cursor = target

    def paced_get(path: str, params: dict | None = None):
        nonlocal requests_used
        if requests_used:
            sleep_fn(max(0.0, pace_seconds))
        payload = _get(path, api_key, params)
        requests_used += 1
        return payload

    while cursor <= latest_finished_day and days_completed < max_days:
        if requests_used >= request_budget:
            break
        start_ts, end_ts = _unix_day_window(cursor)
        try:
            fixture_payload = paced_get(
                "/fixtures",
                {"status": "finished", "start_time": start_ts, "end_time": end_ts, "per_page": 50},
            )
        except Exception as exc:
            errors.append(f"{cursor.isoformat()}:FIXTURE_LIST:{type(exc).__name__}:{exc}")
            break

        fixtures = fixture_payload.get("data") or []
        total_seen += len(fixtures)
        if requests_used + len(fixtures) > request_budget:
            errors.append(f"{cursor.isoformat()}:REQUEST_BUDGET_DEFERRED_DAY")
            break

        for fixture in fixtures:
            fixture_id = str(fixture.get("id") or "")
            if not fixture_id:
                skipped += 1
                continue
            try:
                odds_payload = paced_get(f"/fixtures/{fixture_id}/odds")
                existing[fixture_id] = normalize_finished_snapshot(fixture, odds_payload)
                added += 1
            except Exception as exc:
                skipped += 1
                errors.append(f"{fixture_id}:{type(exc).__name__}:{exc}")

        processed_dates.append(cursor.isoformat())
        days_completed += 1
        state["completed_through"] = cursor.isoformat()
        cursor += timedelta(days=1)

    _write_archive(archive_path, existing)
    if cursor > latest_finished_day:
        state["cycles_completed"] = int(state.get("cycles_completed") or 0) + 1
        next_date = current_day
    else:
        next_date = cursor

    state.update(
        {
            "schema_version": "1.3",
            "provider": "5dollarfootballapi_free",
            "attribution": ATTRIBUTION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "processed_dates": processed_dates,
            "next_date": next_date.isoformat(),
            "fixtures_seen": total_seen,
            "rows_added_or_refreshed": added,
            "rows_total": len(existing),
            "requests_used": requests_used,
            "request_budget": request_budget,
            "pace_seconds": pace_seconds,
            "days_completed_this_run": days_completed,
            "max_days_per_run": max_days,
            "skipped": skipped,
            "errors": errors[:40],
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
        result = collect_batch(root)
    except Exception as exc:
        result = {
            "schema_version": "1.3",
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
