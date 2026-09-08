from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .execution_safety import execution_snapshot_status
from .market_contract import CurrentMarket

BASE = "https://api.oddspapi.io/v4"
ENV_KEY = "ODDSPAPI_KEY"
USER_AGENT = "football-odds-scanner/0.1 personal-research"
SPORT_ID = 10


def _num(value):
    return float(value) if isinstance(value, (int, float)) else None


def _quarter(value) -> float | None:
    x = _num(value)
    if x is None or abs(x * 4 - round(x * 4)) > 1e-9:
        return None
    return x


def _get(path: str, key: str, params: dict | None = None, timeout: int = 20):
    query = dict(params or {})
    query["apiKey"] = key
    url = BASE + path + "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _catalog(markets: list[dict]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for market in markets:
        if market.get("sportId") != SPORT_ID:
            continue
        if str(market.get("period") or "").lower() != "fulltime":
            continue
        if market.get("playerProp") is True:
            continue
        result[str(market.get("marketId"))] = market
    return result


def _player(outcome: dict) -> dict | None:
    players = outcome.get("players") or {}
    if not isinstance(players, dict) or not players:
        return None
    p = players.get("0")
    if not isinstance(p, dict):
        p = next((x for x in players.values() if isinstance(x, dict)), None)
    if not isinstance(p, dict) or _num(p.get("price")) is None or _num(p.get("price")) <= 1.0:
        return None
    return p


def _stamp(player: dict) -> str | None:
    value = player.get("bookmakerChangedAt") or player.get("changedAt")
    return str(value) if isinstance(value, str) and value.strip() else None


def _oldest_timestamp(players: list[dict]) -> str | None:
    parsed: list[tuple[datetime, str]] = []
    for p in players:
        stamp = _stamp(p)
        if not stamp:
            return None
        try:
            dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError:
            return None
        if dt.tzinfo is None:
            return None
        parsed.append((dt.astimezone(timezone.utc), stamp))
    return min(parsed, key=lambda x: x[0])[1] if parsed else None


def _outcome_lookup(market_meta: dict) -> dict[str, str]:
    return {str(o.get("outcomeId")): str(o.get("outcomeName") or "") for o in market_meta.get("outcomes") or []}


def _fixture_fields(fixture: dict) -> tuple[str, str, str, str, str, str]:
    kickoff = str(fixture.get("startTime") or fixture.get("start_time") or "")
    date_value = time_value = ""
    if kickoff:
        try:
            dt = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
            date_value = dt.date().isoformat()
            time_value = dt.time().replace(tzinfo=None).isoformat(timespec="minutes")
        except ValueError:
            pass
    league = str(fixture.get("tournamentName") or fixture.get("tournamentSlug") or fixture.get("tournamentId") or "")
    home = str(fixture.get("participant1Name") or fixture.get("home") or "")
    away = str(fixture.get("participant2Name") or fixture.get("away") or "")
    status_name = str(fixture.get("statusName") or "").lower().replace("-", "_").replace(" ", "_")
    status = "pre_match" if status_name in {"pre_game", "pregame", "scheduled", "pre_match"} else status_name
    return league, date_value, time_value, home, away, status


def parse_fixture_markets(fixture: dict, odds_payload: dict, markets_catalog: list[dict], *, bookmaker: str = "bet365", now: datetime | None = None, max_age_minutes: int = 30) -> list[CurrentMarket]:
    """Normalize exact full-time Bet365 1X2 x AH-line x O/U-line combinations.

    Market metadata is authoritative. No line is rounded or guessed. Each emitted
    row uses the oldest timestamp among all required selections so mixed-age market
    structures fail conservatively at the execution-safety gate.
    """
    catalog = _catalog(markets_catalog)
    books = odds_payload.get("bookmakerOdds") or {}
    book = books.get(bookmaker)
    if not isinstance(book, dict) or book.get("bookmakerIsActive") is False or book.get("suspended") is True:
        return []

    one_x_two = None
    ah_rows: list[dict] = []
    ou_rows: list[dict] = []
    for market_id, market_data in (book.get("markets") or {}).items():
        meta = catalog.get(str(market_id))
        if not isinstance(meta, dict) or not isinstance(market_data, dict) or market_data.get("marketActive") is False:
            continue
        outcomes = market_data.get("outcomes") or {}
        names = _outcome_lookup(meta)
        mname = str(meta.get("marketName") or "").lower()
        mtype = str(meta.get("marketType") or "").lower()
        selections: dict[str, dict] = {}
        for outcome_id, outcome in outcomes.items():
            p = _player(outcome) if isinstance(outcome, dict) else None
            if not p or p.get("active") is False:
                continue
            label = names.get(str(outcome_id), "").strip().lower()
            if label:
                selections[label] = p

        if mtype == "1x2" and {"1", "x", "2"}.issubset(selections):
            one_x_two = {"home": selections["1"], "draw": selections["x"], "away": selections["2"]}
            continue
        line = _quarter(meta.get("handicap"))
        if line is None:
            continue
        if "asian handicap" in mname:
            home_p = selections.get("home") or selections.get("1")
            away_p = selections.get("away") or selections.get("2")
            if home_p and away_p:
                ah_rows.append({"line": line, "home": home_p, "away": away_p})
            continue
        if "over under" in mname or (mtype == "totals" and {"over", "under"}.issubset(selections)):
            over_p, under_p = selections.get("over"), selections.get("under")
            if over_p and under_p:
                ou_rows.append({"line": line, "over": over_p, "under": under_p})

    if not one_x_two or not ah_rows or not ou_rows:
        return []

    league, date_value, kickoff, home, away, status = _fixture_fields(fixture)
    current = now or datetime.now(timezone.utc)
    rows: list[CurrentMarket] = []
    for ah in ah_rows:
        for ou in ou_rows:
            required = [one_x_two["home"], one_x_two["draw"], one_x_two["away"], ah["home"], ah["away"], ou["over"], ou["under"]]
            as_of = _oldest_timestamp(required)
            stale = None
            if as_of:
                try:
                    stamp = datetime.fromisoformat(as_of.replace("Z", "+00:00")).astimezone(timezone.utc)
                    age = (current.astimezone(timezone.utc) - stamp).total_seconds()
                    stale = age > max_age_minutes * 60 or age < -300
                except ValueError:
                    stale = None
            rows.append(CurrentMarket(
                source=f"oddspapi:{bookmaker}:timestamped", league=league, date=date_value, kickoff=kickoff,
                home=home, away=away, ah_home_line=ah["line"], ah_home_odds=float(ah["home"]["price"]),
                ah_away_line=-ah["line"], ah_away_odds=float(ah["away"]["price"]), ou_line=ou["line"],
                over_odds=float(ou["over"]["price"]), under_odds=float(ou["under"]["price"]),
                one_x_two_home=float(one_x_two["home"]["price"]), one_x_two_draw=float(one_x_two["draw"]["price"]),
                one_x_two_away=float(one_x_two["away"]["price"]), status=status, as_of=as_of, stale=stale,
                tradable=(status == "pre_match" and stale is False),
            ))
    return rows


