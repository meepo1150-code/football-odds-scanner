from __future__ import annotations
import json,re,unicodedata,urllib.parse,urllib.request
from datetime import datetime,timezone,timedelta
from pathlib import Path
from .result_response_cache import fetch_day
from .oddspapi_result_cache import merge_normalized_results
SNAP=Path("data/normalized/europe_pinnacle_research_v2_snapshots.jsonl")
RESULTS=Path("data/normalized/oddspapi_finished_results.jsonl")
REPORT=Path("reports/fotmob_result_backfill.json")
BASE="https://www.fotmob.com/api/data/matches"
TEAM_ALIASES={
    "riversunited":"riversunitedfc",
    "unitedarabemirates":"uae",
    "congorepublic":"congo",
    "hapoelacre":"hapoelironiakko",
    "extremadura":"cdextremadura",
    "zamoracf":"zamora",
    "nantongzhiyun":"nantongzhiyunfc",
    "uralyekaterinburg":"ural",
    "halifaxtown":"fchalifaxtown",
    "gateshead":"gatesheadfc",
    "limavadyunited":"limavady",
    "readyfotball":"ready",
    "sfgrei":"grei",
    "kfumosloii":"kfum2",
    "sundby":"sundbybk",
    "nykobing":"nykobingfc",
    "steinbachhaiger":"tsvsteinbach",
    "fc08homburg":"homburg",
    "sotra":"sotrasportsklubb",
    "porsgrenland":"pors",
    "rotweisserfurt":"rwerfurt",
    "holstebro":"holstebroboldklub",
    "ishoj":"ishojif",
    "sandefjordii":"sandefjord2",
    "lillehammer":"lillehammerfk",
    "ceuta":"adceutafc",
    "realsociedadii":"realsociedadb",
}
def _read(p):
    out=[]
    if not p.exists(): return out
    for line in p.read_text(encoding="utf-8").splitlines():
        try:x=json.loads(line)
        except json.JSONDecodeError:continue
        if isinstance(x,dict):out.append(x)
    return out
def _norm(v):
    raw=str(v or "").casefold().translate(str.maketrans({"ø":"o","æ":"ae","å":"a","ð":"d","þ":"th","ł":"l","đ":"d"}))
    s=unicodedata.normalize("NFKD",raw).encode("ascii","ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+","",s)
def _team_key(v):
    n=_norm(v)
    return TEAM_ALIASES.get(n,n)

def _safe_club_key(v):
    # Conservative structural normalization only. Never strips women/youth markers.
    raw=str(v or "")
    n=_team_key(raw)
    if re.search(r"(?i)women|feminin|femenin|kvinner|\(w\)|\bu\s*-?\d{2}\b",raw):
        return n
    # Roman reserve marker II and numeric 2 are deterministic equivalents at the end.
    n=re.sub(r"ii$","2",n)
    # Common club designators; only removed at string edges to avoid changing core names.
    changed=True
    while changed:
        old=n
        n=re.sub(r"^(?:fc|fk|cf|sc|sk|ac|cd|ca|bk)","",n)
        n=re.sub(r"(?:fc|fk|cf|sc|sk|ac|cd|ca|bk|if)$","",n)
        changed=n!=old
    return n
def _category(v):
    s=str(v or "").casefold()
    m=re.search(r"\bu\s*-?(\d{2})\b",s)
    if m: return "u"+m.group(1)
    if re.search(r"women|woman|female|feminin|femenin|kvinner|dam|\(w\)",s): return "women"
    return None

def _category_base_key(v, category):
    n=_safe_club_key(v)
    if category=="women":
        n=re.sub(r"(?:women|woman|female|feminin|femenin|kvinner|dam|w)$","",n)
    elif category and category.startswith("u"):
        n=re.sub(category+r"$","",n)
    return n

def _utc(v):
    try:
        d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    except Exception:return None
def _fetch(day):
    q=urllib.parse.urlencode({"date":day.replace("-",""),"ccode3":"THA","timezone":"Asia/Bangkok"})
    req=urllib.request.Request(BASE+"?"+q,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=30) as r:
        data=json.loads(r.read().decode())
    return data if isinstance(data,dict) else {}
def _events(payload):
    out=[]
    for league in payload.get("leagues") or []:
        for m in league.get("matches") or []:
            h=m.get("home") or {};a=m.get("away") or {};status=m.get("status") or {}
            ko=_utc(status.get("utcTime"))
            if not ko:
                ts=m.get("timeTS")
                if isinstance(ts,(int,float)):ko=datetime.fromtimestamp(ts/1000 if ts>1e12 else ts,timezone.utc)
            reason=status.get('reason') or {}
            normal_ft=(status.get('finished') is True and not status.get('cancelled') and not status.get('awarded') and str(reason.get('short','')).upper()=='FT')
            out.append({"id":m.get("id"),"home":h.get("name") or h.get("longName"),"away":a.get("name") or a.get("longName"),"kickoff":ko,"finished":normal_ft,"hg":h.get("score"),"ag":a.get("score"),"league":league.get("name"),'provider_status':status})
    return out
