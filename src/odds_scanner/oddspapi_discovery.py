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


def summarize_fixture_odds(fixture: dict, odds_payload: dict, catalog: list[dict], *, sample_limit: int = 16) -> dict:
    """Return schema diagnostics without persisting raw prices or provider payloads."""
    catalog_by_id = {str(m.get("marketId")): m for m in catalog if isinstance(m, dict)}
    books = odds_payload.get("bookmakerOdds") or {} if isinstance(odds_payload, dict) else {}
    book = books.get("bet365") if isinstance(books, dict) else None
    summary = {
        "fixture_id": fixture.get("fixtureId"),
        "tournament": fixture.get("tournamentName") or fixture.get("tournamentSlug"),
        "start_time": fixture.get("startTime"),
        "bookmaker_present": isinstance(book, dict),
        "bookmaker_active": None,
        "suspended": None,
        "market_count": 0,
        "active_market_count": 0,
        "catalog_match_count": 0,
        "market_samples": [],
    }
    if not isinstance(book, dict):
        return summary
    summary["bookmaker_active"] = book.get("bookmakerIsActive")
    summary["suspended"] = book.get("suspended")
    markets = book.get("markets") or {}
    if not isinstance(markets, dict):
        return summary
    summary["market_count"] = len(markets)

    for market_id, market_data in markets.items():
        if not isinstance(market_data, dict):
            continue
        if market_data.get("marketActive") is not False:
            summary["active_market_count"] += 1
        meta = catalog_by_id.get(str(market_id))
        if meta:
            summary["catalog_match_count"] += 1
        if len(summary["market_samples"]) >= sample_limit:
            continue

        outcome_labels = []
        if isinstance(meta, dict):
            outcome_labels = [str(o.get("outcomeName") or "") for o in meta.get("outcomes") or [] if isinstance(o, dict)]
        players_seen = 0
        changed_at_present = 0
        bookmaker_changed_at_present = 0
        main_line_true = 0
        for outcome in (market_data.get("outcomes") or {}).values():
            if not isinstance(outcome, dict):
                continue
            for player in (outcome.get("players") or {}).values():
                if not isinstance(player, dict):
                    continue
                players_seen += 1
                changed_at_present += int(bool(player.get("changedAt")))
                bookmaker_changed_at_present += int(bool(player.get("bookmakerChangedAt")))
                main_line_true += int(player.get("mainLine") is True)

        summary["market_samples"].append({
            "market_id": str(market_id),
            "market_active": market_data.get("marketActive"),
            "catalog_match": meta is not None,
            "market_name": meta.get("marketName") if isinstance(meta, dict) else None,
            "market_type": meta.get("marketType") if isinstance(meta, dict) else None,
            "period": meta.get("period") if isinstance(meta, dict) else None,
            "handicap": meta.get("handicap") if isinstance(meta, dict) else None,
            "outcome_labels": outcome_labels,
            "players_seen": players_seen,
            "changed_at_present": changed_at_present,
            "bookmaker_changed_at_present": bookmaker_changed_at_present,
            "main_line_true": main_line_true,
        })
    return summary


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
            "schema_version": "1.3",
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
    diagnostics: list[dict] = []
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
        candidates = [
            f for f in fixture_rows
            if f.get("hasOdds") is True and int(f.get("statusId", -1)) == 0 and f.get("fixtureId")
        ]
        candidates.sort(key=lambda f: str(f.get("startTime") or ""))

        for fixture in candidates[: max(1, limit)]:
            odds_requests += 1
            odds = paced_get(
                "/odds",
                {"fixtureId": fixture["fixtureId"], "bookmakers": "bet365", "language": "en", "verbosity": 3},
            )
            diagnostics.append(summarize_fixture_odds(fixture, odds, catalog))
            normalized.extend(parse_fixture_markets(fixture, odds, catalog, now=now))
    except Exception as exc:
        return {
            "schema_version": "1.3",
            "provider": "oddspapi_free",
            "status": "UNAVAILABLE",
            "generated_at": generated_at,
            "execution_candidate": False,
            "rows": 0,
            "fixtures_discovered": len(fixture_rows),
            "odds_requests": odds_requests,
            "requests_attempted": total_requests,
            "request_spacing_seconds": request_spacing_seconds,
            "market_diagnostics": diagnostics,
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
        if f.get("hasOdds") is True and int(f.get("statusId", -1)) == 0 and f.get("fixtureId")
    )
    return {
        "schema_version": "1.3",
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
        "market_diagnostics": diagnostics,
        "freshness_basis": "oldest bookmakerChangedAt/changedAt across required 1X2+AH+OU selections",
        "samples": [asdict(r) for r in normalized[:2]],
    }


def write_health(root: Path) -> dict:
    payload = probe_from_env()
    path = root / "reports/oddspapi_health.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
