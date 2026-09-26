from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .daily_fixture_result_sync import FIXTURES_PATH
from .flashscore_result_provider import fetch_exact_result
from .oddspapi_result_cache import RESULTS_PATH, merge_normalized_results

REPORT_PATH = Path('reports/research_v2_daily_result_backfill.json')
AUDIT_PATH = Path('data/normalized/europe_pinnacle_research_v2_audit.jsonl')
SNAPSHOTS_PATH = Path('data/normalized/europe_pinnacle_research_v2_snapshots.jsonl')
RESULT_MATURITY_DELAY = timedelta(hours=3)


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists(): return []
    rows=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        try: row=json.loads(line)
        except json.JSONDecodeError: continue
        if isinstance(row,dict): rows.append(row)
    return rows


def _utc(value) -> datetime | None:
    if not isinstance(value,str) or not value.strip(): return None
    try: dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError: return None
    if dt.tzinfo is None: return None
    return dt.astimezone(timezone.utc)


def _result_match_key(home, away, kickoff) -> str | None:
    ko=_utc(kickoff)
    if ko is None: return None
    h=str(home or '').strip().casefold(); a=str(away or '').strip().casefold()
    if not h or not a: return None
    return hashlib.sha1(f"{h}|{a}|{ko.isoformat()}".encode()).hexdigest()


def _pinnwire_bridge_candidates(fixtures:list[dict],snapshots:list[dict],existing_ids:set[str],*,now:datetime)->tuple[list[dict],int]:
    by_key={}
    for row in fixtures:
        key=_result_match_key(row.get('home'),row.get('away'),row.get('kickoff')); flashscore_id=str(row.get('flashscore_id') or '').strip()
        if not key or not flashscore_id: continue
        by_key.setdefault(key,[]).append(row)
    out=[]; ambiguous=0; seen=set()
    for snap in snapshots:
        fixture_id=str(snap.get('fixture_id') or '').strip(); key=str(snap.get('result_match_key') or '').strip(); kickoff=_utc(snap.get('kickoff'))
        if not fixture_id.startswith('pinnwire:') or not key or fixture_id in existing_ids or fixture_id in seen: continue
        if kickoff is None or now < kickoff + RESULT_MATURITY_DELAY: continue
        matches=by_key.get(key,[])
        if len(matches)!=1:
            ambiguous += int(len(matches)>1)
            continue
        row=matches[0]; flashscore_id=str(row.get('flashscore_id') or '').strip()
        out.append({'fixture_id':fixture_id,'home':snap.get('home'),'away':snap.get('away'),'kickoff':snap.get('kickoff'),'external_providers':{'flashscoreId':flashscore_id},'mapping_source':'PINNWIRE_RESULT_MATCH_KEY_TO_UNIQUE_ODDSPAPI_DAILY_FIXTURE_THEN_EXACT_FLASHSCORE_ID','research_v2_priority':True,'bridge_source_fixture_id':row.get('fixture_id')})
        seen.add(fixture_id)
    return sorted(out,key=lambda r:(str(r.get('kickoff') or ''),str(r.get('fixture_id') or ''))),ambiguous


def select_candidates(fixtures:list[dict],existing_ids:set[str],*,now:datetime,priority_ids:set[str]|None=None)->list[dict]:
    priority_ids=priority_ids or set(); by_fixture={}
    for row in fixtures:
        fixture_id=str(row.get('fixture_id') or '').strip(); flashscore_id=str(row.get('flashscore_id') or '').strip(); kickoff=_utc(row.get('kickoff'))
        if not fixture_id or not flashscore_id or fixture_id in existing_ids or fixture_id in by_fixture: continue
        if kickoff is None or now < kickoff + RESULT_MATURITY_DELAY: continue
        by_fixture[fixture_id]={'fixture_id':fixture_id,'home':row.get('home'),'away':row.get('away'),'kickoff':row.get('kickoff'),'external_providers':{'flashscoreId':flashscore_id},'mapping_source':'ODDSPAPI_DAILY_FIXTURE_FLASHSCORE_ID_EXACT_ONLY','research_v2_priority':fixture_id in priority_ids}
    return sorted(by_fixture.values(),key=lambda r:(0 if r['fixture_id'] in priority_ids else 1,str(r.get('kickoff') or ''),str(r.get('fixture_id') or '')))


