from __future__ import annotations
import json,re,unicodedata,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path

SNAP=Path("data/normalized/europe_pinnacle_research_v2_snapshots.jsonl")
RESULTS=Path("data/normalized/oddspapi_finished_results.jsonl")
REPORT=Path("reports/fotmob_pinnwire_coverage_probe.json")
BASE="https://www.fotmob.com/api/data/matches"

def _read(p):
    out=[]
    if not p.exists(): return out
    for line in p.read_text(encoding="utf-8").splitlines():
        try: x=json.loads(line)
        except json.JSONDecodeError: continue
        if isinstance(x,dict): out.append(x)
    return out

def _norm(v):
    s=unicodedata.normalize("NFKD",str(v or "")).encode("ascii","ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+","",s)

def _utc(v):
    try:
        d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    except Exception:return None

def _fetch(day):
    q=urllib.parse.urlencode({"date":day,"ccode3":"THA","timezone":"Asia/Bangkok"})
    req=urllib.request.Request(BASE+"?"+q,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode())

def _events(payload):
    leagues=payload.get("leagues") if isinstance(payload,dict) else []
    out=[]
    for league in leagues or []:
        for m in league.get("matches") or []:
            h=m.get("home") or {}; a=m.get("away") or {}; status=m.get("status") or {}
            ts=m.get("timeTS")
            ko=datetime.fromtimestamp(ts/1000,timezone.utc) if isinstance(ts,(int,float)) else None
            out.append({"id":m.get("id"),"home":h.get("name") or h.get("longName"),"away":a.get("name") or a.get("longName"),"kickoff":ko,"finished":bool(status.get("finished")),"hg":h.get("score"),"ag":a.get("score"),"league":league.get("name")})
    return out

def probe(root=Path(".")):
    snaps=[x for x in _read(root/SNAP) if x.get("provider")=="pinnwire"]
    have={str(x.get("fixture_id")) for x in _read(root/RESULTS)}
    latest={}
    for s in snaps:
        fid=str(s.get("fixture_id") or "")
        if fid and fid not in have: latest[fid]=s
    days=sorted({str(x.get("football_day")) for x in latest.values() if x.get("football_day")})
    fetched=[]; failures=[]; schema_samples=[]
    for day in days:
        try:\n            payload=_fetch(day)\n            schema_samples.append({"day":day,"top_type":type(payload).__name__,"top_keys":list(payload.keys())[:30] if isinstance(payload,dict) else [],"sample":str(payload)[:3000]})\n            fetched.extend(_events(payload))
        except Exception as e:failures.append({"day":day,"error":f"{type(e).__name__}: {e}"})
    idx={}
    for e in fetched:
        if not e["kickoff"]:continue
        k=(_norm(e["home"]),_norm(e["away"]),e["kickoff"].isoformat())
        idx.setdefault(k,[]).append(e)
    exact=finished=amb=0;samples=[]
    for fid,s in latest.items():
        ko=_utc(s.get("kickoff"))
        if not ko:continue
        ms=idx.get((_norm(s.get("home")),_norm(s.get("away")),ko.isoformat()),[])
        if len(ms)>1:amb+=1
        elif len(ms)==1:
            exact+=1
            if ms[0]["finished"] and isinstance(ms[0]["hg"],int) and isinstance(ms[0]["ag"],int):finished+=1
            if len(samples)<20:samples.append({"fixture_id":fid,"snapshot":[s.get("home"),s.get("away"),s.get("kickoff")],"fotmob":{"id":ms[0]["id"],"home":ms[0]["home"],"away":ms[0]["away"],"finished":ms[0]["finished"],"score":[ms[0]["hg"],ms[0]["ag"]]}})
    report={"schema_version":"1.0","classification":"FOTMOB_PINNWIRE_EXACT_COVERAGE_PROBE","generated_at":datetime.now(timezone.utc).isoformat(),"missing_before":len(latest),"days_requested":days,"events_fetched":len(fetched),"exact_unique_matches":exact,"finished_exact_unique_matches":finished,"ambiguous_exact_matches_rejected":amb,"request_failures":failures,"matching_policy":"EXACT_NORMALIZED_HOME_AWAY_AND_EXACT_UTC_KICKOFF_UNIQUE_ONLY","fuzzy_matching_used":False,"promotion_eligible":False,"schema_samples":schema_samples,"samples":samples}
    q=root/REPORT;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8");return report

if __name__=="__main__":print(json.dumps(probe(),ensure_ascii=False))
