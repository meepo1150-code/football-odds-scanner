from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from .oddspapi_provider import ENV_KEY, SPORT_ID, _catalog, _get, _outcome_lookup, _quarter

HISTORY_START = datetime(2026, 1, 1, tzinfo=timezone.utc)
DISCOVERY_WINDOW_DAYS = 9
DISCOVERY_REFRESH_DAYS = 7
HISTORY_REQUEST_SPACING_SECONDS = 5.2
DEFAULT_FIXTURES_PER_RUN = 10
STATE_PATH = Path("reports/oddspapi_history_state.json")
ARCHIVE_PATH = Path("data/normalized/oddspapi_history_ticks.jsonl")
CATALOG_PATH = Path("data/normalized/oddspapi_market_catalog.json")

BIG5_TOURNAMENTS = {
    17: {"country": "England", "name": "Premier League"},
    34: {"country": "France", "name": "Ligue 1"},
    35: {"country": "Germany", "name": "Bundesliga"},
    23: {"country": "Italy", "name": "Serie A"},
    8: {"country": "Spain", "name": "LaLiga"},
}


def _utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _rows(payload) -> list[dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("data", "fixtures", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _load_archived_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        fid = row.get("fixture_id")
        if fid is not None:
            ids.add(str(fid))
    return ids


def next_discovery_window(state: dict, now: datetime) -> tuple[datetime, datetime, str] | None:
    """Return one billable discovery window or None.

    During initial backfill, advance one <10-day soccer window only when the
    cached fixture queue is empty. Once caught up, refresh the latest 9 days no
    more than once per week. This bounds historical discovery quota.
    """
    queue = state.get("fixture_queue")
    if isinstance(queue, list) and queue:
        return None

    if state.get("backfill_complete") is not True:
        cursor = _utc(state.get("discovery_cursor")) or HISTORY_START
        if cursor >= now:
            return None
        end = min(cursor + timedelta(days=DISCOVERY_WINDOW_DAYS), now)
        return cursor, end, "BACKFILL"

    last = _utc(state.get("last_discovery_at"))
    if last is not None and now - last < timedelta(days=DISCOVERY_REFRESH_DAYS):
        return None
    start = max(HISTORY_START, now - timedelta(days=DISCOVERY_WINDOW_DAYS))
    return start, now, "REFRESH"


def _catalog_payload(markets: list[dict]) -> list[dict]:
    result = []
    for market in markets:
        if market.get("sportId") != SPORT_ID:
            continue
        if str(market.get("period") or "").lower() != "fulltime":
            continue
        if market.get("playerProp") is True:
            continue
        result.append(market)
    return result


def _tick_list(player_value) -> list[dict]:
    if not isinstance(player_value, list):
        return []
    ticks = []
    for item in player_value:
        if not isinstance(item, dict):
            continue
        price = item.get("price")
        created = item.get("createdAt")
        if not isinstance(price, (int, float)) or float(price) <= 1.0:
            continue
        if not isinstance(created, str) or _utc(created) is None:
            continue
        ticks.append({
            "created_at": created,
            "price": float(price),
            "active": item.get("active") is True,
        })
    ticks.sort(key=lambda x: x["created_at"])
    return ticks


def _history_books(payload: dict) -> dict:
    books = payload.get("bookmakers") if isinstance(payload, dict) else None
    return books if isinstance(books, dict) else {}


def normalize_historical_fixture(fixture: dict, payload: dict, markets_catalog: list[dict], *, bookmaker: str = "bet365") -> dict | None:
    books = _history_books(payload)
    book = books.get(bookmaker)
    if not isinstance(book, dict):
        return None
    catalog = _catalog(markets_catalog)
    one_x_two = None
    ah: list[dict] = []
    ou: list[dict] = []

    for market_id, market_data in (book.get("markets") or {}).items():
        meta = catalog.get(str(market_id))
        if not isinstance(meta, dict) or not isinstance(market_data, dict):
            continue
        names = _outcome_lookup(meta)
        selections: dict[str, list[dict]] = {}
        for outcome_id, outcome in (market_data.get("outcomes") or {}).items():
            if not isinstance(outcome, dict):
                continue
            players = outcome.get("players") or {}
            ticks = _tick_list(players.get("0")) if isinstance(players, dict) else []
            label = names.get(str(outcome_id), "").strip().lower()
            if label and ticks:
                selections[label] = ticks

        mtype = str(meta.get("marketType") or "").lower()
        mname = str(meta.get("marketName") or "").lower()
        if mtype == "1x2" and {"1", "x", "2"}.issubset(selections):
            one_x_two = {"home": selections["1"], "draw": selections["x"], "away": selections["2"]}
            continue

        line = _quarter(meta.get("handicap"))
        if line is None:
            continue
        if "asian handicap" in mname:
            home = selections.get("home") or selections.get("1")
            away = selections.get("away") or selections.get("2")
            if home and away:
                ah.append({"line": line, "home": home, "away": away})
            continue
        if "over under" in mname or (mtype == "totals" and {"over", "under"}.issubset(selections)):
            over, under = selections.get("over"), selections.get("under")
            if over and under:
                ou.append({"line": line, "over": over, "under": under})

    if not one_x_two and not ah and not ou:
        return None
    return {
        "schema_version": "1.0",
        "fixture_id": str(fixture.get("fixtureId")),
        "tournament_id": fixture.get("tournamentId"),
        "league": fixture.get("tournamentName") or fixture.get("tournamentSlug"),
        "kickoff": fixture.get("startTime"),
        "home": fixture.get("participant1Name"),
        "away": fixture.get("participant2Name"),
        "bookmaker": bookmaker,
        "one_x_two": one_x_two,
        "asian_handicap": sorted(ah, key=lambda x: x["line"]),
        "over_under": sorted(ou, key=lambda x: x["line"]),
        "history_semantics": "FULL_PRICE_HISTORY_FROM_ODDSPAPI",
        "result_join_status": "NOT_JOINED",
        "promotion_eligible": False,
    }


def _compact_fixture(fixture: dict) -> dict:
    tid = fixture.get("tournamentId")
    info = BIG5_TOURNAMENTS.get(int(tid)) if isinstance(tid, (int, float)) or str(tid).isdigit() else None
    return {
        "fixtureId": fixture.get("fixtureId"),
        "tournamentId": tid,
        "tournamentName": fixture.get("tournamentName") or (info or {}).get("name"),
        "tournamentSlug": fixture.get("tournamentSlug"),
        "startTime": fixture.get("startTime"),
        "participant1Name": fixture.get("participant1Name"),
        "participant2Name": fixture.get("participant2Name"),
        "archive_country": (info or {}).get("country"),
    }


def _discover_window(key: str, start: datetime, end: datetime) -> list[dict]:
    """One billable soccer fixture request; filter the validated Big-5 IDs locally."""
    payload = _get("/fixtures", key, {
        "sportId": SPORT_ID,
        "from": _iso(start),
        "to": _iso(end),
        "statusId": 2,
        "hasOdds": "true",
        "bookmakers": "bet365",
        "language": "en",
    })
    found = []
    for fixture in _rows(payload):
        tid = fixture.get("tournamentId")
        try:
            tid_int = int(tid)
        except (TypeError, ValueError):
            continue
        if tid_int not in BIG5_TOURNAMENTS or fixture.get("fixtureId") is None:
            continue
        found.append(_compact_fixture(fixture))
    dedup = {str(f["fixtureId"]): f for f in found}
    rows = list(dedup.values())
    rows.sort(key=lambda f: str(f.get("startTime") or ""))
    return rows


def run_archive(
    root: Path,
    *,
    max_fixtures: int = DEFAULT_FIXTURES_PER_RUN,
    now_fn: Callable[[], datetime] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict:
    now = (now_fn or (lambda: datetime.now(timezone.utc)))()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    state_path = root / STATE_PATH
    archive_path = root / ARCHIVE_PATH
    catalog_path = root / CATALOG_PATH
    state = _read_json(state_path, {})
    key = os.getenv(ENV_KEY)
    if not key:
        payload = {
            "schema_version": "1.1",
            "status": "API_KEY_NOT_CONFIGURED",
            "generated_at": now.isoformat(),
            "promotion_eligible": False,
            "result_join_status": "NOT_JOINED",
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
        archived = _load_archived_ids(archive_path)
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

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    processed = 0
    added = 0
    history_requests = 0
    errors: list[str] = []
    skipped_ids = {str(x) for x in (state.get("skipped_fixture_ids") or [])}
    remaining = list(fixture_queue)
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
                with archive_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                added += 1
            else:
                skipped_ids.add(fid)
        except Exception as exc:
            errors.append(f"{fid}:{type(exc).__name__}:{exc}")
            remaining.append(fixture)
        processed += 1

    archive_rows = len(_load_archived_ids(archive_path))
    payload = {
        "schema_version": "1.1",
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


if __name__ == "__main__":
    print(run_archive(Path(".")))