def run(root=Path(".")):
    snaps=_read(root/SNAP)
    existing=_read(root/RESULTS); existing_ids={str(x.get("fixture_id")) for x in existing}
    missing={}
    for s in snaps:
        fid=str(s.get("fixture_id") or "")
        if fid and fid not in existing_ids and _utc(s.get("kickoff")) and _utc(s.get("kickoff")) + timedelta(hours=3) <= datetime.now(timezone.utc):missing[fid]=s
    day_set=set()
    for s in missing.values():
        ko=_utc(s.get("kickoff"))
        if ko:
            for delta in (-1,0,1): day_set.add((ko+timedelta(days=delta)).date().isoformat())
        elif s.get("football_day"): day_set.add(str(s.get("football_day")))
    days=sorted(day_set)
    events=[];failures=[];fetch_evidence=[];requests_used=0
    for day in days:
        try:
            payload, evidence=fetch_day(root,day,_fetch)
            fetch_evidence.append({'day':day,**evidence});requests_used+=evidence['requests']
            day_events=_events(payload)
            for event in day_events:event['retrieved_at']=evidence['fetched_at']
            events.extend(day_events)
        except Exception as e:
            requests_used+=1
            failures.append({"day":day,"error":f"{type(e).__name__}: {e}"})
    # Neighbor-day responses can repeat one event; count unique provider identities.
    # Conflicting copies remain separate so the unique-match gate fails closed.
    unique={}
    for event in events:
        signature=(event.get("id"),event.get("home"),event.get("away"),event.get("kickoff"),event.get("league"),event.get("finished"),event.get("hg"),event.get("ag"))
        unique[signature]=event
    events=list(unique.values())
    idx={}; safe_idx={}; kickoff_idx={}
    for e in events:
        if e["kickoff"]:
            idx.setdefault((_team_key(e["home"]),_team_key(e["away"]),e["kickoff"].isoformat()),[]).append(e)
            safe_idx.setdefault((_safe_club_key(e["home"]),_safe_club_key(e["away"]),e["kickoff"].isoformat()),[]).append(e)
            kickoff_idx.setdefault(e["kickoff"].isoformat(),[]).append(e)
    added=[];ambiguous=0; exact_unfinished=0; no_exact_identity=0; kickoff_candidate_only=0; candidate_samples=[]
    for fid,s in missing.items():
        ko=_utc(s.get("kickoff"))
        if not ko:continue
        ms=idx.get((_team_key(s.get("home")),_team_key(s.get("away")),ko.isoformat()),[])
        if not ms:
            ms=safe_idx.get((_safe_club_key(s.get("home")),_safe_club_key(s.get("away")),ko.isoformat()),[])
        if not ms:
            category=_category(s.get("league"))
            if category:
                contextual=[]
                for e in kickoff_idx.get(ko.isoformat(),[]):
                    event_category=_category(e.get("league")) or _category(e.get("home")) or _category(e.get("away"))
                    if event_category!=category: continue
                    if (_category_base_key(s.get("home"),category)==_category_base_key(e.get("home"),category)
                        and _category_base_key(s.get("away"),category)==_category_base_key(e.get("away"),category)):
                        contextual.append(e)
                ms=contextual
        if len(ms)>1:ambiguous+=1;continue
        if len(ms)!=1:
            no_exact_identity+=1
            candidates=kickoff_idx.get(ko.isoformat(),[])
            if candidates:
                kickoff_candidate_only+=1
                if len(candidate_samples)<100:
                    candidate_samples.append({"fixture_id":fid,"snapshot":{"home":s.get("home"),"away":s.get("away"),"kickoff":ko.isoformat()},"fotmob_candidates":[{"id":e.get("id"),"home":e.get("home"),"away":e.get("away"),"finished":e.get("finished"),"score":[e.get("hg"),e.get("ag")],"league":e.get("league")} for e in candidates]})
            continue
        e=ms[0]
        if not e.get('id') or not e["finished"] or type(e["hg"]) is not int or type(e["ag"]) is not int or min(e['hg'],e['ag'])<0:
            exact_unfinished+=1
            continue
        added.append({"fixture_id":fid,"ft_home_goals":e["hg"],"ft_away_goals":e["ag"],"result_source":"FOTMOB_DAILY_MATCH_EXACT_IDENTITY","result_identity":"EXACT_ALIAS_SAFE_TOKEN_OR_LEAGUE_CATEGORY_CONTEXT_HOME_AWAY_AND_EXACT_UTC_KICKOFF_UNIQUE","provider_event_id":e["id"],"provider_evidence":{"provider":"fotmob","event_id":e["id"],"home":e["home"],"away":e["away"],"kickoff":e["kickoff"].isoformat(),"league":e["league"]},"promotion_eligible":False,"research_only":True})
        added[-1]['provider_evidence'].update(retrieved_at=e.get('retrieved_at'),status=e.get('provider_status'))
    added_count=merge_normalized_results(root/RESULTS,added)
    report={"schema_version":"1.0","classification":"FOTMOB_EXACT_RESULT_BACKFILL","missing_before":len(missing),"missing_after":len(missing)-len(added),"verified_bridge_matches":len(added),"days_requested":days,"events_fetched":len(events),"exact_results_added":len(added),"ambiguous_exact_matches_rejected":ambiguous,"exact_identity_unfinished":exact_unfinished,"no_exact_identity":no_exact_identity,"kickoff_candidate_only":kickoff_candidate_only,"kickoff_candidate_samples":candidate_samples,"request_failures":failures,"matching_policy":"EXACT_ALIAS_OR_SAFE_CLUB_TOKEN_HOME_AWAY_AND_EXACT_UTC_KICKOFF_UNIQUE_ONLY","fuzzy_matching_used":False,"promotion_eligible":False}
    report.update(generated_at=datetime.now(timezone.utc).isoformat(),requests_used=requests_used,cache_hits=sum(x['source']=='CACHE' for x in fetch_evidence),stale_cache_fallbacks=sum(x['source'].startswith('STALE') for x in fetch_evidence),fetch_evidence=fetch_evidence,exact_results_added=added_count,verified_bridge_matches=added_count,missing_after=len(missing)-added_count)
    p=root/REPORT;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8");return report
if __name__=="__main__":print(json.dumps(run(),ensure_ascii=False))
