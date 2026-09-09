from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import oddspapi_history_archive as base
from .oddspapi_history_store import append_row, archived_fixture_ids

# Preserve the established normalization/discovery contract while changing only
# durable tick storage. Existing callers/tests can keep using the legacy module.
HISTORY_START = base.HISTORY_START
HISTORY_REQUEST_SPACING_SECONDS = base.HISTORY_REQUEST_SPACING_SECONDS
DEFAULT_FIXTURES_PER_RUN = base.DEFAULT_FIXTURES_PER_RUN
STATE_PATH = base.STATE_PATH
CATALOG_PATH = base.CATALOG_PATH
BIG5_TOURNAMENTS = base.BIG5_TOURNAMENTS
ENV_KEY = base.ENV_KEY

_rows = base._rows
_iso = base._iso
_utc = base._utc
_read_json = base._read_json
_catalog_payload = base._catalog_payload
_compact_fixture = base._compact_fixture
normalize_historical_fixture = base.normalize_historical_fixture
next_discovery_window = base.next_discovery_window
_get = base._get
_discover_window = base._discover_window


def run_archive(
    root: Path,
    *,
    max_fixtures: int = DEFAULT_FIXTURES_PER_RUN,
    now_fn: Callable[[], datetime] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict:
    """Archive historical ticks without growing the legacy monolithic JSONL.

    The existing 51MB legacy file remains read-only for backward compatibility.
    Every new normalized fixture is appended to a UTC-day shard under
    data/normalized/oddspapi_history_ticks/. Archived-id checks span both the
    legacy file and all shards, so no fixture is rediscovered merely because of
    the storage transition.
    """
    now = (now_fn or (lambda: datetime.now(timezone.utc)))()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    state_path = root / STATE_PATH
    catalog_path = root / CATALOG_PATH
    state = _read_json(state_path, {})
    key = os.getenv(ENV_KEY)
    if not key:
        payload = {
            "schema_version": "1.2",
            "status": "API_KEY_NOT_CONFIGURED",
            "generated_at": now.isoformat(),
            "promotion_eligible": False,
            "result_join_status": "NOT_JOINED",
            "history_storage": "LEGACY_PLUS_DAILY_SHARDS",
        }
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    billable_requests = 0
    fixture_queue = state.get("fixture_queue") if isinstance(state.get("fixture_queue"), list) else []
    discovery_mode = None
    discovery_start = None
    discovery_end = None
    window = next_discovery_window(state, now)
    if window is not None:
        start, end, discovery_mode = window
        discovered = _discover_window(key, start, end)
        billable_requests += 1
        archived = archived_fixture_ids(root)
        skipped = {str(x) for x in (state.get("skipped_fixture_ids") or [])}
        fixture_queue = [f for f in discovered if str(f.get("fixtureId")) not in archived | skipped]
        discovery_start, discovery_end = _iso(start), _iso(end)
        state["last_discovery_at"] = now.isoformat()
        if discovery_mode == "BACKFILL":
            state["discovery_cursor"] = end.isoformat()
            if end >= now:
                state["backfill_complete"] = True

    if catalog_path.exists():
        markets_catalog = _read_json(catalog_path, [])
    else:
        markets_catalog = _catalog_payload(_rows(_get("/markets", key, {"language": "en"})))
        billable_requests += 1
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        catalog_path.write_text(json.dumps(markets_catalog, ensure_ascii=False), encoding="utf-8")

    processed = 0
    added = 0
    history_requests = 0
    errors: list[str] = []
    skipped_ids = {str(x) for x in (state.get("skipped_fixture_ids") or [])}
    remaining = list(fixture_queue)
    touched_shards: set[str] = set()
    while remaining and processed < max(1, max_fixtures):
        fixture = remaining.pop(0)
        if history_requests:
            sleep_fn(HISTORY_REQUEST_SPACING_SECONDS)
        fid = str(fixture.get("fixtureId"))
        history_requests += 1
        try:
            history = _get("/historical-odds", key, {"fixtureId": fid, "bookmakers": "bet365", "language": "en"})
            row = normalize_historical_fixture(fixture, history, markets_catalog)
            if row:
                path = append_row(root, row)
                try:
                    touched_shards.add(str(path.relative_to(root)))
                except ValueError:
                    touched_shards.add(str(path))
                added += 1
            else:
                skipped_ids.add(fid)
        except Exception as exc:
            errors.append(f"{fid}:{type(exc).__name__}:{exc}")
            remaining.append(fixture)
        processed += 1

    archive_rows = len(archived_fixture_ids(root))
    payload = {
        "schema_version": "1.2",
        "status": "OK" if not errors else "PARTIAL_WITH_ERRORS",
        "generated_at": now.isoformat(),
        "coverage_start": HISTORY_START.isoformat(),
        "last_discovery_at": state.get("last_discovery_at"),
        "discovery_cursor": state.get("discovery_cursor", HISTORY_START.isoformat()),
        "backfill_complete": state.get("backfill_complete") is True,
        "last_discovery_mode": discovery_mode,
        "last_discovery_window": {"from": discovery_start, "to": discovery_end} if discovery_start else None,
        "fixture_queue": remaining,
        "skipped_fixture_ids": sorted(skipped_ids),
        "queued_remaining": len(remaining),
        "processed_this_run": processed,
        "rows_added_this_run": added,
        "archive_rows": archive_rows,
        "history_storage": "LEGACY_PLUS_DAILY_SHARDS",
        "touched_shards": sorted(touched_shards),
        "billable_requests_this_run": billable_requests,
        "free_history_requests_this_run": history_requests,
        "history_request_spacing_seconds": HISTORY_REQUEST_SPACING_SECONDS,
        "result_join_status": "NOT_JOINED",
        "promotion_eligible": False,
        "promotion_blockers": [
            "MATCH_RESULTS_NOT_JOINED",
            "ODDSPAPI_HISTORY_STARTS_2026_AND_IS_NOT_YET_MULTI_SEASON",
        ],
        "errors": errors[:10],
    }
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
