from __future__ import annotations

import json
import os
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ENV_KEY = "API_FOOTBALL_KEY"
BASE_URL = "https://v3.football.api-sports.io"
BANGKOK = ZoneInfo("Asia/Bangkok")
BIG5_LEAGUES = {39: "Premier League", 61: "Ligue 1", 78: "Bundesliga", 135: "Serie A", 140: "La Liga"}
FIXTURES_PATH = Path("data/normalized/api_football_fixtures.jsonl")
REPORT_PATH = Path("reports/api_football_shadow_health.json")
ODDS_PROBE_PATH = Path("reports/api_football_odds_probe.json")


def _get(path: str, key: str, params: dict | None = None, timeout: int = 45) -> dict:
    query = f"?{urlencode(params)}" if params else ""
    request = Request(f"{BASE_URL}{path}{query}", headers={"x-apisports-key": key})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_fixture(item: dict, observed_at: str) -> dict | None:
    fixture = item.get("fixture") if isinstance(item.get("fixture"), dict) else {}
    league = item.get("league") if isinstance(item.get("league"), dict) else {}
    teams = item.get("teams") if isinstance(item.get("teams"), dict) else {}
    goals = item.get("goals") if isinstance(item.get("goals"), dict) else {}
    status = fixture.get("status") if isinstance(fixture.get("status"), dict) else {}
    league_id = league.get("id")
    fixture_id = fixture.get("id")
    kickoff = fixture.get("date")
    if league_id not in BIG5_LEAGUES or fixture_id is None or not kickoff:
        return None
    short = str(status.get("short") or "")
    finished = short in {"FT", "AET", "PEN"} and goals.get("home") is not None and goals.get("away") is not None
    return {
        "provider": "api_football",
        "provider_fixture_id": str(fixture_id),
        "league_id": int(league_id),
        "league": str(league.get("name") or BIG5_LEAGUES[league_id]),
        "season": league.get("season"),
        "kickoff": str(kickoff),
        "home": str((teams.get("home") or {}).get("name") or ""),
        "away": str((teams.get("away") or {}).get("name") or ""),
        "status": short,
        "ft_home_goals": int(goals["home"]) if finished else None,
        "ft_away_goals": int(goals["away"]) if finished else None,
        "finished": finished,
        "observed_at": observed_at,
        "identity_semantics": "API_FOOTBALL_PROVIDER_FIXTURE_ID_EXACT",
        "research_only": True,
    }


def _read(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        fixture_id = str(row.get("provider_fixture_id") or "")
        if fixture_id:
            rows[fixture_id] = row
    return rows


def _write(path: Path, rows: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows.values(), key=lambda row: (row.get("kickoff", ""), row.get("provider_fixture_id", "")))
    path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in ordered), encoding="utf-8")


