from __future__ import annotations

import json, urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SNAP=Path("data/normalized/europe_pinnacle_research_v2_snapshots.jsonl")
RESULTS=Path("data/normalized/oddspapi_finished_results.jsonl")
REPORT=Path("reports/sofascore_pinnwire_coverage_probe.json")
BASE="https://www.sofascore.com/api/v1/sport/football/scheduled-events"


def _rows(path):
    out=[]
    if not path.exists(): return out
    for line in path.read_text(encoding="utf-8").splitlines():
        try: x=json.loads(line)
        except json.JSONDecodeError: continue
        if isinstance(x,dict): out.append(x)
    return out


def _norm(v): return str(v or "").strip().casefold()


def _utc(v):
    try:
        if isinstance(v,(int,float)): return datetime.fromtimestamp(v,tz=timezone.utc)
        d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    except (TypeError,ValueError,OSError): return None


def _fetch(day):
    req=urllib.request.Request(f"{BASE}/{day}",headers={"Accept":"application/json","User-Agent":"football-odds-scanner/coverage-probe"})
    with urllib.request.urlopen(req,timeout=30) as r: data=json.loads(r.read().decode())
    return data.get("events",[]) if isinstance(data,dict) else []


def run(root=Path(".")):
    snaps=_rows(root/SNAP); settled={str(x.get("fixture_id")) for x in _rows(root/RESULTS)}
    missing={}
    for s in snaps:
        fid=str(s.get("fixture_id") or "")
        ko=_utc(s.get("kickoff"))
        if not fid.startswith("pinnwire:") or fid in settled or not ko: continue
        missing.setdefault(fid,s)
    days=sorted({(_utc(s.get("kickoff")).date().isoformat()) for s in missing.values() if _utc(s.get("kickoff"))})
    index={}; fetched=0; failures=[]
    for day in days:
        try: events=_fetch(day); fetched+=len(events)
        except Exception as exc: failures.append({"day":day,"error":f"{type(exc).__name__}: {exc}"}); continue
        for e in events:
            ko=_utc(e.get("startTimestamp")); h=e.get("homeTeam") or {}; a=e.get("awayTeam") or {}
            if not ko: continue
            key=(_norm(h.get("name")),_norm(a.get("name")),ko.isoformat())
            index.setdefault(key,[]).append(e)
    exact=0; ambiguous=0; by_day=Counter(); samples=[]
    for fid,s in missing.items():
        ko=_utc(s.get("kickoff")); key=(_norm(s.get("home")),_norm(s.get("away")),ko.isoformat())
        matches=index.get(key,[])
        if len(matches)==1:
            exact+=1; by_day[ko.date().isoformat()]+=1
            if len(samples)<30:
                e=matches[0]; samples.append({"fixture_id":fid,"home":s.get("home"),"away":s.get("away"),"kickoff":ko.isoformat(),"sofascore_event_id":e.get("id"),"status":(e.get("status") or {}).get("type"),"home_score":(e.get("homeScore") or {}).get("current"),"away_score":(e.get("awayScore") or {}).get("current")})
        elif len(matches)>1: ambiguous+=1
    report={"schema_version":"1.0","classification":"SOFASCORE_PINNWIRE_COVERAGE_PROBE_ONLY","settlement_effect":"NONE","promotion_eligible":False,"fuzzy_matching_used":False,"matching_policy":"EXACT_STRIP_CASEFOLD_HOME_AWAY_AND_EXACT_UTC_KICKOFF","missing_pinnwire_fixtures":len(missing),"days_requested":len(days),"events_fetched":fetched,"exact_unique_matches":exact,"exact_coverage_pct":round(100*exact/len(missing),2) if missing else 0,"ambiguous_exact_matches":ambiguous,"exact_by_day":dict(sorted(by_day.items())),"request_failures":failures,"samples":samples}
    p=root/REPORT;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8");return report

if __name__=="__main__": print(json.dumps(run(),ensure_ascii=False))
