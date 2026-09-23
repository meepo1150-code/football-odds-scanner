from __future__ import annotations

import json
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .europe_pinnacle_discovery import SNAPSHOT_PATH, AUDIT_PATH, _merge_jsonl
from .sgodds_provider import fetch_current_markets

BKK = ZoneInfo("Asia/Bangkok")
REPORT = Path("reports/sgodds_research_v2_status.json")
BOOKMAKER = "singapore_pools"


def _parse_source_dt(date_text: str, time_text: str) -> datetime | None:
    raw = f"{date_text} {time_text}".strip()
    for fmt in ("%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%d-%m-%Y %H:%M", "%d/%m/%y %H:%M", "%d %b %Y %H:%M", "%d %B %Y %H:%M", "%d %b %y %H:%M"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=BKK)
        except ValueError:
            pass
    return None


def _football_day(now: datetime) -> tuple[datetime, datetime, str]:
    local = now.astimezone(BKK)
    label = local.date() - timedelta(days=1) if local.time() < dtime(6) else local.date()
    start = datetime.combine(label, dtime(12), BKK)
    end = datetime.combine(label + timedelta(days=1), dtime(6), BKK)
    return start, end, label.isoformat()


def _devig3(h: float | None, d: float | None, a: float | None):
    if not all(x and x > 1 for x in (h, d, a)):
        return None
    raw = (1 / h, 1 / d, 1 / a)
    s = sum(raw)
    return tuple(x / s for x in raw)


def _write(root: Path, report: dict) -> dict:
    p = root / REPORT
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def run(root: Path = Path(".")) -> dict:
    now = datetime.now(timezone.utc)
    ws, we, day = _football_day(now)
    report = {
        "schema_version": "1.0",
        "provider": "sgodds_singapore_pools_open",
        "bookmaker": BOOKMAKER,
        "football_day": day,
        "generated_at": now.isoformat(),
        "research_only": True,
        "requests_used": 0,
        "quota_required": False,
        "source_semantics": "CURRENT_OPEN_MARKET_SNAPSHOT",
    }
    try:
        markets = fetch_current_markets()
    except Exception as exc:
        report.update(status="SOURCE_FETCH_FAILED", errors=[f"{type(exc).__name__}: {exc}"])
        return _write(root, report)

    snapshots, audits = [], []
    source_rows_in_day = 0
    parse_failures = 0
    for m in markets:
        kickoff = _parse_source_dt(m.date, m.kickoff)
        if kickoff is None:
            parse_failures += 1
            continue
        if not (ws <= kickoff < we):
            continue
        source_rows_in_day += 1
        if m.ah_home_line is None or m.ah_home_odds is None or m.ah_away_odds is None:
            continue

        fair = _devig3(m.one_x_two_home, m.one_x_two_draw, m.one_x_two_away)
        if m.ah_home_line < 0:
            fav = "H"
        elif m.ah_home_line > 0:
            fav = "A"
        elif fair:
            fav = "H" if fair[0] >= fair[2] else "A"
        else:
            continue

        selected_line = m.ah_home_line if fav == "H" else m.ah_away_line
        selected_price = m.ah_home_odds if fav == "H" else m.ah_away_odds
        if selected_line is None or selected_price is None:
            continue

        fid = f"sgodds:{m.league}:{kickoff.isoformat()}:{m.home}:{m.away}"
        snap = {
            "provider": "sgodds_singapore_pools_open",
            "source": "sgodds:singapore_pools:current",
            "bookmaker": BOOKMAKER,
            "fixture_id": fid,
            "football_day": day,
            "observed_at": now.isoformat(),
            "scheduled_target_at": now.astimezone(BKK).isoformat(),
            "observation_timing": "SCHEDULED_FREE_SCAN",
            "research_only": True,
            "league": m.league,
            "home": m.home,
            "away": m.away,
            "kickoff": kickoff.astimezone(timezone.utc).isoformat(),
            "favorite_side": fav,
            "favorite_fair_probability": fair[0] if fair and fav == "H" else (fair[2] if fair else None),
            "one_x_two": {"home": m.one_x_two_home, "draw": m.one_x_two_draw, "away": m.one_x_two_away},
            "ah": {
                "selected_side_line": selected_line,
                "selected_side_price": selected_price,
                "home_line": m.ah_home_line,
                "home_price": m.ah_home_odds,
                "away_line": m.ah_away_line,
                "away_price": m.ah_away_odds,
            },
            "ou": {"line": m.ou_line, "over_price": m.over_odds, "under_price": m.under_odds},
            "quote_timestamp_verified": False,
        }
        snapshots.append(snap)
        core = 1.8 <= selected_price <= 2.2
        audits.append({
            "football_day": day, "fixture_id": fid, "provider": snap["provider"], "bookmaker": BOOKMAKER,
            "league": m.league, "home": m.home, "away": m.away, "kickoff": snap["kickoff"],
            "observed_at": now.isoformat(), "scheduled_target_at": snap["scheduled_target_at"],
            "observation_timing": snap["observation_timing"], "eligibility_status": "MATCH" if core else "NOT_MATCH",
            "eligibility_reason": "AH_CORE_PRICE" if core else "AH_OUTSIDE_CORE_PRICE", "research_population": True,
        })

    total_s = _merge_jsonl(root / SNAPSHOT_PATH, snapshots, ("observed_at", "fixture_id")) if snapshots else 0
    total_a = _merge_jsonl(root / AUDIT_PATH, audits, ("observed_at", "fixture_id")) if audits else 0
    report.update(
        status="RESEARCH_V2_OBSERVED" if snapshots else "ZERO_USABLE_FIXTURES",
        source_rows=len(markets), source_rows_in_football_day=source_rows_in_day,
        date_parse_failures=parse_failures, parsed_date_counts=parsed_dates, source_date_samples=source_date_samples, football_window_start=ws.isoformat(), football_window_end=we.isoformat(), strict_snapshots_this_run=len(snapshots),
        core_price_snapshots=sum(1 for s in snapshots if 1.8 <= s["ah"]["selected_side_price"] <= 2.2),
        persisted_snapshot_rows=total_s, persisted_audit_rows=total_a,
    )
    return _write(root, report)


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False))
