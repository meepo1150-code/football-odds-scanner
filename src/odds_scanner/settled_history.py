from __future__ import annotations

import json
from pathlib import Path
from .asian_settlement import settle_asian_handicap, settle_asian_total

INPUT=Path("data/normalized/oddspapi_prematch_joined.jsonl")
OUTPUT=Path("data/normalized/oddspapi_settled_history.jsonl")
REPORT=Path("reports/oddspapi_settled_history.json")

def _pack(x): return {"settlement":x.settlement.value,"profit_units":round(x.profit_units,8),"return_units":round(x.return_units,8)}
def _ends(ticks):
    good=[t for t in (ticks or []) if isinstance(t,dict) and isinstance(t.get("price"),(int,float)) and t["price"]>1]
    return (good[0],good[-1]) if good else (None,None)
def _settle_pair(fn,hg,ag,line,ticks,side):
    first,last=_ends(ticks)
    if not first: return None
    return {
        "opening":{"created_at":first["created_at"],"price":first["price"],**_pack(fn(hg,ag,line,first["price"],side))},
        "latest":{"created_at":last["created_at"],"price":last["price"],**_pack(fn(hg,ag,line,last["price"],side))},
        "price_move":round(last["price"]-first["price"],8),
    }

def settle_row(row:dict)->dict:
    hg=int(row["ft_home_goals"]); ag=int(row["ft_away_goals"]); markets=[]
    for m in row.get("asian_handicap") or []:
        line=m.get("line")
        if not isinstance(line,(int,float)): continue
        for key,side,used_line in (("home","H",line),("away","A",-line)):
            s=_settle_pair(settle_asian_handicap,hg,ag,used_line,m.get(key),side)
            if s: markets.append({"market":"AH","selection":key.upper(),"line":line,**s})
    for m in row.get("over_under") or []:
        line=m.get("line")
        if not isinstance(line,(int,float)): continue
        for key,side in (("over","O"),("under","U")):
            s=_settle_pair(settle_asian_total,hg,ag,line,m.get(key),side)
            if s: markets.append({"market":"OU","selection":key.upper(),"line":line,**s})
    return {"schema_version":"1.0","fixture_id":row.get("fixture_id"),"tournament_id":row.get("tournament_id"),"league":row.get("league"),"kickoff":row.get("kickoff"),"home":row.get("home"),"away":row.get("away"),"ft_home_goals":hg,"ft_away_goals":ag,"settled_markets":markets,"settlement_status":"SETTLED" if markets else "NO_SETTLEABLE_MARKET","promotion_eligible":False}

def write_settled(root:Path=Path("."))->dict:
    rows=[]; p=root/INPUT
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            try:r=json.loads(line)
            except json.JSONDecodeError:continue
            if isinstance(r,dict) and "ft_home_goals" in r and "ft_away_goals" in r: rows.append(settle_row(r))
    out=root/OUTPUT; out.parent.mkdir(parents=True,exist_ok=True); out.write_text("".join(json.dumps(r,separators=(",",":"))+"\n" for r in rows),encoding="utf-8")
    settled=sum(r["settlement_status"]=="SETTLED" for r in rows); markets=sum(len(r["settled_markets"]) for r in rows)
    report={"schema_version":"1.0","classification":"EXPLORATORY_SETTLEMENT_QA_ONLY","joined_rows":len(rows),"settled_rows":settled,"settled_market_sides":markets,"promotion_allowed":False,"promotion_blockers":["ODDSPAPI_HISTORY_NOT_MULTI_SEASON","FROZEN_VALIDATION_NOT_RUN"]}
    rp=root/REPORT; rp.parent.mkdir(parents=True,exist_ok=True); rp.write_text(json.dumps(report,indent=2),encoding="utf-8"); return report
