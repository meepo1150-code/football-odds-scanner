from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

INPUT=Path("data/normalized/oddspapi_settled_history.jsonl")
REPORT=Path("reports/oddspapi_exploratory_settlement.json")

def summarize(rows:list[dict])->dict:
    groups=defaultdict(list)
    for row in rows:
        for m in row.get("settled_markets") or []:
            opening=m.get("opening") or {}
            if isinstance(opening.get("profit_units"),(int,float)):
                key=(m.get("market"),m.get("selection"),m.get("line"))
                groups[key].append(float(opening["profit_units"]))
    cells=[]
    for (market,selection,line),profits in sorted(groups.items(),key=lambda x:str(x[0])):
        n=len(profits); roi=sum(profits)/n
        cells.append({"market":market,"selection":selection,"line":line,"n":n,"opening_flat_stake_roi":round(roi,6),"descriptive_only":True})
    return {"schema_version":"1.0","classification":"DESCRIPTIVE_ONLY_NOT_VALIDATED","cells":cells,"cell_count":len(cells),"promotion_allowed":False,"promotion_blockers":["NO_PREREGISTERED_MULTI_SEASON_SPLIT","NO_MULTIPLE_TESTING_CORRECTION","NO_HOLDOUT_VALIDATION"]}

def write_summary(root:Path=Path("."))->dict:
    rows=[]; p=root/INPUT
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            try:r=json.loads(line)
            except json.JSONDecodeError:continue
            if isinstance(r,dict):rows.append(r)
    report=summarize(rows); rp=root/REPORT; rp.parent.mkdir(parents=True,exist_ok=True); rp.write_text(json.dumps(report,indent=2),encoding="utf-8"); return report
