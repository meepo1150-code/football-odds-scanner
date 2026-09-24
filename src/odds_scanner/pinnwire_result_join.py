from __future__ import annotations
import json,re,unicodedata
from datetime import datetime,timezone
from pathlib import Path
from .asian_settlement import settle_asian_handicap
from .oddspapi_result_cache import RESULTS_PATH,merge_normalized_results
SNAPSHOTS_PATH=Path("data/normalized/europe_pinnacle_research_v2_snapshots.jsonl")
API_FIXTURES_PATH=Path("data/normalized/api_football_fixtures.jsonl")
SETTLEMENTS_PATH=Path("data/normalized/pinnwire_research_v2_settlements.jsonl")
REPORT_PATH=Path("reports/pinnwire_result_join_status.json")
def _read(p):
    if not p.exists(): return []
    out=[]
    for line in p.read_text(encoding="utf-8").splitlines():
        try:x=json.loads(line)
        except json.JSONDecodeError:continue
        if isinstance(x,dict):out.append(x)
    return out
def _name(v):
    s=unicodedata.normalize("NFKD",str(v or "")).encode("ascii","ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+","",s)
TEAM_EQUIV={
    "drcongo":"congodr","congorepublic":"congo",
    "alsohar":"sohar","alseeb":"seeb",
    "uskkok":"uskokklis","kunkhalifat":"kunkhalifatfc",
}
def _aliases(v):
    n=_name(v); out={n}
    if n in TEAM_EQUIV: out.add(TEAM_EQUIV[n])
    out.update(k for k,val in TEAM_EQUIV.items() if val==n)
    for token in ("footballclub","club","fc","sc"):
        if n.endswith(token) and len(n)>len(token)+2: out.add(n[:-len(token)])
        if n.startswith(token) and len(n)>len(token)+2: out.add(n[len(token):])
    return {x for x in out if x}
def _same_team(a,b):
    return bool(_aliases(a)&_aliases(b))
def _utc(v):
    try:
        d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    except (TypeError,ValueError):return None
def run(root=Path("."),kickoff_tolerance_seconds=60):
    snaps=[x for x in _read(root/SNAPSHOTS_PATH) if x.get("provider")=="pinnwire"]; fixtures=_read(root/API_FIXTURES_PATH)
    # Match kickoff first, then require deterministic team aliases. This safely handles\n    # provider decoration such as "Pharco FC" vs "Pharco" without fuzzy guessing.
    latest={}
    for s in snaps:
        fid=str(s.get("fixture_id") or "")
        if fid and (fid not in latest or str(s.get("observed_at"))>str(latest[fid].get("observed_at"))):latest[fid]=s
    results=[];settlements=[];unmatched=[];ambiguous=[];matched_total=0;matched_pending=0;unmatched_with_kickoff=0;unmatched_no_kickoff=0;unmatched_samples=[]
    for fid,s in latest.items():
        ko=_utc(s.get("kickoff")); exact=[]; kickoff_candidates=[]
        for f in fixtures:
            fk=_utc(f.get("kickoff"))
            if not (ko and fk and abs((fk-ko).total_seconds())<=kickoff_tolerance_seconds): continue
            kickoff_candidates.append(f)
            if _same_team(s.get("home"),f.get("home")) and _same_team(s.get("away"),f.get("away")): exact.append(f)
        if len(exact)!=1:
            if len(exact)>1: ambiguous.append(fid)
            else:
                unmatched.append(fid)
                if kickoff_candidates: unmatched_with_kickoff+=1
                else: unmatched_no_kickoff+=1
                if len(unmatched_samples)<12: unmatched_samples.append({'fixture_id':fid,'home':s.get('home'),'away':s.get('away'),'kickoff':s.get('kickoff'),'kickoff_candidate_count':len(kickoff_candidates),'kickoff_candidates':[{'home':x.get('home'),'away':x.get('away')} for x in kickoff_candidates[:5]]})
            continue
        f=exact[0]; matched_total+=1
        if not f.get("finished"):
            matched_pending+=1;continue
        hg,ag=f.get("ft_home_goals"),f.get("ft_away_goals")
        if not isinstance(hg,int) or not isinstance(ag,int):continue
        results.append({"fixture_id":fid,"ft_home_goals":hg,"ft_away_goals":ag,"result_source":"API_FOOTBALL_EXACT_NORMALIZED_TEAMS_KICKOFF","api_football_fixture_id":f.get("provider_fixture_id")})
        ah=s.get("ah") or {}
        try:b=settle_asian_handicap(hg,ag,float(ah.get("selected_side_line")),float(ah.get("selected_side_price")),str(s.get("favorite_side")))
        except (TypeError,ValueError):continue
        settlements.append({"fixture_id":fid,"football_day":s.get("football_day"),"home":s.get("home"),"away":s.get("away"),"kickoff":s.get("kickoff"),"observed_at":s.get("observed_at"),"side":s.get("favorite_side"),"line":ah.get("selected_side_line"),"odds":ah.get("selected_side_price"),"ft_home_goals":hg,"ft_away_goals":ag,"settlement":b.settlement.value,"profit_units":b.profit_units,"result_source":"API_FOOTBALL_EXACT_NORMALIZED_TEAMS_KICKOFF"})
    added=merge_normalized_results(root/RESULTS_PATH,results)
    p=root/SETTLEMENTS_PATH;p.parent.mkdir(parents=True,exist_ok=True);p.write_text("".join(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n" for x in settlements),encoding="utf-8")
    report={"schema_version":"1.1","classification":"PINNWIRE_RESULT_JOIN","generated_at":datetime.now(timezone.utc).isoformat(),"pinnwire_fixtures":len(latest),"api_fixture_rows":len(fixtures),"matched_total":matched_total,"matched_pending":matched_pending,"finished_exact_matches":len(results),"results_added":added,"settlements":len(settlements),"unmatched":len(unmatched),"unmatched_with_kickoff_candidate":unmatched_with_kickoff,"unmatched_no_kickoff_candidate":unmatched_no_kickoff,"unmatched_samples":unmatched_samples,"ambiguous_rejected":len(ambiguous),"join_policy":"CURATED_DETERMINISTIC_TEAM_ALIASES_AND_EXACT_KICKOFF","kickoff_tolerance_seconds":kickoff_tolerance_seconds,"fuzzy_matching_allowed":False}
    q=root/REPORT_PATH;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8");return report
if __name__=="__main__":print(json.dumps(run(),ensure_ascii=False))
