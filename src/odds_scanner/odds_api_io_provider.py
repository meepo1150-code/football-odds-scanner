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

BASE = "https://api.odds-api.io/v3"
ENV_KEY = "ODDS_API_IO_KEY"
USER_AGENT = "football-odds-scanner/0.1 personal-research"
BOOKMAKER = "Bet365"


def _num(value):
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if x > 1.0 else None


def _line(value):
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if abs(x * 4 - round(x * 4)) < 1e-8 else None


def _dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _get(path: str, key: str, params: dict | None = None, timeout: int = 15):
    query = dict(params or {})
    query["apiKey"] = key
    url = BASE + path + "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _book_markets(payload: dict, bookmaker: str) -> list[dict]:
    books = payload.get("bookmakers") or {}
    if not isinstance(books, dict):
        return []
    for name, markets in books.items():
        if str(name).lower() == bookmaker.lower() and isinstance(markets, list):
            return markets
    return []


def _market(markets: list[dict], names: set[str]) -> list[dict]:
    wanted = {x.lower() for x in names}
    return [m for m in markets if str(m.get("name") or "").lower() in wanted]


def _oldest_timestamp(*markets: dict) -> str | None:
    values = [_dt(m.get("updatedAt")) for m in markets]
    if any(v is None for v in values):
        return None
    return min(values).isoformat()


def parse_event_odds(payload: dict, *, bookmaker: str = BOOKMAKER, now: datetime | None = None) -> list[CurrentMarket]:
    """Normalize every valid AH × O/U line combination from one event.

    We deliberately do not guess a bookmaker 'main' line when multiple alternatives are
    present. Line and price remain inseparable and each advertised combination is emitted.
    The oldest ML/AH/O-U market updatedAt is used as the conservative snapshot timestamp.
    """
    markets = _book_markets(payload, bookmaker)
    ml_markets = _market(markets, {"ML", "Moneyline"})
    ah_markets = _market(markets, {"Spread", "Asian Handicap"})
    ou_markets = _market(markets, {"Totals", "Over/Under"})
    if not ml_markets or not ah_markets or not ou_markets:
        return []

    ml_market = ml_markets[0]
    ml_values = ml_market.get("odds") or []
    ml = next((x for x in ml_values if _num(x.get("home")) and _num(x.get("draw")) and _num(x.get("away"))), None)
    if not ml:
        return []

    ah_entries = []
    for m in ah_markets:
        for x in m.get("odds") or []:
            line = _line(x.get("hdp"))
            ho, ao = _num(x.get("home")), _num(x.get("away"))
            if line is not None and ho and ao:
                ah_entries.append((m, line, ho, ao))

    ou_entries = []
    for m in ou_markets:
        for x in m.get("odds") or []:
            line = _line(x.get("hdp", x.get("max")))
            over, under = _num(x.get("over")), _num(x.get("under"))
            if line is not None and over and under:
                ou_entries.append((m, line, over, under))

    event_status = str(payload.get("status") or "").lower()
    status = "scheduled" if event_status in {"pending", "scheduled", "not_started"} else event_status or None
    kickoff_dt = _dt(payload.get("date"))
    league = payload.get("league") or {}
    event_id = str(payload.get("id") or "")
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    rows = []
    for ah_m, ah_line, home_ah, away_ah in ah_entries:
        for ou_m, ou_line, over, under in ou_entries:
            as_of = _oldest_timestamp(ml_market, ah_m, ou_m)
            quote_dt = _dt(as_of)
            stale = None if quote_dt is None else (now - quote_dt > timedelta(minutes=30))
            rows.append(
                CurrentMarket(
                    source=f"odds-api.io:{bookmaker}:event:{event_id}",
                    league=str(league.get("name") or league.get("slug") or ""),
                    date=kickoff_dt.date().isoformat() if kickoff_dt else "",
                    kickoff=kickoff_dt.time().replace(tzinfo=None).isoformat(timespec="minutes") if kickoff_dt else "",
                    home=str(payload.get("home") or ""),
                    away=str(payload.get("away") or ""),
                    ah_home_line=ah_line,
                    ah_home_odds=home_ah,
                    ah_away_line=-ah_line,
                    ah_away_odds=away_ah,
                    ou_line=ou_line,
                    over_odds=over,
                    under_odds=under,
                    one_x_two_home=_num(ml.get("home")),
                    one_x_two_draw=_num(ml.get("draw")),
                    one_x_two_away=_num(ml.get("away")),
                    status=status,
                    as_of=as_of,
                    stale=stale,
                    tradable=status == "scheduled",
                )
            )
    return rows


