from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .execution_safety import execution_snapshot_status
from .oddspapi_provider import (
    ENV_KEY,
    SPORT_ID,
    _get,
    _safe_account_summary,
    parse_fixture_markets,
)


DEFAULT_REQUEST_SPACING_SECONDS = 1.1


def fixture_query(now: datetime, *, hours: int = 24) -> dict:
    """Build a narrow pre-match Bet365 discovery query.

    OddsPapi documents statusId=0 as Pre-Game and supports hasOdds/bookmakers
    filters on GET /fixtures. Use an exact rolling UTC window rather than a
    calendar-date approximation so discovery spends quota only on relevant rows.
    """
    current = now.astimezone(timezone.utc)
    end = current + timedelta(hours=hours)
    return {
        "sportId": SPORT_ID,
        "from": current.isoformat().replace("+00:00", "Z"),
        "to": end.isoformat().replace("+00:00", "Z"),
        "statusId": 0,
        "hasOdds": "true",
        "bookmakers": "bet365",
        "language": "en",
    }


def _rows(payload) -> list[dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("data", "fixtures", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def probe_from_env(
    *,
    limit: int = 5,
    hours: int = 24,
    request_spacing_seconds: float = DEFAULT_REQUEST_SPACING_SECONDS,
    sleep_fn=time.sleep,
) -> dict:
    generated_at = datetime.now(timezone.utc).isoformat()
    key = os.getenv(ENV_KEY)
    if not key:
        return {
            "schema_version": "1.2",
            "provider": "oddspapi_free",
            "status": "API_KEY_NOT_CONFIGURED",
            "generated_at": generated_at,
            "execution_candidate": False,
            "rows": 0,
            "fixtures_discovered": 0,
            "odds_requests": 0,
            "note": f"Optional GitHub secret {ENV_KEY} is not configured.",
        }

    if request_spacing_seconds < 0:
        raise ValueError("request_spacing_seconds must be non-negative")

    now = datetime.now(timezone.utc)
    odds_requests = 0
    total_requests = 0
    fixture_rows: list[dict] = []
    normalized = []
    first_request = True

    def paced_get(path: str, params: dict | None = None):
        nonlocal first_request, total_requests
        if not first_request and request_spacing_seconds:
            sleep_fn(request_spacing_seconds)
        first_request = False
        total_requests += 1
        return _get(path, key, params)

    try:
        account = paced_get("/account")
        catalog_payload = paced_get("/markets", {"language": "en"})
        catalog = _rows(catalog_payload)
        fixtures_payload = paced_get("/fixtures", fixture_query(now, hours=hours))
        fixture_rows = _rows(fixtures_payload)

        # API-side filters are primary, but keep local fail-closed checks too.
        candidates = [
            f for f in fixture_rows
            if f.get("hasOdds") is True
            and int(f.get("statusId", -1)) == 0
            and f.get("fixtureId")
        ]
        candidates.sort(key=lambda f: str(f.get("startTime") or ""))

        for fixture in candidates[: max(1, limit)]:
            odds_requests += 1
            odds = paced_get(
                "/odds",
                {
                    "fixtureId": fixture["fixtureId"],
                    "bookmakers": "bet365",
                    "language": "en",
                    "verbosity": 3,
                },
            )
            normalized.extend(parse_fixture_markets(fixture, odds, catalog, now=now))
    except Exception as exc:
        return {
            "schema_version": "1.2",
            "provider": "oddspapi_free",
            "status": "UNAVAILABLE",
            "generated_at": generated_at,
            "execution_candidate": False,
            "rows": 0,
            "fixtures_discovered": len(fixture_rows),
            "odds_requests": odds_requests,
            "requests_attempted": total_requests,
            "request_spacing_seconds": request_spacing_seconds,
            "errors": [f"{type(exc).__name__}: {exc}"],
        }

    safe = 0
    reasons: dict[str, int] = {}
    for row in normalized:
        ok, reason = execution_snapshot_status(row, now=now)
        safe += int(ok)
        reasons[reason] = reasons.get(reason, 0) + 1

    candidates_count = sum(
        1 for f in fixture_rows
        if f.get("hasOdds") is True
        and int(f.get("statusId", -1)) == 0
        and f.get("fixtureId")
    )
    return {
        "schema_version": "1.2",
        "provider": "oddspapi_free",
        "status": "EXECUTION_SAFE_ROWS_AVAILABLE" if safe else ("ROWS_BUT_NOT_EXECUTION_SAFE" if normalized else "NO_ROWS"),
        "generated_at": generated_at,
        "execution_candidate": safe > 0,
        "fixtures_discovered": len(fixture_rows),
        "fixtures_eligible_after_local_check": candidates_count,
        "fixtures_probed": min(candidates_count, max(1, limit)),
        "odds_requests": odds_requests,
        "requests_attempted": total_requests,
        "request_spacing_seconds": request_spacing_seconds,
        "rows": len(normalized),
        "execution_safe_rows": safe,
        "reasons": reasons,
        "account": _safe_account_summary(account),
        "discovery": {
            "window_hours": hours,
            "status_id": 0,
            "has_odds": True,
            "bookmaker": "bet365",
            "api_side_filtering": True,
            "detailed_odds_probe_cap": limit,
        },
        "freshness_basis": "oldest bookmakerChangedAt/changedAt across required 1X2+AH+OU selections",
        "samples": [asdict(r) for r in normalized[:2]],
    }


def write_health(root: Path) -> dict:
    payload = probe_from_env()
    path = root / "reports/oddspapi_health.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
