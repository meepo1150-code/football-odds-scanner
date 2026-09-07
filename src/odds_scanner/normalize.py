from __future__ import annotations
import csv, math
from pathlib import Path
from typing import Iterable

OPENING_TRIPLETS = [("AvgH","AvgD","AvgA"),("B365H","B365D","B365A"),("PSH","PSD","PSA")]
CLOSING_TRIPLETS = [("AvgCH","AvgCD","AvgCA"),("B365CH","B365CD","B365CA"),("PSCH","PSCD","PSCA")]

def _f(v):
    try:
        x=float(v)
        return x if math.isfinite(x) and x > 1.0 else None
    except (TypeError,ValueError):
        return None

def choose_triplet(row: dict, candidates):
    for cols in candidates:
        vals=tuple(_f(row.get(c)) for c in cols)
        if all(v is not None for v in vals):
            return vals, "/".join(cols)
    return (None,None,None), None

def fair_probs(h: float,d: float,a: float):
    inv=[1/h,1/d,1/a]
    s=sum(inv)
    return tuple(x/s for x in inv), s-1.0

def normalize_rows(rows: Iterable[dict], season: str) -> list[dict]:
    out=[]
    for r in rows:
        result=(r.get("FTR") or "").strip().upper()
        oh, osrc = choose_triplet(r, OPENING_TRIPLETS)
        ch, csrc = choose_triplet(r, CLOSING_TRIPLETS)
        if not all(oh):
            continue
        fp, margin=fair_probs(*oh)
        out.append({"season":season,"division":r.get("Div","E0"),"date":r.get("Date",""),"home":r.get("HomeTeam",""),"away":r.get("AwayTeam",""),"result":result,"open_h":oh[0],"open_d":oh[1],"open_a":oh[2],"close_h":ch[0],"close_d":ch[1],"close_a":ch[2],"open_source":osrc,"close_source":csrc,"fair_h":fp[0],"fair_d":fp[1],"fair_a":fp[2],"overround":margin})
    return out

def write_csv(rows: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