def run_backfill(root:Path=Path('.'),*,now:datetime|None=None,max_requests:int=80,sleep_seconds:float=0.25)->dict:
    current=(now or datetime.now(timezone.utc)).astimezone(timezone.utc); fixtures=_load_jsonl(root/FIXTURES_PATH); existing=_load_jsonl(root/RESULTS_PATH); audit=_load_jsonl(root/AUDIT_PATH); snapshots=_load_jsonl(root/SNAPSHOTS_PATH)
    existing_ids={str(r.get('fixture_id')) for r in existing if r.get('fixture_id') is not None}; priority_ids={str(r.get('fixture_id')) for r in audit if r.get('fixture_id') is not None} | {str(r.get('fixture_id')) for r in snapshots if r.get('fixture_id') is not None}
    direct_candidates=select_candidates(fixtures,existing_ids,now=current,priority_ids=priority_ids); bridged_candidates,bridge_ambiguous=_pinnwire_bridge_candidates(fixtures,snapshots,existing_ids,now=current); bridged_ids={r['fixture_id'] for r in bridged_candidates}; candidates=bridged_candidates+[r for r in direct_candidates if r['fixture_id'] not in bridged_ids]; attempted=0; normalized=[]; failures=[]; priority_attempted=0; bridge_attempted=0; bridge_parsed=0
    for ref in candidates[:max_requests]:
        attempted+=1; priority_attempted+=int(bool(ref.get('research_v2_priority'))); is_bridge=str(ref.get('mapping_source') or '').startswith('PINNWIRE_'); bridge_attempted+=int(is_bridge); result,meta=fetch_exact_result(ref)
        if result:
            result['daily_fixture_result_track']='RESEARCH_V2_DAILY_EXACT_ID'; result['mapping_source']=ref.get('mapping_source'); result['bridge_source_fixture_id']=ref.get('bridge_source_fixture_id'); bridge_parsed+=int(is_bridge); normalized.append(result)
        else: failures.append({'fixture_id':ref.get('fixture_id'),'flashscore_id':(ref.get('external_providers') or {}).get('flashscoreId'),**meta})
        if sleep_seconds>0 and attempted<min(max_requests,len(candidates)): time.sleep(sleep_seconds)
    added=merge_normalized_results(root/RESULTS_PATH,normalized)
    payload={'schema_version':'1.2','classification':'RESEARCH_V2_DAILY_FIXTURE_EXACT_RESULT_BACKFILL','status':'RESULTS_ADDED' if added else ('REQUESTS_ATTEMPTED_NO_NEW_RESULTS' if attempted else 'NO_MATURE_EXACT_ID_CANDIDATES'),'generated_at':current.isoformat(),'daily_fixture_rows':len(fixtures),'existing_result_rows':len(existing),'eligible_exact_id_fixtures':len(candidates),'research_v2_priority_ids':len(priority_ids),'research_v2_priority_candidates':sum(1 for r in candidates if r.get('research_v2_priority')),'pinnwire_exact_key_bridge_candidates':len(bridged_candidates),'pinnwire_exact_key_bridge_ambiguous_rejected':bridge_ambiguous,'requests_attempted':attempted,'research_v2_priority_attempted':priority_attempted,'pinnwire_exact_key_bridge_attempted':bridge_attempted,'pinnwire_exact_key_bridge_results_parsed':bridge_parsed,'results_parsed':len(normalized),'results_added':added,'maturity_delay_hours':3,'mapping_policy':'PINNWIRE_EXACT_NORMALIZED_TEAMS_AND_KICKOFF_UNIQUE_BRIDGE_TO_ODDSPAPI_FLASHSCORE_ID_OR_DIRECT_EXACT_ID','team_name_or_date_fuzzy_matching_allowed':False,'odds_api_requests':0,'failures':failures[:80],'research_only':True}
    path=root/REPORT_PATH; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8'); return payload

if __name__=='__main__': print(json.dumps(run_backfill(),ensure_ascii=False))
