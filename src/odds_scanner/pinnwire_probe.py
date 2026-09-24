from __future__ import annotations
import json, urllib.parse, urllib.request, hashlib, os
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime, timezone

BASE="https://pinnwire.com/kit/v1/prematch/fixtures"

def probe():
    now=datetime.now(timezone.utc).isoformat()
    try:
        url=BASE+"?"+urllib.parse.urlencode({"sport_id":1,"key":"demo"})
        req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"football-odds-scanner/0.1"})
        with urllib.request.urlopen(req,timeout=20) as r:
            payload=json.loads(r.read().decode())
        events=payload.get("events") or payload.get("data") or []
        samples=[]; spreads=0; future=0; core_ah=0; totals25=0
        for ev in events:
            periods=ev.get("periods") or {}
            p0=periods.get("num_0") or periods.get("0") or {}
            sp=p0.get("spreads") or {}
            if sp: spreads+=1
            try:
                st=ev.get("starts") or ev.get("start_time"); future += int(bool(st) and datetime.fromisoformat(st.replace("Z","+00:00")) > datetime.now(timezone.utc))
            except Exception: pass
            if isinstance(sp,dict) and any(1.8 <= float(v.get("home",0)) <= 2.2 or 1.8 <= float(v.get("away",0)) <= 2.2 for v in sp.values() if isinstance(v,dict)): core_ah+=1
            tots=p0.get("totals") or {}
            if isinstance(tots,dict) and "2.5" in tots: totals25+=1
            if len(samples)<3: samples.append({"id":ev.get("id"),"home":ev.get("home"),"away":ev.get("away"),"starts":ev.get("starts") or ev.get("start_time"),"spread_keys":list(sp)[:5] if isinstance(sp,dict) else [], "period_keys":list(periods)[:8] if isinstance(periods,dict) else [], "period0":p0})
        return {"provider":"pinnwire_demo_prematch","generated_at":now,"status":"OK" if events else "NO_EVENTS","events":len(events),"events_with_spreads":spreads,"future_events":future,"events_with_core_ah_1_8_2_2":core_ah,"events_with_total_2_5":totals25,"provider_generated_at":payload.get("generated_at"),"samples":samples}
    except Exception as e:
        return {"provider":"pinnwire_demo","generated_at":now,"status":"UNAVAILABLE","events":0,"errors":[f"{type(e).__name__}: {e}"]}



BANGKOK=ZoneInfo("Asia/Bangkok")
SNAP=Path("data/normalized/europe_pinnacle_research_v2_snapshots.jsonl")
REPORT=Path("reports/pinnwire_research_v2_status.json")

def _balanced(spreads):
    best=None
    for _,v in (spreads or {}).items():
        if not isinstance(v,dict): continue
        try: h=float(v.get("home")); a=float(v.get("away")); line=float(v.get("hdp"))
        except Exception: continue
        score=abs(h-a)
        if best is None or score<best[0]: best=(score,line,h,a)
    return best

def collect():
    now=datetime.now(timezone.utc); local=now.astimezone(BANGKOK); day=local.date().isoformat()
    report={"schema_version":"3.1","generated_at":now.isoformat(),"classification":"PINNACLE_RESEARCH_V2","provider":"pinnwire","bookmaker":"pinnacle","football_day":day,"requests_used":1}
    try:
        url=BASE+"?"+urllib.parse.urlencode({"sport_id":1,"key":"demo"})
        req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"football-odds-scanner/0.1"})
        with urllib.request.urlopen(req,timeout=30) as r: payload=json.loads(r.read().decode())
        events=payload.get("events") or payload.get("data") or []; snaps=[]
        for ev in events:
            try: ko=datetime.fromisoformat(str(ev.get("starts") or ev.get("start_time")).replace("Z","+00:00")).astimezone(timezone.utc)
            except Exception: continue
            if ko<=now or ko.astimezone(BANGKOK).date().isoformat()!=day: continue
            p0=(ev.get("periods") or {}).get("num_0") or (ev.get("periods") or {}).get("0") or {}
            pick=_balanced(p0.get("spreads") or {})
            if not pick: continue
            _,line,hp,ap=pick
            if line==0: continue
            fav="H" if line<0 else "A"
            totals=p0.get("totals") or {}; t25=totals.get("2.5") or {}
            home=str(ev.get("home") or ""); away=str(ev.get("away") or "")
            rawid=str(ev.get("id") or "")
            stable=rawid or hashlib.sha1(f"{home}|{away}|{ko.isoformat()}".encode()).hexdigest()[:16]
            snaps.append({"fixture_id":f"pinnwire:{stable}","provider_fixture_id":rawid or stable,"result_match_key":hashlib.sha1(f"{home.strip().casefold()}|{away.strip().casefold()}|{ko.isoformat()}".encode()).hexdigest(),"result_match_policy":"EXACT_NORMALIZED_TEAMS_AND_KICKOFF_ONLY","universe":"PINNACLE_RESEARCH_V2","league":ev.get("league") or ev.get("league_name"),"country":ev.get("country"),"kickoff":ko.isoformat(),"home":home,"away":away,"bookmaker":"pinnacle","provider":"pinnwire","observed_at":now.isoformat(),"source_semantics":"PINNWIRE_PREMATCH_FULL_SNAPSHOT","mainline_verified":False,"line_selection_semantics":"MOST_BALANCED_AVAILABLE_PAIR","favorite_side":fav,"ah":{"home_line":line,"home_price":hp,"away_line":-line,"away_price":ap,"selected_side_line":line if fav=="H" else -line,"selected_side_price":hp if fav=="H" else ap,"opposite_side_price":ap if fav=="H" else hp},"ou":{"line":2.5 if t25 else None,"over_price":t25.get("over"),"under_price":t25.get("under")},"promotion_eligible":False,"football_day":day,"research_only":True})
        existing=[]
        if SNAP.exists():
            for line in SNAP.read_text(encoding="utf-8").splitlines():
                try: existing.append(json.loads(line))
                except Exception: pass
        keys={(str(x.get("fixture_id")),str(x.get("observed_at"))) for x in existing}
        existing.extend(x for x in snaps if (str(x.get("fixture_id")),str(x.get("observed_at"))) not in keys)
        SNAP.parent.mkdir(parents=True,exist_ok=True); SNAP.write_text("".join(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n" for x in existing),encoding="utf-8")
        report.update(status="RESEARCH_V2_OBSERVED" if snaps else "ZERO_FIXTURES",provider_events=len(events),strict_snapshots_this_run=len(snaps),persisted_snapshot_rows=len(existing),result_match_keys=sum(1 for x in snaps if x.get("result_match_key")),coverage_mode="PINNWIRE_PREMATCH_ALL_SOCCER_TODAY_BANGKOK")
    except Exception as e: report.update(status="API_REQUEST_FAILED",errors=[f"{type(e).__name__}: {e}"])
    REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"); return report

if __name__=="__main__": print(json.dumps(collect() if os.getenv("PINNWIRE_V2_SCAN","").lower() in {"1","true","yes"} else probe(),ensure_ascii=False))
