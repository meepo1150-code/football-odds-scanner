from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus
from .pinnwire_result_join import _read, _utc, _name, SNAPSHOTS_PATH
from .research_population import in_scope

RESULTS_PATH=Path("data/normalized/oddspapi_finished_results.jsonl")
QUEUE_PATH=Path("reports/pinnwire_web_result_recovery_queue.json")

def build_queue(root=Path("."), limit=100):
    snaps=[x for x in _read(root/SNAPSHOTS_PATH) if x.get("provider")=="pinnwire" and in_scope(x)]
    settled={str(x.get("fixture_id") or "") for x in _read(root/RESULTS_PATH)}
    latest={}
    for s in snaps:
        fid=str(s.get("fixture_id") or "")
        if fid and fid not in settled and (fid not in latest or str(s.get("observed_at"))>str(latest[fid].get("observed_at"))):
            latest[fid]=s
    rows=[]
    for fid,s in sorted(latest.items(), key=lambda kv:(str(kv[1].get("kickoff") or ""),kv[0]))[:limit]:
        ko=_utc(s.get("kickoff"))
        day=ko.date().isoformat() if ko else str(s.get("football_day") or "")
        query=f'"{s.get("home","")}" "{s.get("away","")}" {day} football result'
        rows.append({
            "fixture_id":fid,"home":s.get("home"),"away":s.get("away"),"kickoff":s.get("kickoff"),
            "football_day":s.get("football_day"),"search_query":query,
            "search_url":"https://www.google.com/search?q="+quote_plus(query),
            "required_identity":["home_team","away_team","match_date"],
            "required_result":["ft_home_goals","ft_away_goals"],
            "acceptance_policy":"DETERMINISTIC_TEAMS_AND_DATE; SOURCE_URL_REQUIRED; CONFLICTS_REJECTED",
            "status":"WEB_EVIDENCE_REQUIRED"
        })
    payload={"schema_version":"1.0","classification":"PINNWIRE_WEB_RESULT_RECOVERY_QUEUE","generated_at":datetime.now(timezone.utc).isoformat(),"unresolved_total":len(latest),"queued":len(rows),"api_requests_used":0,"validation_relaxed":False,"rows":rows}
    p=root/QUEUE_PATH;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8");return payload

def validate_evidence(item):
    required=("fixture_id","home","away","kickoff","ft_home_goals","ft_away_goals","source_url","retrieved_at")
    if any(item.get(k) in (None,"") for k in required): return False,"MISSING_REQUIRED_FIELD"
    if type(item["ft_home_goals"]) is not int or type(item["ft_away_goals"]) is not int or min(item["ft_home_goals"],item["ft_away_goals"])<0:
        return False,"INVALID_FT_SCORE"
    if not str(item["source_url"]).startswith(("https://","http://")): return False,"INVALID_SOURCE_URL"
    return True,"VALID"

if __name__=="__main__": print(json.dumps(build_queue(),ensure_ascii=False))
