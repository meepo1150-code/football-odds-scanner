from __future__ import annotations

from .research_population import in_scope, exclusion_reason, POLICY
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from .result_recovery_lifecycle import retired_ids
from .oddspapi_result_cache import merge_normalized_results

SNAPSHOTS_PATH = Path("data/normalized/europe_pinnacle_research_v2_snapshots.jsonl")
RESULTS_PATH = Path("data/normalized/oddspapi_finished_results.jsonl")
REPORT_PATH = Path("reports/openligadb_result_backfill.json")
BASE = "https://api.openligadb.de"
LEAGUES = ("bl1","bl2","bl3","ucl","uel2026","la1","pl")


def _utc(v):
    try:
        d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    except (TypeError,ValueError):
        return None


def _norm(v): return str(v or "").strip().casefold()


def _load_jsonl(path):
    if not path.exists(): return []
    out=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        try: row=json.loads(line)
        except json.JSONDecodeError: continue
        if isinstance(row,dict): out.append(row)
    return out


def _fetch(shortcut, season):
    req=urllib.request.Request(f"{BASE}/getmatchdata/{shortcut}/{season}",headers={"Accept":"application/json","User-Agent":"football-odds-scanner/0.1"})
    with urllib.request.urlopen(req,timeout=30) as r:
        data=json.loads(r.read().decode())
    return data if isinstance(data,list) else []


def _score(match):
    if match.get("matchIsFinished") is not True: return None
    # Actual provider payload distinguishes After90Minutes from later scores.
    # resultOrderID is presentation order, not normal-time semantics.
    scores=set()
    for row in match.get("matchResults") or []:
        if row.get("resultTypeKind") != "After90Minutes": continue
        h,a=row.get('pointsTeam1'),row.get('pointsTeam2')
        if type(h) is int and type(a) is int and min(h,a)>=0:scores.add((h,a))
    return next(iter(scores)) if len(scores)==1 else None


def run(root=Path("."), season=None):
    season=str(season or datetime.now(timezone.utc).year)
    snaps=_load_jsonl(root/SNAPSHOTS_PATH); existing=_load_jsonl(root/RESULTS_PATH)
    existing_ids={str(x.get("fixture_id")) for x in existing} | retired_ids(root)
    index={}
    api_rows=0; requests=0
    for league in LEAGUES:
        try: rows=_fetch(league,season); requests+=1
        except Exception: continue
        api_rows+=len(rows)
        for m in rows:
            ko=_utc(m.get("matchDateTimeUTC") or m.get("matchDateTime"))
            t1=m.get("team1") or {}; t2=m.get("team2") or {}; score=_score(m)
            if not ko or not score: continue
            key=(_norm(t1.get("teamName")),_norm(t2.get("teamName")),ko.isoformat())
            index.setdefault(key,[]).append((m,score,league))
    added=[]; ambiguous=0
    for s in snaps:
        if not in_scope(s): continue
        fid=str(s.get("fixture_id") or "")
        if not fid.startswith("pinnwire:") or fid in existing_ids: continue
        ko=_utc(s.get("kickoff"))
        if not ko: continue
        matches=index.get((_norm(s.get("home")),_norm(s.get("away")),ko.isoformat()),[])
        if len(matches)>1: ambiguous+=1; continue
        if len(matches)!=1: continue
        m,score,league=matches[0]
        added.append({"fixture_id":fid,"ft_home_goals":score[0],"ft_away_goals":score[1],"result_source":"OPENLIGADB_EXACT_TEAMS_AND_KICKOFF","result_identity":"OPENLIGADB_MATCH_ID_PLUS_EXACT_NORMALIZED_TEAMS_AND_KICKOFF","provider_event_id":m.get("matchID"),"provider_evidence":{"league_shortcut":league,"match_id":m.get("matchID"),"kickoff":ko.isoformat()},"promotion_eligible":False,"research_only":True})
    added_count=merge_normalized_results(root/RESULTS_PATH,added)
    report={"schema_version":"1.0","classification":"OPENLIGADB_SECONDARY_RESULT_BACKFILL","season":season,"league_shortcuts":list(LEAGUES),"requests_used":requests,"api_match_rows":api_rows,"exact_results_added":added_count,"ambiguous_exact_matches_rejected":ambiguous,"matching_policy":"EXACT_NORMALIZED_HOME_AWAY_AND_EXACT_UTC_KICKOFF_ONLY","fuzzy_matching_used":False,"promotion_eligible":False}
    p=root/REPORT_PATH;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8");return report


if __name__=="__main__": print(json.dumps(run(),ensure_ascii=False))
