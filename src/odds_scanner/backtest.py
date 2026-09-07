from __future__ import annotations
from collections import defaultdict
import json, math
from pathlib import Path

SIDES=("H","D","A")
ODDS_KEY={"H":"open_h","D":"open_d","A":"open_a"}
FAIR_KEY={"H":"fair_h","D":"fair_d","A":"fair_a"}

def bucket(v: float, width: float = 0.10) -> tuple[float,float]:
    lo=math.floor((v+1e-9)/width)*width
    return round(lo,2), round(lo+width,2)

def _summarize(records: list[dict], side: str):
    n=len(records)
    wins=sum(r["result"]==side for r in records)
    avg_odds=sum(float(r[ODDS_KEY[side]]) for r in records)/n
    actual=wins/n
    expected=sum(float(r[FAIR_KEY[side]]) for r in records)/n
    profit=sum((float(r[ODDS_KEY[side]])-1) if r["result"]==side else -1 for r in records)
    roi=profit/n
    close=[r for r in records if r.get("close_h") and r.get("close_d") and r.get("close_a")]
    ck={"H":"close_h","D":"close_d","A":"close_a"}[side]
    clv=sum(float(r[ODDS_KEY[side]])/float(r[ck])-1 for r in close)/len(close) if close else None
    return {"n":n,"wins":wins,"win_rate":actual,"market_expected":expected,"calibration_gap_pp":(actual-expected)*100,"avg_odds":avg_odds,"flat_stake_roi":roi,"profit_units":profit,"avg_clv":clv}

def build_report(rows: list[dict], test_seasons: set[str] | None = None, min_n: int = 20):
    test_seasons=test_seasons or set()
    groups=defaultdict(list)
    for r in rows:
        if r.get("result") not in SIDES: continue
        split="test" if r.get("season") in test_seasons else "train"
        for side in SIDES:
            lo,hi=bucket(float(r[ODDS_KEY[side]]))
            groups[(split,side,lo,hi)].append(r)
    stats=[]
    for (split,side,lo,hi), recs in sorted(groups.items()):
        if len(recs)<min_n: continue
        s=_summarize(recs,side)
        s.update({"split":split,"side":side,"odds_low":lo,"odds_high":hi})
        stats.append(s)
    return {"schema_version":"1.0","methodology":{"probability":"normalized inverse 1X2 odds (proportional de-vig)","roi":"flat 1-unit stake at selected opening-odds field","warning":"Exploratory historical evidence only; positive in-sample ROI is not proof of future edge."},"rows":len(rows),"test_seasons":sorted(test_seasons),"buckets":stats}

def write_report(report: dict, path: Path):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
