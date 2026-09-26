from __future__ import annotations
import json
from datetime import datetime,time as dtime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from .europe_pinnacle_discovery import SNAPSHOT_PATH,AUDIT_PATH,_merge_jsonl
from .propline_provider import fetch

BKK=ZoneInfo("Asia/Bangkok")
REPORT=Path("reports/propline_research_v2_status.json")

def _football_day(now):
    local=now.astimezone(BKK); label=local.date()-timedelta(days=1) if local.time()<dtime(6) else local.date()
    return datetime.combine(label,dtime(12),BKK),datetime.combine(label+timedelta(days=1),dtime(6),BKK),label.isoformat()
def _dt(v):
    try:return datetime.fromisoformat(str(v).replace("Z","+00:00")).astimezone(timezone.utc)
    except:return None
def _devig3(h,d,a):
    if not all(x and x>1 for x in (h,d,a)): return None
    raw=(1/h,1/d,1/a); s=sum(raw); return tuple(x/s for x in raw)
def run(root=Path(".")):
    now=datetime.now(timezone.utc); ws,we,day=_football_day(now)
    try: rows,errors=fetch()
    except Exception as e: rows=[]; errors=[f"{type(e).__name__}: {e}"]
    snaps=[]; audits=[]; in_day=0; kickoff_dates={}; kickoff_samples=[]
    for m in rows:
        ko=_dt(m.get("kickoff"))
        if ko:
            local_date=ko.astimezone(BKK).date().isoformat()
            kickoff_dates[local_date]=kickoff_dates.get(local_date,0)+1
            if len(kickoff_samples)<20: kickoff_samples.append({"sport":m.get("sport"),"home":m.get("home"),"away":m.get("away"),"kickoff":m.get("kickoff"),"local":ko.astimezone(BKK).isoformat(),"bookmaker":m.get("bookmaker")})
        if not ko or not (ws.astimezone(timezone.utc)<=ko<we.astimezone(timezone.utc)): continue
        in_day+=1
        hl=m.get("ah_home_line"); hp=m.get("ah_home_odds"); al=m.get("ah_away_line"); ap=m.get("ah_away_odds")
        if None in (hl,hp,al,ap): continue
        fair=_devig3(m.get("one_x_two_home"),m.get("one_x_two_draw"),m.get("one_x_two_away"))
        if float(hl)<0:fav="H"
        elif float(hl)>0:fav="A"
        elif fair:fav="H" if fair[0]>=fair[2] else "A"
        else:continue
        line=hl if fav=="H" else al; price=hp if fav=="H" else ap
        if not (1.01<float(price)<20): continue
        fid=f"propline:{m['sport']}:{m['event_id']}"
        # Observation time identifies the scan round. A bookmaker's last price
        # change can predate several scans and must never deduplicate them.
        observed=now.isoformat()
        snap={"provider":"propline","source":f"propline:{m['bookmaker']}","bookmaker":m["bookmaker"],"fixture_id":fid,"football_day":day,"observed_at":observed,"price_changed_at":m.get("bookmaker_updated_at"),"scheduled_target_at":now.astimezone(BKK).isoformat(),"observation_timing":"SCHEDULED_FREE_SCAN","research_only":True,"league":m["sport"],"home":m["home"],"away":m["away"],"kickoff":ko.isoformat(),"favorite_side":fav,"favorite_fair_probability":fair[0] if fair and fav=="H" else (fair[2] if fair else None),"one_x_two":{"home":m.get("one_x_two_home"),"draw":m.get("one_x_two_draw"),"away":m.get("one_x_two_away")},"ah":{"selected_side_line":line,"selected_side_price":price,"home_line":hl,"home_price":hp,"away_line":al,"away_price":ap},"ou":{"line":m.get("ou_line"),"over_price":m.get("over_odds"),"under_price":m.get("under_odds")},"quote_timestamp_verified":bool(m.get("bookmaker_updated_at"))}
        snaps.append(snap); core=1.8<=float(price)<=2.2
        audits.append({"football_day":day,"fixture_id":fid,"provider":"propline","bookmaker":m["bookmaker"],"league":m["sport"],"home":m["home"],"away":m["away"],"kickoff":ko.isoformat(),"observed_at":observed,"scheduled_target_at":snap["scheduled_target_at"],"observation_timing":snap["observation_timing"],"eligibility_status":"MATCH" if core else "NOT_MATCH","eligibility_reason":"AH_CORE_PRICE" if core else "AH_OUTSIDE_CORE_PRICE","research_population":True})
    ts=_merge_jsonl(root/SNAPSHOT_PATH,snaps,("observed_at","fixture_id")) if snaps else 0
    ta=_merge_jsonl(root/AUDIT_PATH,audits,("observed_at","fixture_id")) if audits else 0
    report={"schema_version":"1.1","provider":"propline","football_day":day,"generated_at":now.isoformat(),"status":"RESEARCH_V2_OBSERVED" if snaps else "ZERO_USABLE_FIXTURES","source_rows":len(rows),"source_rows_in_football_day":in_day,"strict_snapshots_this_run":len(snaps),"core_price_snapshots":sum(1 for s in snaps if 1.8<=float(s["ah"]["selected_side_price"])<=2.2),"persisted_snapshot_rows":ts,"persisted_audit_rows":ta,"kickoff_date_counts":kickoff_dates,"kickoff_samples":kickoff_samples,"errors":errors[:10]}
    p=root/REPORT;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(report,indent=2),encoding="utf-8");return report
if __name__=="__main__":print(json.dumps(run()))
