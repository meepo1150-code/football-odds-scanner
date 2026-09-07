from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .market_contract import CurrentMarket

BASE = "https://api.5dollarfootballapi.com/v1"
ENV_KEY = "FIVE_DOLLAR_FOOTBALL_API_KEY"
USER_AGENT = "football-odds-scanner/0.1 personal-research"


def _number(value):
    if isinstance(value, (int, float)):
        return float(value)
    return None


def parse_fixture_odds(fixture: dict, odds_payload: dict, *, bookmaker: str = "bet365") -> CurrentMarket:
    """Parse documented fixture + odds responses without claiming quote freshness."""
    data = odds_payload.get("data") or {}
    books = data.get("bookmakers") or []
    book = next((b for b in books if str(b.get("slug", "")).lower() == bookmaker.lower()), None)
    if not isinstance(book, dict):
        raise ValueError(f"bookmaker {bookmaker!r} missing from odds payload")
    odds = book.get("odds") or {}
    x12 = (odds.get("1x2") or {}).get("closing") or {}
    ah = (odds.get("asian_handicap") or {}).get("closing") or {}
    goal = (odds.get("goal_line") or {}).get("closing") or {}

    line = _number(ah.get("line"))
    home_ah = line
    away_ah = -line if line is not None else None
    kickoff = str(fixture.get("kickoff_utc") or "")
    date_value, time_value = "", ""
    if kickoff:
        try:
            dt = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
            date_value = dt.date().isoformat()
            time_value = dt.time().replace(tzinfo=None).isoformat(timespec="minutes")
        except ValueError:
            pass

    teams = fixture.get("teams") or {}
    league = fixture.get("league") or {}
    return CurrentMarket(
        source=f"5dollarfootballapi:{bookmaker}",
        league=str(league.get("name") or league.get("id") or ""),
        date=date_value,
        kickoff=time_value,
        home=str((teams.get("home") or {}).get("name") or ""),
        away=str((teams.get("away") or {}).get("name") or ""),
        ah_home_line=home_ah,
        ah_home_odds=_number(ah.get("home")),
        ah_away_line=away_ah,
        ah_away_odds=_number(ah.get("away")),
        ou_line=_number(goal.get("line")),
        over_odds=_number(goal.get("over")),
        under_odds=_number(goal.get("under")),
        one_x_two_home=_number(x12.get("home")),
        one_x_two_draw=_number(x12.get("draw")),
        one_x_two_away=_number(x12.get("away")),
        status=str(fixture.get("status") or "") or None,
        # The documented summary response does not expose the quote's recorded_at.
        # Never substitute request time: the execution safety layer must reject
        # freshness-unverified summary rows until a provider timestamp is available.
        as_of=None,
        stale=None,
        tradable=True if fixture.get("status") == "scheduled" else False,
    )


def _get(path: str, key: str, params: dict | None = None, timeout: int = 15) -> dict:
    query = urllib.parse.urlencode(params or {})
    url = BASE + path + (("?" + query) if query else "")
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("success") not in (1, True):
        raise RuntimeError(f"5DollarFootballAPI unsuccessful response: {payload!r}")
    return payload


def probe_from_env(limit: int = 3) -> dict:
    key = os.getenv(ENV_KEY)
    generated_at = datetime.now(timezone.utc).isoformat()
    if not key:
        return {
            "schema_version": "1.0",
            "provider": "5dollarfootballapi_free",
            "status": "API_KEY_NOT_CONFIGURED",
            "generated_at": generated_at,
            "execution_candidate": False,
            "rows": 0,
            "note": f"Set GitHub secret {ENV_KEY} to run the live free-tier probe. No key is stored in the repository.",
        }

    fixtures_env = _get("/fixtures", key, {"status": "scheduled", "per_page": max(1, min(limit, 10))})
    fixtures = fixtures_env.get("data") or []
    rows = []
    errors = []
    for fixture in fixtures[:limit]:
        try:
            odds = _get(f"/fixtures/{fixture['id']}/odds", key)
            rows.append(parse_fixture_odds(fixture, odds))
        except Exception as exc:
            errors.append(f"{fixture.get('id')}:{type(exc).__name__}:{exc}")

    quarter_ah = sum(1 for r in rows if r.ah_home_line is not None and abs(r.ah_home_line * 2 - round(r.ah_home_line * 2)) > 1e-9)
    quarter_ou = sum(1 for r in rows if r.ou_line is not None and abs(r.ou_line * 2 - round(r.ou_line * 2)) > 1e-9)
    two_sided_ah = sum(1 for r in rows if r.ah_home_odds and r.ah_away_odds)
    two_sided_ou = sum(1 for r in rows if r.over_odds and r.under_odds)
    return {
        "schema_version": "1.0",
        "provider": "5dollarfootballapi_free",
        "status": "SCHEMA_OK_FRESHNESS_UNVERIFIED" if rows else "NO_ROWS",
        "generated_at": generated_at,
        "execution_candidate": False,
        "fixtures_seen": len(fixtures),
        "rows": len(rows),
        "two_sided_ah": two_sided_ah,
        "two_sided_ou": two_sided_ou,
        "quarter_ah": quarter_ah,
        "quarter_ou": quarter_ou,
        "errors": errors,
        "samples": [asdict(r) for r in rows[:2]],
        "note": "Closing is documented as latest pre-match for scheduled fixtures, but summary odds rows expose no per-quote timestamp in the documented response. Execution remains blocked by the freshness gate.",
    }


def write_health(root: Path) -> dict:
    try:
        payload = probe_from_env()
    except Exception as exc:
        payload = {
            "schema_version": "1.0",
            "provider": "5dollarfootballapi_free",
            "status": "UNAVAILABLE",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "execution_candidate": False,
            "errors": [f"{type(exc).__name__}: {exc}"],
        }
    path = root / "reports/five_dollar_health.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
