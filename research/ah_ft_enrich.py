"""Fail-closed enrichment of movement features from exact source snapshots."""
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path

def dt(s):
    try:
        d=datetime.fromisoformat(str(s).replace("Z","+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (ValueError,TypeError):
        return None

def enrich(features, snapshots):
    # Strict source fixture ID, source contract, and observation timestamp.
    # Never infer side from signed handicap alone.
    lookup=defaultdict(list)
    for s in snapshots:
        key=(str(s.get("fixture_id")),str(s.get("observed_at")))
        lookup[key].append(s)
    out=[]
    for f in features:
        x=dict(f)
        x.pop("favorite_side",None)
        x.pop("last_favorite_side",None)
        x["side_evidence"]="UNVERIFIED"
        ids=f.get("source_fixture_ids") or [f.get("fixture_id")]
        last=f.get("last_observed_at")
        candidates=[s for fid in ids for s in lookup.get((str(fid),str(last)),[])]
        valid=[]
        for s in candidates:
            observed,kickoff=dt(s.get("observed_at")),dt(s.get("kickoff"))
            ah=s.get("ah") or {}
            side=s.get("favorite_side")
            if not (observed and kickoff and observed<kickoff and side in ("H","A")): continue
            if s.get("mainline_verified") is not True: continue
            if str(s.get("bookmaker")).lower()!="pinnacle": continue
            try:
                selected=float(ah["selected_side_line"])
                actual=float(ah["home_line"] if side=="H" else ah["away_line"])
                if abs(selected-actual)>1e-9 or abs(selected-float(f["last_ah_line"]))>1e-9: continue
            except (TypeError,ValueError,KeyError): continue
            valid.append(s)
        contracts={(s.get("provider"),s.get("bookmaker"),s.get("source_semantics"),s.get("favorite_side"),s.get("kickoff")) for s in valid}
        if len(valid)==1 and len(contracts)==1:
            x["last_favorite_side"]=valid[0]["favorite_side"]
            x["side_evidence"]="EXACT_SOURCE_SNAPSHOT"
        out.append(x)
    return out

def read(path):
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():yield json.loads(line)

def main():
    from research.ah_ft_join import analyze
    root=Path("data/normalized")
    features=enrich(read(root/"research_v2_movement_features.jsonl"),read(root/"europe_pinnacle_research_v2_snapshots.jsonl"))
    # Pinnwire settlements carry exact pinnwire fixture IDs and documented FT evidence.
    # Normalize only fields supported by the settlement rows; do not bridge providers.
    verified=[]
    for row in read(root/"pinnwire_research_v2_settlements.jsonl"):
        if not row.get("result_source") or not str(row.get("fixture_id","")).startswith("pinnwire:"):
            continue
        if row.get("ft_home_goals") is None or row.get("ft_away_goals") is None:
            continue
        verified.append({**row,"result_identity":"PINNWIRE_EXACT_FIXTURE_ID_SETTLEMENT_EVIDENCE"})
    # Read existing verified local FT sources without API calls or data writes.
    inputs={"pinnwire_research_v2_settlements.jsonl":len(verified)}
    for filename in ("dashboard_verified_results.jsonl","oddspapi_finished_results.jsonl","v2_forward_settlements.jsonl"):
        count=0
        for row in read(root/filename):
            if not row.get("result_source") or row.get("ft_home_goals") is None or row.get("ft_away_goals") is None: continue
            if filename=="dashboard_verified_results.jsonl":
                if row.get("status")!="FT" or not row.get("verified_at"): continue
                row={**row,"result_identity":"DASHBOARD_VERIFIED_EXACT_FIXTURE_ID"}
            elif not row.get("result_identity"): continue
            verified.append(row); count+=1
        inputs[filename]=count
    report=analyze(features,verified)
    report["ft_source_counts"]=inputs
    report["ft_input_rows"]=len(verified)
    report["ft_input"]="multiple_local_verified_ft_files"
    report["side_evidence_counts"]={k:sum(x["side_evidence"]==k for x in features) for k in ("EXACT_SOURCE_SNAPSHOT","UNVERIFIED")}
    dest=Path("reports/research_ah_ft_join_exploratory.json")
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"matched":report["matched"],"side_evidence_counts":report["side_evidence_counts"],"excluded":report["excluded"]}))

if __name__=="__main__":main()
