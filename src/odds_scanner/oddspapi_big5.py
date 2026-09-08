from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .execution_safety import execution_snapshot_status
from .oddspapi_discovery import DEFAULT_REQUEST_SPACING_SECONDS, _rows, summarize_fixture_odds
from .oddspapi_provider import (
    ENV_KEY,
    ODDSPAPI_CURRENT_FRESHNESS_BASIS,
    SPORT_ID,
    _get,
    _safe_account_summary,
    parse_fixture_markets,
)


BIG5_TARGETS = {
    "England": {"premier league", "premier-league"},
    "Germany": {"bundesliga"},
    "Italy": {"serie a", "serie-a"},
    "Spain": {"laliga", "la liga", "la-liga"},
    "France": {"ligue 1", "ligue-1"},
}


def _norm(value) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", "-").split())


def select_big5_tournaments(rows: list[dict]) -> list[dict]:
    """Select one top division per Big-5 country without fuzzy league guessing."""
    selected: list[dict] = []
    seen_countries: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        country = str(row.get("categoryName") or "")
        if country not in BIG5_TARGETS or country in seen_countries:
            continue
        name = _norm(row.get("tournamentName"))
        slug = _norm(row.get("tournamentSlug"))
        aliases = BIG5_TARGETS[country]
        if name in aliases or slug in aliases:
            if row.get("tournamentId") is not None:
                selected.append(row)
                seen_countries.add(country)
    selected.sort(key=lambda r: str(r.get("categoryName") or ""))
    return selected


def _parse_dt(value) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def probe_from_env(
    *,
    horizon_days: int = 7,
    diagnostic_limit: int = 10,
    request_spacing_seconds: float = DEFAULT_REQUEST_SPACING_SECONDS,
    sleep_fn=time.sleep,
) -> dict:
    generated_at = datetime.now(timezone.utc).isoformat()
    key = os.getenv(ENV_KEY)
    if not key:
        return {
            "schema_version": "2.1",
            "provider": "oddspapi_free",
            "mode": "BIG5_BATCH",
            "status": "API_KEY_NOT_CONFIGURED",
            "generated_at": generated_at,
            "execution_candidate": False,
            "rows": 0,
        }
    if request_spacing_seconds < 0:
        raise ValueError("request_spacing_seconds must be non-negative")

    window_start = datetime.now(timezone.utc)
    end = window_start + timedelta(days=horizon_days)
    request_count = 0
    first = True

    def paced_get(path: str, params: dict | None = None):
        nonlocal request_count, first
        if not first and request_spacing_seconds:
            sleep_fn(request_spacing_seconds)
        first = False
        request_count += 1
        return _get(path, key, params)

    diagnostics: list[dict] = []
    try:
        account = paced_get("/account")
        catalog = _rows(paced_get("/markets", {"language": "en"}))
        tournaments = _rows(paced_get("/tournaments", {"sportId": SPORT_ID, "language": "en"}))
        selected = select_big5_tournaments(tournaments)
        if not selected:
            return {
                "schema_version": "2.1",
                "provider": "oddspapi_free",
                "mode": "BIG5_BATCH",
                "status": "BIG5_TOURNAMENTS_NOT_FOUND",
                "generated_at": generated_at,
                "execution_candidate": False,
                "rows": 0,
                "requests_attempted": request_count,
                "account": _safe_account_summary(account),
            }
        ids = ",".join(str(r["tournamentId"]) for r in selected)
        batch = _rows(paced_get(
            "/odds-by-tournaments",
            {"tournamentIds": ids, "bookmakers": "bet365", "language": "en", "verbosity": 3},
        ))
        # This timestamp means "the current endpoint response was observed now".
        # It is deliberately distinct from every selection's changedAt timestamp.
        observed_at = datetime.now(timezone.utc)
    except Exception as exc:
        return {
            "schema_version": "2.1",
            "provider": "oddspapi_free",
            "mode": "BIG5_BATCH",
            "status": "UNAVAILABLE",
            "generated_at": generated_at,
            "execution_candidate": False,
            "rows": 0,
            "requests_attempted": request_count,
            "errors": [f"{type(exc).__name__}: {exc}"],
        }

    eligible: list[dict] = []
    for fixture in batch:
        start = _parse_dt(fixture.get("startTime"))
        if start is None or start < window_start or start > end:
            continue
        if int(fixture.get("statusId", -1)) != 0 or fixture.get("hasOdds") is not True:
            continue
        eligible.append(fixture)
    eligible.sort(key=lambda f: str(f.get("startTime") or ""))

    normalized = []
    for fixture in eligible:
        rows = parse_fixture_markets(fixture, fixture, catalog, now=observed_at)
        normalized.extend(rows)
        if len(diagnostics) < diagnostic_limit:
            diagnostics.append(summarize_fixture_odds(fixture, fixture, catalog))

    safety_now = datetime.now(timezone.utc)
    safe = 0
    reasons: dict[str, int] = {}
    for row in normalized:
        ok, reason = execution_snapshot_status(row, now=safety_now)
        safe += int(ok)
        reasons[reason] = reasons.get(reason, 0) + 1

    selected_summary = [
        {
            "country": r.get("categoryName"),
            "tournament_id": r.get("tournamentId"),
            "tournament_name": r.get("tournamentName"),
            "tournament_slug": r.get("tournamentSlug"),
        }
        for r in selected
    ]
    return {
        "schema_version": "2.1",
        "provider": "oddspapi_free",
        "mode": "BIG5_BATCH",
        "status": "EXECUTION_SAFE_ROWS_AVAILABLE" if safe else ("ROWS_BUT_NOT_EXECUTION_SAFE" if normalized else "NO_ROWS"),
        "generated_at": generated_at,
        "execution_candidate": safe > 0,
        "requests_attempted": request_count,
        "request_spacing_seconds": request_spacing_seconds,
        "horizon_days": horizon_days,
        "selected_tournaments": selected_summary,
        "selected_tournament_count": len(selected_summary),
        "batch_fixture_rows": len(batch),
        "window_fixture_rows": len(eligible),
        "rows": len(normalized),
        "execution_safe_rows": safe,
        "reasons": reasons,
        "account": _safe_account_summary(account),
        "market_diagnostics": diagnostics,
        "freshness_basis": ODDSPAPI_CURRENT_FRESHNESS_BASIS,
        "price_change_timestamp_semantics": "changedAt/bookmakerChangedAt records when the price last changed; it is retained separately and does not age an otherwise active current quote.",
        "observed_at": observed_at.isoformat(),
        "samples": [asdict(r) for r in normalized[:2]],
    }


def write_health(root: Path) -> dict:
    payload = probe_from_env()
    path = root / "reports/oddspapi_health.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
