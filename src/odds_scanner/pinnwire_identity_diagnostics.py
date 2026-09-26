from __future__ import annotations
import json
from collections import Counter, defaultdict
from pathlib import Path
from .daily_fixture_result_backfill import _load_jsonl, _utc
from .daily_fixture_result_sync import FIXTURES_PATH
SNAP=Path("data/normalized/europe_pinnacle_research_v2_snapshots.jsonl")
RES=Path("data/normalized/oddspapi_finished_results.jsonl")
OUT=Path("reports/pinnwire_identity_diagnostics.json")

def norm(v): return str(v or "").strip().casefold()

def run(root=Path(".")):
    fixtures=_load_jsonl(root/FIXTURES_PATH); snaps=_load_jsonl(root/SNAP); results=_load_jsonl(root/RES)
    settled={str(x.get("fixture_id")) for x in results}
    by_ko=defaultdict(list)
    for f in fixtures:
        ko=_utc(f.get("kickoff"))
        if ko and f.get("flashscore_id"): by_ko[ko.isoformat()].append(f)
    unique={}
    for s in snaps:
        fid=str(s.get("fixture_id") or "")
        if fid.startswith("pinnwire:"): unique.setdefault(fid,s)
    missing=[s for fid,s in unique.items() if fid not in settled]
    counts=Counter(); samples=[]; offsets=Counter(); nearest_samples=[]\n    fixture_times=sorted(((_utc(f.get("kickoff")),f) for f in fixtures if _utc(f.get("kickoff")) and f.get("flashscore_id")), key=lambda x:x[0])
    for s in missing:
        ko=_utc(s.get("kickoff")); cands=by_ko.get(ko.isoformat(),[]) if ko else []
        if not cands:
            counts["no_exact_kickoff_candidate"]+=1
            if ko and fixture_times:
                nearest=min(fixture_times,key=lambda x:abs((x[0]-ko).total_seconds()))
                delta=int((nearest[0]-ko).total_seconds()//60)
                offsets[str(delta)]+=1
                if len(nearest_samples)<40:
                    nearest_samples.append({"pinnwire_fixture_id":s.get("fixture_id"),"kickoff":s.get("kickoff"),"home":s.get("home"),"away":s.get("away"),"nearest_delta_minutes":delta,"nearest_fixture_id":nearest[1].get("fixture_id"),"nearest_home":nearest[1].get("home"),"nearest_away":nearest[1].get("away"),"nearest_kickoff":nearest[1].get("kickoff")})
            continue
        counts["has_exact_kickoff_candidate"]+=1
        exact=[f for f in cands if norm(f.get("home"))==norm(s.get("home")) and norm(f.get("away"))==norm(s.get("away"))]
        home=[f for f in cands if norm(f.get("home"))==norm(s.get("home"))]
        away=[f for f in cands if norm(f.get("away"))==norm(s.get("away"))]
        if len(exact)==1: counts["exact_teams_unique"]+=1
        elif len(exact)>1: counts["exact_teams_ambiguous"]+=1
        elif len(home)==1 and len(away)==0: counts["home_exact_only"]+=1
        elif len(away)==1 and len(home)==0: counts["away_exact_only"]+=1
        else: counts["same_kickoff_names_differ"]+=1
        if len(samples)<40 and not exact:
            samples.append({"pinnwire_fixture_id":s.get("fixture_id"),"kickoff":s.get("kickoff"),"pinnwire_home":s.get("home"),"pinnwire_away":s.get("away"),"candidate_count":len(cands),"candidates":[{"fixture_id":f.get("fixture_id"),"home":f.get("home"),"away":f.get("away"),"flashscore_id":f.get("flashscore_id")} for f in cands[:8]]})
    payload={"schema_version":"1.0","classification":"PINNWIRE_IDENTITY_DIAGNOSTICS_ONLY","snapshot_unique_pinnwire":len(unique),"missing_pinnwire_results":len(missing),"daily_fixture_rows":len(fixtures),"exact_kickoff_counts":dict(counts),"mismatch_samples":samples,"nearest_kickoff_offset_minutes":dict(offsets.most_common(30)),"nearest_kickoff_samples":nearest_samples,"settlement_effect":"NONE","fuzzy_matching_used":False}
    (root/OUT).parent.mkdir(parents=True,exist_ok=True);(root/OUT).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8");return payload
if __name__=="__main__": print(json.dumps(run(),ensure_ascii=False))
