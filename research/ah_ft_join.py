"""Read-only AH quarter-line settlement and exact-ID FT join; no provider calls."""
import json
from pathlib import Path
from collections import Counter, defaultdict

def rows(path):
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def settle(line, goal_diff):
    q = round(line * 4)
    if abs(line * 4 - q) > 1e-8:
        raise ValueError("Not a quarter handicap")
    legs = [(q-1)/4, (q+1)/4] if q % 2 else [line]
    outcomes = [1 if goal_diff+x > 0 else -1 if goal_diff+x < 0 else 0 for x in legs]
    if len(outcomes) == 1:
        return {1:"FULL_WIN",0:"PUSH",-1:"FULL_LOSS"}[outcomes[0]]
    return {2:"FULL_WIN",1:"HALF_WIN",0:"PUSH",-1:"HALF_LOSS",-2:"FULL_LOSS"}[sum(outcomes)]

def analyze(features, results):
    ft = defaultdict(set)
    for r in results:
        if not (r.get("result_source") and r.get("result_identity")): continue
        if r.get("reason") in ("FOTMOB_NOT_NORMAL_TIME_FT", "AFTER_EXTRA_TIME"): continue
        try:
            h,a=int(r["ft_home_goals"]),int(r["ft_away_goals"])
            if h<0 or a<0: continue
        except (KeyError,ValueError,TypeError): continue
        ft[str(r.get("fixture_id"))].add((h,a))
    groups=defaultdict(Counter)
    excluded=Counter()
    for r in features:
        if r.get("observation_gap_minutes") is None or int(r.get("observations") or 0)<2:
            excluded["not_multi_snapshot"]+=1; continue
        if r.get("favorite_switch"):
            excluded["favorite_switch"]+=1; continue
        side=r.get("last_favorite_side") or r.get("favorite_side")
        if side not in ("H","A"):
            excluded["missing_verified_favorite_side"]+=1; continue
        # Only exact canonical/provider IDs retained by the movement builder.
        # A bridge is accepted only when every matching ID has one consistent FT.
        ids={str(r.get("fixture_id"))}
        ids.update(str(x) for x in (r.get("source_fixture_ids") or []) if x is not None)
        found=[ft[x] for x in ids if ft.get(x)]
        scores=set().union(*found) if found else set()
        if not scores:
            excluded["ft_not_found"]+=1; continue
        if len(scores)!=1:
            excluded["ft_score_conflict"]+=1; continue
        if not ft.get(str(r.get("fixture_id"))) and found:
            excluded["provider_id_bridge_used"]+=1
        try:
            first=float(r["first_ah_line"]); last=float(r["last_ah_line"])
            h,a=next(iter(scores)); diff=(h-a if side=="H" else a-h)
            label=settle(last,diff)
        except (KeyError,TypeError,ValueError):
            excluded["invalid_ah"]+=1; continue
        key=f"{first:+g}->{last:+g}|{r.get('movement','UNKNOWN')}"
        groups[key][label]+=1
        groups[key]["N"]+=1
        groups[key]["FT_"+("WIN" if diff>0 else "DRAW" if diff==0 else "LOSS")]+=1
    categories=("FULL_WIN","HALF_WIN","PUSH","HALF_LOSS","FULL_LOSS")
    return {"classification":"EXPLORATORY_ONLY","join_policy":"EXACT_FIXTURE_ID_ONLY",
            "matched":sum(c["N"] for c in groups.values()),"excluded":dict(excluded),
            "groups":{k:{"n":v["N"],"settlement_counts":{c:v[c] for c in categories},
                        "settlement_percent":{c:round(100*v[c]/v["N"],2) for c in categories},
                        "ft_counts":{c:v[c] for c in ("FT_WIN","FT_DRAW","FT_LOSS")}}
                      for k,v in sorted(groups.items())}}

def main():
    base=Path("data/normalized")
    result=analyze(rows(base/"research_v2_movement_features.jsonl"),rows(base/"oddspapi_finished_results.jsonl"))
    out=Path("reports/research_ah_ft_join_exploratory.json")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"matched":result["matched"],"excluded":result["excluded"]}))

if __name__=="__main__": main()
