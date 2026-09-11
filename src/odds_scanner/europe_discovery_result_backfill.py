from __future__ import annotations

import json, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .europe_discovery_evidence import ENTRIES_PATH, load_jsonl
from .flashscore_result_provider import fetch_exact_result
from .oddspapi_result_cache import RESULTS_PATH, merge_normalized_results

REPORT_PATH=Path('reports/europe_discovery_result_backfill.json')
MATURITY=timedelta(hours=3)


def utc(v):
    if not isinstance(v,str) or not v: return None
    try: dt=datetime.fromisoformat(v.replace('Z','+00:00'))
    except ValueError: return None
    if dt.tzinfo is None: return None
    return dt.astimezone(timezone.utc)


def select(entries:list[dict],existing:set[str],now:datetime)->list[dict]:
    out={}
    for e in entries:
        fid=str(e.get('fixture_id') or '')
        if not fid or fid in existing or fid in out: continue
        ko=utc(e.get('kickoff'))
        if ko is None or now < ko+MATURITY: continue
        ext=e.get('external_providers'); fs=ext.get('flashscoreId') if isinstance(ext,dict) else None
        if fs is None or not str(fs).strip(): continue
        out[fid]={'fixture_id':fid,'home':e.get('home'),'away':e.get('away'),'kickoff':e.get('kickoff'),'external_providers':{'flashscoreId':fs},'mapping_source':'ODDSPAPI_CURRENT_EXTERNALPROVIDERS_EXACT_IDS_FROM_DISCOVERY_ENTRY'}
    return sorted(out.values(),key=lambda r:(str(r.get('kickoff') or ''),str(r.get('fixture_id') or '')))


def run(root:Path=Path('.'),*,now:datetime|None=None,max_requests:int=10,sleep_seconds:float=1.0)->dict:
    current=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    entries=load_jsonl(root/ENTRIES_PATH); existing_rows=load_jsonl(root/RESULTS_PATH); existing={str(r.get('fixture_id')) for r in existing_rows if r.get('fixture_id') is not None}
    candidates=select(entries,existing,current); normalized=[]; failures=[]; attempted=0
    for ref in candidates[:max_requests]:
        attempted+=1; result,meta=fetch_exact_result(ref)
        if result:
            result['discovery_result_track']='EUROPE_DISCOVERY_ONLY'; normalized.append(result)
        else: failures.append({'fixture_id':ref.get('fixture_id'),'flashscore_id':(ref.get('external_providers') or {}).get('flashscoreId'),**meta})
        if sleep_seconds>0 and attempted<min(max_requests,len(candidates)): time.sleep(sleep_seconds)
    added=merge_normalized_results(root/RESULTS_PATH,normalized)
    report={'schema_version':'1.0','classification':'EUROPE_DISCOVERY_EXACT_RESULT_BACKFILL','status':'RESULTS_ADDED' if added else ('REQUESTS_ATTEMPTED_NO_NEW_RESULTS' if attempted else 'NO_MATURE_EXACT_ID_CANDIDATES'),'generated_at':current.isoformat(),'entry_rows':len(entries),'eligible_exact_id_fixtures':len(candidates),'requests_attempted':attempted,'results_parsed':len(normalized),'results_added':added,'odds_api_requests':0,'team_name_or_date_fuzzy_matching_allowed':False,'mapping_policy':'ODDSPAPI_CURRENT_EXTERNALPROVIDERS_FLASHSCOREID_EXACT_ONLY_FROM_DISCOVERY_ENTRY','production_promotion_allowed':False,'failures':failures[:20]}
    p=root/REPORT_PATH; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); return report

if __name__=='__main__': print(json.dumps(run(),ensure_ascii=False))
