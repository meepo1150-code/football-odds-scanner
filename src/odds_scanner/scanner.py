from __future__ import annotations
import json
from pathlib import Path
from .football_data import decode_csv, download_fixtures
from .normalize import choose_triplet, OPENING_TRIPLETS, fair_probs

def scan(root: Path, min_history: int=100, min_gap_pp: float=1.0):
    back=json.loads((root/"reports/backtest.json").read_text(encoding="utf-8"))
    fx_path=download_fixtures(root/"data/raw/fixtures.csv")
    fixtures=decode_csv(fx_path.read_bytes())
    candidates=[]
    tests=[b for b in back["buckets"] if b["split"]=="test" and b["n"]>=min_history and b["calibration_gap_pp"]>=min_gap_pp]
    for r in fixtures:
        odds,src=choose_triplet(r,OPENING_TRIPLETS)
        if not all(odds): continue
        probs,margin=fair_probs(*odds)
        for side,odd in zip(("H","D","A"),odds):
            hit=next((b for b in tests if b["side"]==side and b["odds_low"] <= odd < b["odds_high"]),None)
            if hit:
                candidates.append({"date":r.get("Date",""),"time":r.get("Time",""),"league":r.get("Div",""),"home":r.get("HomeTeam",""),"away":r.get("AwayTeam",""),"side":side,"odds":odd,"source":src,"overround":margin,"history":hit})
    candidates.sort(key=lambda x:(x["history"]["calibration_gap_pp"],x["history"]["n"]),reverse=True)
    out={"schema_version":"1.0","qualifying":len(candidates),"candidates":candidates,"rule":{"min_test_history":min_history,"min_calibration_gap_pp":min_gap_pp}}
    p=root/"reports/today.json"; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    return out
