"""Keyless result evidence; exact teams/kickoff only, never an odds source."""
from .research_population import in_scope, exclusion_reason, POLICY
import json
import unicodedata
import re
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from .result_recovery_lifecycle import retired_ids
from .fotmob_result_backfill import _read
from .research_v2_integrity import trusted_snapshot
from .oddspapi_result_cache import merge_normalized_results
from .result_response_cache import fetch_day

BASE='https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard'
RESULTS=Path('data/normalized/oddspapi_finished_results.jsonl')


def utc(value):
    try:
        d=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except ValueError:return None


def identity(home,away,kickoff):
    def text(value):
        return ''.join(c for c in unicodedata.normalize('NFKD',str(value or '').strip().casefold()) if not unicodedata.combining(c))
    return (text(home),text(away),kickoff)


def events(payload):
    out=[]
    for e in payload.get('events',[]):
        comps=e.get('competitions') or []
        if len(comps)!=1 or not e.get('id'):continue
        c=comps[0]; status=c.get('status') or {}; kind=status.get('type') or {}
        if kind.get('name')!='STATUS_FULL_TIME' or kind.get('completed') is not True or status.get('period')!=2:continue
        sides=c.get('competitors') or []
        homes=[s for s in sides if s.get('homeAway')=='home'];aways=[s for s in sides if s.get('homeAway')=='away']
        if len(homes)!=1 or len(aways)!=1:continue
        h,a=homes[0],aways[0]; ko=utc(c.get('date'))
        if not ko or any(not re.fullmatch(r'[0-9]+',str(s.get('score'))) for s in (h,a)):continue
        hn=(h.get('team') or {}).get('displayName');an=(a.get('team') or {}).get('displayName')
        if not hn or not an:continue
        out.append({'id':str(e['id']),'uid':e.get('uid'),'home':hn,'away':an,'kickoff':ko.isoformat(),'hg':int(h['score']),'ag':int(a['score']),'status':status})
    return out


def fetch(day):
    req=urllib.request.Request(BASE+'?dates='+day.replace('-','')+'&limit=1000',headers={'User-Agent':'football-odds-scanner/0.1','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=20) as r:payload=json.load(r)
    if not isinstance(payload.get('events'),list):raise ValueError('Missing events list')
    return payload


def run(root=Path('.'),max_requests=12,now=None):
    now=now or datetime.now(timezone.utc)
    existing=_read(root/RESULTS); known={str(r.get('fixture_id')) for r in existing} | retired_ids(root)
    blocked={str(r.get('fixture_id')) for r in _read((root/RESULTS).with_suffix('.conflicts.jsonl'))}
    missing={};days=set()
    for s in _read(root/'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl'):
        fid=str(s.get('fixture_id'));ko=utc(s.get('kickoff'))
        if not (trusted_snapshot(s) and in_scope(s)) or fid in known or fid in blocked or not ko or now-ko<timedelta(hours=3):continue
        key=identity(s.get('home'),s.get('away'),ko.isoformat())
        missing.setdefault(fid,set()).add(key)
        for delta in (-1,0,1):
            day=ko.date()+timedelta(days=delta)
            if day<=now.date():days.add(day.isoformat())
    index={};evidence=[];errors=[];used=0;deferred=[]
    for day in sorted(days,reverse=True):
        if used>=max_requests:deferred.append(day);continue
        try:
            payload,proof=fetch_day(root,day,fetch,now,provider='espn');used+=proof['requests'];evidence.append({'day':day,**proof})
            for e in events(payload):
                e['retrieved_at']=proof['fetched_at'];key=identity(e['home'],e['away'],e['kickoff'])
                signature=(e['id'],e['uid'],e['hg'],e['ag'])
                index.setdefault(key,{})[signature]=e
        except Exception as exc:used+=1;errors.append({'day':day,'error':f'{type(exc).__name__}: {exc}'})
    staged=[];ambiguous=0;not_found=0
    for fid,keys in missing.items():
        if len(keys)!=1:ambiguous+=1;continue
        matches=list(index.get(next(iter(keys)),{}).values())
        if len(matches)>1:ambiguous+=1;continue
        if not matches:not_found+=1;continue
        e=matches[0]
        staged.append({'fixture_id':fid,'ft_home_goals':e['hg'],'ft_away_goals':e['ag'],'provider_event_id':e['id'],'result_source':'ESPN_EXACT_TEAMS_KICKOFF_FULL_TIME','result_identity':'VERIFIED_UNIQUE_ACCENT_NORMALIZED_HOME_AWAY_EXACT_UTC_KICKOFF','provider_evidence':{'provider':'espn','source_url':BASE,**e},'research_only':True,'promotion_eligible':False})
    stage=root/'data/normalized/espn_result_recovery_staged.jsonl';stage.parent.mkdir(parents=True,exist_ok=True)
    stage.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in staged))
    added=merge_normalized_results(root/RESULTS,staged)
    report={'generated_at':now.isoformat(),'capability':'RESULTS_ONLY','status':'PARTIAL_SOURCE_FAILURE' if errors else 'VERIFIED_RESULT_BACKFILL_COMPLETED','missing_before':len(missing),'results_added':added,'missing_after':len(missing)-added,'exact_matches':0,'verified_bridge_matches':added,'ambiguous':ambiguous,'not_found':not_found,'quarantined_results_excluded':len(blocked),'requests_used':used,'cache_hits':sum(e['source']=='CACHE' for e in evidence),'fetch_evidence':evidence,'errors':errors,'deferred_days':deferred,'fuzzy_matching_used':False,'production_promotion_allowed':False}
    p=root/'reports/espn_result_backfill.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':print(json.dumps(run()))
