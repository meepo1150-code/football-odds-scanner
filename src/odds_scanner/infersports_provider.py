from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://api.infersports.dev"
USER_AGENT = "football-odds-scanner/0.1 personal-research"


def _get_json(path: str, params: dict | None = None, timeout: int = 30) -> dict:
    query = urllib.parse.urlencode(params or {})
    url = BASE + path + (("?" + query) if query else "")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("InferSports returned non-object JSON")
    return payload


def list_scheduled_football(limit: int = 30) -> list[dict]:
    payload = _get_json("/v1/events", {"sport": "football", "status": "scheduled", "limit": limit})
    rows = payload.get("data", [])
    if not isinstance(rows, list):
        raise RuntimeError("InferSports events payload missing data list")
    return rows


def event_odds(event_id: str) -> dict:
    return _get_json(
        f"/v1/events/{event_id}/odds",
        {"markets": "asian_handicap,totals,1x2", "period": "full_time", "format": "decimal"},
    )


def _two_sided(quote: dict) -> bool:
    prices = quote.get("prices") or {}
    if not isinstance(prices, dict):
        return False
    market = str(quote.get("market_type", ""))
    if market == "asian_handicap":
        keys = (("home", "away"), ("home_team", "away_team"))
    elif market == "totals":
        keys = (("over", "under"),)
    elif market == "1x2":
        keys = (("home", "draw", "away"),)
    else:
        return False
    for group in keys:
        if all(isinstance(prices.get(k), (int, float)) and float(prices[k]) > 1.0 for k in group):
            return True
    return False


def probe(limit_events: int = 12) -> dict:
    events = list_scheduled_football(limit=max(limit_events, 1))
    market_counts = Counter()
    bookmaker_counts = Counter()
    quarter_lines = Counter()
    two_sided = Counter()
    stale_blocks = 0
    successful_events = 0
    errors: list[str] = []
    samples: list[dict] = []

    for event in events[:limit_events]:
        event_id = event.get("event_id")
        if not event_id:
            continue
        try:
            block = event_odds(str(event_id))
        except Exception as exc:
            errors.append(f"{event_id}:{type(exc).__name__}:{exc}")
            continue
        successful_events += 1
        if block.get("stale") is True:
            stale_blocks += 1
        odds = block.get("odds") or []
        for q in odds:
            market = str(q.get("market_type", "unknown"))
            market_counts[market] += 1
            bookmaker_counts[str(q.get("bookmaker", "unknown"))] += 1
            if _two_sided(q):
                two_sided[market] += 1
            line = q.get("line")
            if market in {"asian_handicap", "totals"} and isinstance(line, (int, float)):
                line = float(line)
                if abs(line * 4 - round(line * 4)) < 1e-9 and abs(line * 2 - round(line * 2)) > 1e-9:
                    quarter_lines[market] += 1
            if len(samples) < 6:
                samples.append({
                    "event_id": event_id,
                    "bookmaker": q.get("bookmaker"),
                    "market_type": market,
                    "line": line,
                    "status": q.get("status"),
                    "as_of": q.get("as_of"),
                    "two_sided": _two_sided(q),
                })

    ah_two = two_sided.get("asian_handicap", 0)
    totals_two = two_sided.get("totals", 0)
    return {
        "schema_version": "1.0",
        "provider": "infersports_keyless",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scheduled_events_seen": len(events),
        "events_probed": min(len(events), limit_events),
        "successful_events": successful_events,
        "stale_blocks": stale_blocks,
        "market_counts": dict(sorted(market_counts.items())),
        "two_sided_market_counts": dict(sorted(two_sided.items())),
        "quarter_line_counts": dict(sorted(quarter_lines.items())),
        "bookmaker_counts": dict(bookmaker_counts.most_common()),
        "errors": errors[:10],
        "samples": samples,
        "execution_candidate": successful_events > 0 and ah_two > 0 and totals_two > 0 and stale_blocks < successful_events,
        "note": "Health-only live probe. Provider is not promoted to production until this report demonstrates fresh two-sided pre-match AH and totals coverage on the keyless tier.",
    }


def write_health(root: Path, limit_events: int = 12) -> dict:
    payload = probe(limit_events=limit_events)
    path = root / "reports/infersports_health.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    print(json.dumps(write_health(Path(".")), ensure_ascii=False))


if __name__ == "__main__":
    main()