def _safe_account_summary(account: dict) -> dict:
    """Never persist API keys or subscription identifiers from /account."""
    subscriptions = account.get("subscriptions") or [] if isinstance(account, dict) else []
    active = next((s for s in subscriptions if isinstance(s, dict) and s.get("is_active") is True), None)
    if not active:
        return {"active_subscription": False}
    return {
        "active_subscription": True,
        "price": active.get("price"),
        "currency": active.get("currency"),
        "request_limit": active.get("request_limit"),
        "request_count": active.get("request_count"),
        "rate_limit": active.get("rate_limit"),
        "sport_ids": active.get("sport_ids"),
        "bookmakers": sorted((active.get("bookmakers") or {}).keys()),
    }


def probe_from_env(limit: int = 5) -> dict:
    generated_at = datetime.now(timezone.utc).isoformat()
    key = os.getenv(ENV_KEY)
    if not key:
        return {"schema_version": "1.0", "provider": "oddspapi_free", "status": "API_KEY_NOT_CONFIGURED", "generated_at": generated_at, "execution_candidate": False, "rows": 0, "note": f"Optional GitHub secret {ENV_KEY} is not configured."}
    try:
        account = _get("/account", key)
        catalog = _get("/markets", key, {"sportId": SPORT_ID, "language": "en"})
        now = datetime.now(timezone.utc)
        today = now.date().isoformat()
        tomorrow = (now.date() + timedelta(days=1)).isoformat()
        fixtures = _get("/fixtures", key, {"sportId": SPORT_ID, "from": today, "to": tomorrow})
        fixture_rows = fixtures if isinstance(fixtures, list) else fixtures.get("data") or []
        normalized: list[CurrentMarket] = []
        for fixture in fixture_rows[: max(1, limit)]:
            fid = fixture.get("fixtureId")
            if not fid or not fixture.get("hasOdds"):
                continue
            odds = _get("/odds", key, {"fixtureId": fid, "bookmakers": "bet365", "verbosity": 3})
            normalized.extend(parse_fixture_markets(fixture, odds, catalog if isinstance(catalog, list) else catalog.get("data") or [], now=now))
    except Exception as exc:
        return {"schema_version": "1.0", "provider": "oddspapi_free", "status": "UNAVAILABLE", "generated_at": generated_at, "execution_candidate": False, "rows": 0, "errors": [f"{type(exc).__name__}: {exc}"]}

    safe = 0
    reasons: dict[str, int] = {}
    for row in normalized:
        ok, reason = execution_snapshot_status(row, now=now)
        safe += int(ok)
        reasons[reason] = reasons.get(reason, 0) + 1
    return {
        "schema_version": "1.0", "provider": "oddspapi_free",
        "status": "EXECUTION_SAFE_ROWS_AVAILABLE" if safe else ("ROWS_BUT_NOT_EXECUTION_SAFE" if normalized else "NO_ROWS"),
        "generated_at": generated_at, "execution_candidate": safe > 0, "rows": len(normalized), "execution_safe_rows": safe,
        "reasons": reasons, "account": _safe_account_summary(account),
        "freshness_basis": "oldest bookmakerChangedAt/changedAt across required 1X2+AH+OU selections",
        "samples": [asdict(r) for r in normalized[:2]],
    }


def write_health(root: Path) -> dict:
    payload = probe_from_env()
    path = root / "reports/oddspapi_health.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