class OddsApiIoCurrentProvider:
    provider_id = "odds_api_io_free:bet365"

    def __init__(self, key: str | None = None, *, max_events: int = 20, now_fn=lambda: datetime.now(timezone.utc)):
        self.key = key or os.getenv(ENV_KEY)
        self.max_events = max(1, min(max_events, 20))
        self.now_fn = now_fn

    def fetch(self) -> list[CurrentMarket]:
        if not self.key:
            raise RuntimeError(f"{ENV_KEY} is not configured")
        now = self.now_fn().astimezone(timezone.utc)
        events = _get(
            "/events",
            self.key,
            {
                "sport": "football",
                "status": "pending",
                "bookmaker": BOOKMAKER,
                "from": now.isoformat().replace("+00:00", "Z"),
                "to": (now + timedelta(hours=24)).isoformat().replace("+00:00", "Z"),
            },
        )
        if not isinstance(events, list):
            raise RuntimeError("Odds-API.io events response is not a list")
        selected = events[: self.max_events]
        if not selected:
            return []
        payloads = _get(
            "/odds/multi",
            self.key,
            {"eventIds": ",".join(str(e.get("id")) for e in selected if e.get("id") is not None), "bookmakers": BOOKMAKER},
        )
        if not isinstance(payloads, list):
            raise RuntimeError("Odds-API.io multi-odds response is not a list")
        rows = []
        for p in payloads:
            rows.extend(parse_event_odds(p, now=now))
        return rows


def probe_from_env(max_events: int = 10) -> dict:
    generated_at = datetime.now(timezone.utc).isoformat()
    key = os.getenv(ENV_KEY)
    if not key:
        return {
            "schema_version": "1.0",
            "provider": "odds_api_io_free",
            "status": "API_KEY_NOT_CONFIGURED",
            "generated_at": generated_at,
            "execution_candidate": False,
            "rows": 0,
            "note": f"Optional GitHub secret {ENV_KEY} is not configured.",
        }
    try:
        rows = OddsApiIoCurrentProvider(key, max_events=max_events).fetch()
    except Exception as exc:
        return {
            "schema_version": "1.0",
            "provider": "odds_api_io_free",
            "status": "UNAVAILABLE",
            "generated_at": generated_at,
            "execution_candidate": False,
            "rows": 0,
            "errors": [f"{type(exc).__name__}: {exc}"],
        }
    safety = [execution_snapshot_status(r) for r in rows]
    safe = sum(1 for ok, _ in safety if ok)
    reasons = {}
    for ok, reason in safety:
        if not ok:
            reasons[reason] = reasons.get(reason, 0) + 1
    return {
        "schema_version": "1.0",
        "provider": "odds_api_io_free",
        "status": "EXECUTION_SCHEMA_OK" if safe else ("NO_ROWS" if not rows else "NO_FRESH_EXECUTION_ROWS"),
        "generated_at": generated_at,
        "execution_candidate": safe > 0,
        "rows": len(rows),
        "execution_safe_rows": safe,
        "safety_rejections": reasons,
        "quarter_ah": sum(1 for r in rows if r.ah_home_line is not None and abs(r.ah_home_line * 2 - round(r.ah_home_line * 2)) > 1e-9),
        "quarter_ou": sum(1 for r in rows if r.ou_line is not None and abs(r.ou_line * 2 - round(r.ou_line * 2)) > 1e-9),
        "freshness_basis": "provider market updatedAt; oldest required ML/AH/O-U timestamp used conservatively",
        "samples": [asdict(r) for r in rows[:2]],
    }


def write_health(root: Path) -> dict:
    payload = probe_from_env()
    path = root / "reports/odds_api_io_health.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
