from __future__ import annotations

import json
from pathlib import Path
from .asian_settlement import settle_asian_handicap, settle_asian_total

INPUT=Path("data/normalized/oddspapi_prematch_joined.jsonl")
OUTPUT=Path("data/normalized/oddspapi_settled_history.jsonl")
REPORT=Path("reports/oddspapi_settled_history.json")


def _num(row,*names):
    for n in names:
        v=row.get(n)
        if isinstance(v,(int,float)): return float(v)
    return None

def settle_row(row:dict)->dict:
    out=dict(row); hg=int(row["ft_home_goals"]); ag=int(row["ft_away_goals"])
    ah_line=_num(row,"ah_line","opening_ah_line")
    hp=_num(row,"ah_home_price","opening_ah_home_price","ah_favorite_price")
    ap=_num(row,"ah_away_price","opening_ah_away_price","ah_underdog_price")
    ou_line=_num(row,"ou_line","opening_ou_line")
    op=_num(row,"over_price","ou_over_price","opening_over_price")
    up=_num(row,"under_price","ou_under_price","opening_under_price")
    settlements={}
    if ah_line is not None:
        if hp and hp>1: settlements["ah_home"]=_pack(settle_asian_handicap(hg,ag,ah_line,hp,"H"))
        if ap and ap>1: settlements["ah_away"]=_pack(settle_asian_handicap(hg,ag,-ah_line,ap,"A"))
    if ou_line is not None:
        if op and op>1: settlements["over"]=_pack(settle_asian_total(hg,ag,ou_line,op,"O"))
        if up and up>1: settlements["under"]=_pack(settle_asian_total(hg,ag,ou_line,up,"U"))
    out["settlements"]=settlements
    out["settlement_status"]="SETTLED" if settlements else "NO_SETTLEABLE_MARKET"
    out["promotion_eligible"]=False
    return out

def _pack(x): return {"settlement":x.settlement.value,"profit_units":round(x.profit_units,8),"return_units":round(x.return_units,8)}

def write_settled(root:Path=Path("."))->dict:
    rows=[]
    p=root/INPUT
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            try: r=json.loads(line)
            except json.JSONDecodeError: continue
            if isinstance(r,dict) and "ft_home_goals" in r and "ft_away_goals" in r: rows.append(settle_row(r))
    out=root/OUTPUT; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text("".join(json.dumps(r,separators=(",",":"))+"\n" for r in rows),encoding="utf-8")
    settled=sum(r["settlement_status"]=="SETTLED" for r in rows)
    report={"schema_version":"1.0","classification":"EXPLORATORY_SETTLEMENT_QA_ONLY","joined_rows":len(rows),"settled_rows":settled,"promotion_allowed":False,"promotion_blockers":["ODDSPAPI_HISTORY_NOT_MULTI_SEASON","FROZEN_VALIDATION_NOT_RUN"]}
    rp=root/REPORT; rp.parent.mkdir(parents=True,exist_ok=True); rp.write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report
