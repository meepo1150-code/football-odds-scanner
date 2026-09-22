from __future__ import annotations
import json, os, time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from .five_dollar_provider import ENV_KEY, _get
from .europe_pinnacle_discovery import SNAPSHOT_PATH, AUDIT_PATH, _merge_jsonl, _football_day_bounds
BKK=ZoneInfo("Asia/Bangkok"); REPORT=Path("reports/five_dollar_live_research_v2_status.json"); BOOKMAKER="bet365"
def _f(v):
    try:
        x=float(v); return x if x>1 else None
    except (TypeError,ValueError): return None
def _line(v):
    try:return float(v)
    except (TypeError,ValueError):return None
def _devig(h,d,a):
    if not all(x and x>1 for x in (h,d,a)): return (None,None,None)
    raw=[1/h,1/d,1/a]; s=sum(raw); return tuple(x/s for x in raw)
def _count(p): return len(p.read_text(encoding="utf-8").splitlines()) if p.exists() else 0
def _write(root,r):
    p=root/REPORT;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8");return r
def run(root=Path(".")):
    key=os.getenv(ENV_KEY,"").strip(); now=datetime.now(timezone.utc); ws,we,day=_football_day_bounds(now)
    report={"schema_version":"1.0","provider":"5dollarfootballapi_free","bookmaker":BOOKMAKER,"football_day":day,"generated_at":now.isoformat(),"observed_at":now.isoformat(),"research_only":True,"snapshot_semantics":"LATEST_PREMATCH_OBSERVED_BY_SCANNER_QUOTE_TIMESTAMP_UNVERIFIED","requests_used":0}
    if not key: report["status"]="API_KEY_NOT_CONFIGURED"; return _write(root,report)
    try: payload=_get("/fixtures",key,{"status":"scheduled","start_time":int(ws.timestamp()),"end_time":int(we.timestamp()),"per_page":50}); report["requests_used"]+=1
    except Exception as e: report.update(status="API_REQUEST_FAILED",errors=[f"{type(e).__name__}: {e}"]); return _write(root,report)
    fixtures=payload.get("data") or []; snaps=[]; audits=[]; errors=[]
    for fx in fixtures:
        fid=str(fx.get("id") or "")
        if not fid: continue
        try:
            time.sleep(3.2); op=_get(f"/fixtures/{fid}/odds",key); report["requests_used"]+=1
            books=(op.get("data") or {}).get("bookmakers") or []; book=next((b for b in books if str(b.get("slug","")).lower()==BOOKMAKER),None)
            if not book: raise ValueError("bet365 missing")
            odds=book.get("odds") or {}; x=(odds.get("1x2") or {}).get("closing") or {}; ah=(odds.get("asian_handicap") or {}).get("closing") or {}; ou=(odds.get("goal_line") or {}).get("closing") or {}
            h,d,a=_f(x.get("home")),_f(x.get("draw")),_f(x.get("away")); fh,_,fa=_devig(h,d,a); hl=_line(ah.get("line")); hp,ap=_f(ah.get("home")),_f(ah.get("away"))
            if None in (fh,fa,hl,hp,ap): raise ValueError("required 1X2/AH closing market missing")
            fav="H" if fh>=fa else "A"; favprob=fh if fav=="H" else fa; favline=hl if fav=="H" else -hl; favprice=hp if fav=="H" else ap
            teams=fx.get("teams") or {}; league=fx.get("league") or {}; kickoff=str(fx.get("kickoff_utc") or ""); home=str((teams.get("home") or {}).get("name") or ""); away=str((teams.get("away") or {}).get("name") or ""); sid=f"5dollar:{fid}"
            snap={"provider":"5dollarfootballapi_free","source":"5dollarfootballapi:bet365:latest_pre_match","bookmaker":BOOKMAKER,"fixture_id":sid,"provider_fixture_id":fid,"football_day":day,"observed_at":now.isoformat(),"scheduled_target_at":now.astimezone(BKK).isoformat(),"observation_timing":"MANUAL_LIVE","research_only":True,"league":str(league.get("name") or league.get("id") or ""),"home":home,"away":away,"kickoff":kickoff,"favorite_side":fav,"favorite_fair_probability":favprob,"one_x_two":{"home":h,"draw":d,"away":a},"ah":{"selected_side_line":favline,"selected_side_price":favprice,"home_line":hl,"home_price":hp,"away_line":-hl,"away_price":ap},"ou":{"line":_line(ou.get("line")),"over_price":_f(ou.get("over")),"under_price":_f(ou.get("under"))},"quote_timestamp_verified":False}
            snaps.append(snap); audits.append({"football_day":day,"fixture_id":sid,"provider_fixture_id":fid,"provider":"5dollarfootballapi_free","bookmaker":BOOKMAKER,"league":snap["league"],"home":home,"away":away,"kickoff":kickoff,"observed_at":now.isoformat(),"scheduled_target_at":snap["scheduled_target_at"],"observation_timing":"MANUAL_LIVE","eligibility_status":"MATCH" if 1.8<=favprice<=2.2 else "NOT_MATCH","eligibility_reason":"AH_CORE_PRICE" if 1.8<=favprice<=2.2 else "AH_OUTSIDE_CORE_PRICE","research_population":True})
        except Exception as e: errors.append(f"{fid}:{type(e).__name__}:{e}")
    total_s=_merge_jsonl(root/SNAPSHOT_PATH,snaps,("observed_at","fixture_id")) if snaps else _count(root/SNAPSHOT_PATH); total_a=_merge_jsonl(root/AUDIT_PATH,audits,("observed_at","fixture_id")) if audits else _count(root/AUDIT_PATH)
    report.update(status="RESEARCH_V2_OBSERVED" if snaps else "ZERO_USABLE_FIXTURES",fixtures_returned=len(fixtures),strict_snapshots_this_run=len(snaps),core_price_snapshots=sum(1 for s in snaps if 1.8<=s["ah"]["selected_side_price"]<=2.2),persisted_snapshot_rows=total_s,persisted_audit_rows=total_a,errors=errors[:20]); return _write(root,report)
if __name__=="__main__": print(json.dumps(run(),ensure_ascii=False))
