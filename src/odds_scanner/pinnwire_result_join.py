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
def _utc(v):
    try:
        d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    except (TypeError,ValueError):return None
def run(root=Path("."),kickoff_tolerance_seconds=60):
    snaps=[x for x in _read(root/SNAPSHOTS_PATH) if x.get("provider")=="pinnwire"]; fixtures=_read(root/API_FIXTURES_PATH)
    by={}
    for f in fixtures:
        k=(_name(f.get("home")),_name(f.get("away")))
        if all(k):by.setdefault(k,[]).append(f)
    latest={}
    for s in snaps:
        fid=str(s.get("fixture_id") or "")
        if fid and (fid not in latest or str(s.get("observed_at"))>str(latest[fid].get("observed_at"))):latest[fid]=s
    results=[];settlements=[];unmatched=[];ambiguous=[]
    for fid,s in latest.items():
        ko=_utc(s.get("kickoff")); exact=[]
        for f in by.get((_name(s.get("home")),_name(s.get("away"))),[]):
            fk=_utc(f.get("kickoff"))
            if ko and fk and abs((fk-ko).total_seconds())<=kickoff_tolerance_seconds:exact.append(f)
        if len(exact)!=1:
            (ambiguous if len(exact)>1 else unmatched).append(fid);continue
        f=exact[0]
        if not f.get("finished"):continue
        hg,ag=f.get("ft_home_goals"),f.get("ft_away_goals")
        if not isinstance(hg,int) or not isinstance(ag,int):continue
        results.append({"fixture_id":fid,"ft_home_goals":hg,"ft_away_goals":ag,"result_source":"API_FOOTBALL_EXACT_NORMALIZED_TEAMS_KICKOFF","api_football_fixture_id":f.get("provider_fixture_id")})
        ah=s.get("ah") or {}
        try:b=settle_asian_handicap(hg,ag,float(ah.get("selected_side_line")),float(ah.get("selected_side_price")),str(s.get("favorite_side")))
        except (TypeError,ValueError):continue
        settlements.append({"fixture_id":fid,"football_day":s.get("football_day"),"home":s.get("home"),"away":s.get("away"),"kickoff":s.get("kickoff"),"observed_at":s.get("observed_at"),"side":s.get("favorite_side"),"line":ah.get("selected_side_line"),"odds":ah.get("selected_side_price"),"ft_home_goals":hg,"ft_away_goals":ag,"settlement":b.settlement.value,"profit_units":b.profit_units,"result_source":"API_FOOTBALL_EXACT_NORMALIZED_TEAMS_KICKOFF"})
    added=merge_normalized_results(root/RESULTS_PATH,results)
    p=root/SETTLEMENTS_PATH;p.parent.mkdir(parents=True,exist_ok=True);p.write_text("".join(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n" for x in settlements),encoding="utf-8")
    report={"schema_version":"1.0","classification":"PINNWIRE_RESULT_JOIN","generated_at":datetime.now(timezone.utc).isoformat(),"pinnwire_fixtures":len(latest),"api_fixture_rows":len(fixtures),"finished_exact_matches":len(results),"results_added":added,"settlements":len(settlements),"unmatched":len(unmatched),"ambiguous_rejected":len(ambiguous),"join_policy":"EXACT_NORMALIZED_TEAMS_AND_KICKOFF","kickoff_tolerance_seconds":kickoff_tolerance_seconds,"fuzzy_matching_allowed":False}
    q=root/REPORT_PATH;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8");return report
if __name__=="__main__":print(json.dumps(run(),ensure_ascii=False))