def collect(root: Path = Path("."), *, key: str | None = None, today: date | None = None, get_fn=_get) -> dict:
    api_key = (key or os.getenv(ENV_KEY, "")).strip()
    now = datetime.now(timezone.utc)
    report = {
        "schema_version": "1.0",
        "provider": "api_football",
        "generated_at": now.isoformat(),
        "mode": "SHADOW_FIXTURE_RESULT_ONLY",
        "promotion_eligible": False,
        "odds_ingested": False,
    }
    report_path = root / REPORT_PATH
    if not api_key:
        report.update(status="API_KEY_NOT_CONFIGURED", requests_used=0)
    else:
        local_day = today or now.astimezone(BANGKOK).date()
        days = [local_day - timedelta(days=1), local_day]
        existing = _read(root / FIXTURES_PATH)
        selected: list[dict] = []
        errors: list[str] = []
        current = limit = None
        for day in days:
            try:
                payload = get_fn("/fixtures", api_key, {"date": day.isoformat(), "timezone": "Asia/Bangkok"})
                request_info = payload.get("results")
                response_rows = payload.get("response") if isinstance(payload.get("response"), list) else []
                api_errors = payload.get("errors")
                if api_errors:
                    errors.append(f"{day.isoformat()}:API_ERRORS:{api_errors}")
                for item in response_rows:
                    row = normalize_fixture(item, now.isoformat())
                    if row:
                        selected.append(row)
            except Exception as exc:
                errors.append(f"{day.isoformat()}:{type(exc).__name__}:{exc}")
        try:
            status_payload = get_fn("/status", api_key)
            account = status_payload.get("response") if isinstance(status_payload.get("response"), dict) else {}
            requests = account.get("requests") if isinstance(account.get("requests"), dict) else {}
            current, limit = requests.get("current"), requests.get("limit_day")
        except Exception as exc:
            errors.append(f"STATUS:{type(exc).__name__}:{exc}")
        for row in selected:
            existing[row["provider_fixture_id"]] = row
        _write(root / FIXTURES_PATH, existing)
        report.update(
            status="SHADOW_OK" if selected and not errors else ("SHADOW_PARTIAL" if selected else "SHADOW_FAILED"),
            requests_used=3,
            dates=[day.isoformat() for day in days],
            big5_rows_observed=len(selected),
            finished_rows_observed=sum(1 for row in selected if row["finished"]),
            persisted_rows=len(existing),
            request_count=current,
            request_limit_day=limit,
            request_remaining=(limit - current) if isinstance(limit, int) and isinstance(current, int) else None,
            errors=errors,
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def probe_odds(root: Path = Path("."), *, key: str | None = None, get_fn=_get) -> dict:
    """Validate API-Football Pinnacle Asian Handicap semantics before provider promotion."""
    api_key = (key or os.getenv(ENV_KEY, "")).strip()
    now = datetime.now(timezone.utc)
    report = {
        "schema_version": "1.0",
        "provider": "api_football",
        "generated_at": now.isoformat(),
        "mode": "PINNACLE_ASIAN_HANDICAP_ODDS_PROBE",
        "promotion_eligible": False,
        "requests_used": 0,
    }
    out = root / ODDS_PROBE_PATH
    if not api_key:
        report["status"] = "API_KEY_NOT_CONFIGURED"
    else:
        try:
            bookmakers = get_fn("/odds/bookmakers", api_key, {"search": "Pinnacle"})
            report["requests_used"] += 1
            bets = get_fn("/odds/bets", api_key, {"search": "Handicap"})
            report["requests_used"] += 1
            b_rows = bookmakers.get("response") if isinstance(bookmakers.get("response"), list) else []
            bet_rows = bets.get("response") if isinstance(bets.get("response"), list) else []
            pinnacle = next((x for x in b_rows if "pinnacle" in str(x.get("name", "")).lower()), None)
            handicap = [x for x in bet_rows if "handicap" in str(x.get("name", "")).lower()]
            report["bookmaker_matches"] = b_rows
            report["handicap_bet_matches"] = handicap
            if not pinnacle or not handicap:
                report["status"] = "REFERENCE_NOT_FOUND"
            else:
                # One tightly-scoped request is enough to prove response shape/coverage.
                day = now.astimezone(BANGKOK).date().isoformat()
                payload = get_fn("/odds", api_key, {
                    "date": day,
                    "bookmaker": pinnacle.get("id"),
                    "bet": handicap[0].get("id"),
                })
                report["requests_used"] += 1
                rows = payload.get("response") if isinstance(payload.get("response"), list) else []
                report["date"] = day
                report["pinnacle_bookmaker"] = pinnacle
                report["selected_handicap_bet"] = handicap[0]
                report["odds_results"] = len(rows)
                report["paging"] = payload.get("paging")
                report["api_errors"] = payload.get("errors")
                report["sample"] = rows[:2]
                report["status"] = "ODDS_PROBE_OK" if rows and not payload.get("errors") else "ODDS_PROBE_EMPTY"
        except Exception as exc:
            report["status"] = "ODDS_PROBE_FAILED"
            report["errors"] = [f"{type(exc).__name__}: {exc}"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


V2_SNAPSHOT_PATH = Path("data/normalized/europe_pinnacle_research_v2_snapshots.jsonl")
V2_REPORT_PATH = Path("reports/europe_pinnacle_research_v2_status.json")
V2_LEDGER_PATH = Path("data/normalized/research_v2_slot_ledger.jsonl")

def _pick_balanced(values):
    pairs = {}
    for x in values or []:
        v=str(x.get("value") or ""); parts=v.split()
        if len(parts)<2: continue
        side=parts[0].lower()
        try: line=float(parts[-1]); odd=float(x.get("odd"))
        except (ValueError,TypeError): continue
        pairs[(side,line)]=odd
    candidates=[]
    for (side,line),odd in pairs.items():
        if side!="home": continue
        away=pairs.get(("away",-line))
        if away is None: continue
        candidates.append((abs(odd-away),line,odd,away))
    return min(candidates) if candidates else None

def collect_v2_odds(root: Path=Path("."), *, key: str|None=None, target_at: str|None=None, get_fn=_get) -> dict:
    api_key=(key or os.getenv(ENV_KEY,"")).strip(); now=datetime.now(timezone.utc); local=now.astimezone(BANGKOK)
    target=target_at or os.getenv("RESEARCH_V2_FORCE_TARGET_AT","").strip() or local.replace(hour=21,minute=0,second=0,microsecond=0).isoformat()
    report={"schema_version":"3.0","generated_at":now.isoformat(),"classification":"PINNACLE_RESEARCH_V2","provider":"api_football","bookmaker":"pinnacle","scheduled_target_at":target,"actual_observed_at":local.isoformat(),"research_only":True,"production_promotion_allowed":False,"requests_used":0}
    if not api_key: report["status"]="API_KEY_NOT_CONFIGURED"
    else:
        try:
            day=local.date().isoformat(); rows=[]
            # Free tier allows only pages 1-3. Use the global Pinnacle football feed
            # so weekday cup/international/non-Big5 matches are not silently excluded.
            page=1
            while True:
                payload=get_fn("/odds",api_key,{"date":day,"bookmaker":4,"page":page}); report["requests_used"]+=1
                if payload.get("errors"): raise RuntimeError(str(payload["errors"]))
                batch=payload.get("response") if isinstance(payload.get("response"),list) else []; rows.extend(batch)
                paging=payload.get("paging") or {}; total=min(int(paging.get("total") or 1),3)
                if page>=total: break
                page+=1
            snaps=[]
            for item in rows:
                league=item.get("league") or {}; fixture=item.get("fixture") or {}
                if league.get("id") not in BIG5_LEAGUES: continue
                try: ko=datetime.fromisoformat(str(fixture.get("date")).replace("Z","+00:00")).astimezone(timezone.utc)
                except Exception: continue
                if ko<=now: continue
                book=next((b for b in item.get("bookmakers",[]) if b.get("id")==4),None)
                if not book: continue
                bets={int(b.get("id")):b for b in book.get("bets",[]) if b.get("id") is not None}
                one=bets.get(1); ah=bets.get(4); ou=bets.get(5)
                # AH is the hard requirement for Research V2. 1X2 and O/U enrich
                # the row when the provider publishes them, but must not suppress
                # an otherwise usable Asian Handicap observation.
                if not ah: continue
                onevals={str(x.get("value")).lower():float(x.get("odd")) for x in (one or {}).get("values",[]) if x.get("odd")}
                hp=onevals.get("home"); dp=onevals.get("draw"); ap=onevals.get("away")
                pick=_pick_balanced(ah.get("values",[]))
                oupick=_pick_balanced([{"value":str(x.get("value")).replace("Over","Home").replace("Under","Away"),"odd":x.get("odd")} for x in (ou or {}).get("values",[])])
                if not pick: continue
                if all([hp,dp,ap]):
                    inv=[1/hp,1/dp,1/ap]; tot=sum(inv); fh,fd,fa=[x/tot for x in inv]; fav="H" if fh>=fa else "A"
                else:
                    fh=fd=fa=None
                    # With no 1X2 market, the balanced AH line itself identifies
                    # the giving side. Pick'em is intentionally skipped.
                    fav=None
                _,line,hprice,aprice=pick
                if fav is None:
                    if line<0: fav="H"
                    elif line>0: fav="A"
                    else: continue
                if oupick: _,ouline,oprice,uprice=oupick
                else: ouline=oprice=uprice=None
                snap={"fixture_id":f"api_football:{fixture.get('id')}","provider_fixture_id":str(fixture.get("id")),"tournament_id":league.get("id"),"universe":"PINNACLE_RESEARCH_V2","league":league.get("name"),"country":league.get("country"),"kickoff":ko.isoformat(),"home":None,"away":None,"bookmaker":"pinnacle","provider":"api_football","observed_at":now.isoformat(),"source_semantics":"CURRENT_API_FOOTBALL_PINNACLE_BALANCED_LINE_OBSERVED","mainline_verified":False,"line_selection_semantics":"MOST_BALANCED_AVAILABLE_PAIR","favorite_side":fav,"favorite_fair_probability":round(fh if fav=="H" else fa,8) if fh is not None else None,"one_x_two":{"home":hp,"draw":dp,"away":ap,"fair_home":round(fh,8) if fh is not None else None,"fair_draw":round(fd,8) if fd is not None else None,"fair_away":round(fa,8) if fa is not None else None},"ah":{"home_line":line,"home_price":hprice,"away_line":-line,"away_price":aprice,"selected_side_line":line if fav=="H" else -line,"selected_side_price":hprice if fav=="H" else aprice,"opposite_side_price":aprice if fav=="H" else hprice},"ou":{"line":ouline,"over_price":oprice,"under_price":uprice},"promotion_eligible":False,"football_day":day,"research_only":True,"scheduled_target_at":target}
                snaps.append(snap)
            existing=[]
            p=root/V2_SNAPSHOT_PATH
            if p.exists():
                for line in p.read_text(encoding="utf-8").splitlines():
                    try: existing.append(json.loads(line))
                    except: pass
            keys={(str(x.get("fixture_id")),str(x.get("observed_at"))) for x in existing}
            existing.extend(x for x in snaps if (str(x.get("fixture_id")),str(x.get("observed_at"))) not in keys)
            p.parent.mkdir(parents=True,exist_ok=True); p.write_text("".join(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\\n" for x in existing),encoding="utf-8")
            report.update(status="RESEARCH_V2_OBSERVED" if snaps else "ZERO_FIXTURES",football_day=day,api_rows_returned=len(rows),football_day_fixtures=len(snaps),strict_snapshots_this_run=len(snaps),persisted_snapshot_rows=len(existing),coverage_mode="API_FOOTBALL_GLOBAL_PINNACLE_PAGE_1_3")
        except Exception as exc: report.update(status="API_REQUEST_FAILED",errors=[f"{type(exc).__name__}: {exc}"])
    rp=root/V2_REPORT_PATH; rp.parent.mkdir(parents=True,exist_ok=True); rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"); return report


if __name__ == "__main__":
    if os.getenv("API_FOOTBALL_V2_SCAN", "").strip().lower() in {"1","true","yes"}:
        print(json.dumps(collect_v2_odds(), ensure_ascii=False)); raise SystemExit(0)
    shadow = collect()
    if os.getenv("API_FOOTBALL_ODDS_PROBE", "").strip().lower() in {"1", "true", "yes"}:
        print(json.dumps({"shadow": shadow, "odds_probe": probe_odds()}, ensure_ascii=False))
    else:
        print(json.dumps(shadow, ensure_ascii=False))
