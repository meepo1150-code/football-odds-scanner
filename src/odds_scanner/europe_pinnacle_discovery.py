from __future__ import annotations

import json, os, time
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from .europe_bookmaker_coverage_probe import BOOKMAKER, quota_allows_probe, summarize_rows

# Research V2 is the primary forward data collector. Keep a small emergency reserve,
# while background/history jobs yield to the canonical weekend observations.
CORE_QUOTA_RESERVE = 4
from .oddspapi_discovery import _rows
from .oddspapi_provider import ENV_KEY, _get
from .oddspapi_quota_health import summarize_account
from .v2_mainline_observer import CATALOG_PATH, _load_json, extract_mainline_snapshot, mainline_shape

TARGET_PATH=Path('reports/europe_discovery_tournaments.json'); SNAPSHOT_PATH=Path('data/normalized/europe_pinnacle_research_v2_snapshots.jsonl'); AUDIT_PATH=Path('data/normalized/europe_pinnacle_research_v2_audit.jsonl'); REPORT_PATH=Path('reports/europe_pinnacle_research_v2_status.json'); SLOT_LEDGER_PATH=Path('data/normalized/research_v2_slot_ledger.jsonl')
BANGKOK=ZoneInfo('Asia/Bangkok'); FOOTBALL_DAY_START_HOUR=12; FOOTBALL_DAY_END_HOUR=6; BATCH_SIZE=5; INTER_BATCH_DELAY_SECONDS=2.0; RATE_LIMIT_RETRY_DELAY_SECONDS=5.0; MAX_ATTEMPTS_PER_BATCH=2; RECOVERY_WINDOW_MINUTES=150; WEEKEND_TARGET_HOURS=(12,15,18,19,20,21,22)

def _merge_jsonl(path,new_rows,key_fields):
    rows={}
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            try:r=json.loads(line)
            except json.JSONDecodeError:continue
            if isinstance(r,dict):rows[tuple(str(r.get(k)) for k in key_fields)]=r
    for r in new_rows:rows[tuple(str(r.get(k)) for k in key_fields)]=r
    ordered=sorted(rows.values(),key=lambda r:tuple(str(r.get(k)) for k in key_fields)); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in ordered),encoding='utf-8'); return len(ordered)

def _football_day_bounds(now):
    local=now.astimezone(BANGKOK); label=local.date()-timedelta(days=1) if local.time()<dtime(FOOTBALL_DAY_END_HOUR) else local.date(); start=datetime.combine(label,dtime(12),BANGKOK); end=datetime.combine(label+timedelta(days=1),dtime(6),BANGKOK); return start.astimezone(timezone.utc),end.astimezone(timezone.utc),label.isoformat()

def _schedule_timing(now):
    local=now.astimezone(BANGKOK); candidates=[]
    for delta in (-1,0):
        day=local.date()+timedelta(days=delta)
        for h in (WEEKEND_TARGET_HOURS if day.weekday()>=5 else (21,)): candidates.append(datetime.combine(day,dtime(h),BANGKOK))
        if day.weekday() in (1,2,3,4,5): candidates.append(datetime.combine(day,dtime(0),BANGKOK))
    eligible=[x for x in candidates if x<=local]; target=max(eligible) if eligible else None
    return (target,round((local-target).total_seconds()/60,2)) if target else (None,None)

def _slot_done(path,target):
    if target is None or not path.exists(): return False
    key=target.isoformat()
    for line in path.read_text(encoding='utf-8').splitlines():
        try:r=json.loads(line)
        except json.JSONDecodeError:continue
        if isinstance(r,dict) and str(r.get('scheduled_target_at'))==key and (r.get('state') is None or str(r.get('state')) in {'OBSERVED','ZERO_FIXTURES'}):return True
    return False

def _record_slot(path,report,state,reason=None):
    row={'scheduled_target_at':report.get('scheduled_target_at'),'football_day':report.get('football_day'),'state':state,'actual_observed_at':report.get('actual_observed_at'),'schedule_lag_minutes':report.get('schedule_lag_minutes'),'observation_timing':report.get('observation_timing'),'requests_used':report.get('requests_used',0),'football_day_fixtures':report.get('football_day_fixtures'),'strict_snapshots':report.get('strict_snapshots_this_run'),'reason':reason or report.get('status'),'finalized_at':report.get('generated_at')}
    rows={}
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            try:r=json.loads(line)
            except json.JSONDecodeError:continue
            if isinstance(r,dict) and r.get('scheduled_target_at'):rows[str(r['scheduled_target_at'])]=r
    rows[str(row['scheduled_target_at'])]=row
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for _,x in sorted(rows.items())),encoding='utf-8')

def _parse(v):
    try:
        x=datetime.fromisoformat(str(v).replace('Z','+00:00')); return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
    except (TypeError,ValueError):return None

def _write(r,root):
    p=root/REPORT_PATH;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');return r

def _chunks(v,n):
    for i in range(0,len(v),n):yield v[i:i+n]

def run(root=Path('.')):
    now=datetime.now(timezone.utc); ws,we,day=_football_day_bounds(now); target,lag=_schedule_timing(now); force=os.getenv('RESEARCH_V2_FORCE_RUN','').strip().lower() in {'1','true','yes'}; force_target=os.getenv('RESEARCH_V2_FORCE_TARGET_AT','').strip()
    if force and force_target:
        parsed=_parse(force_target)
        if parsed is not None:
            target=parsed.astimezone(BANGKOK); lag=round((now.astimezone(BANGKOK)-target).total_seconds()/60,2)
    report={'schema_version':'2.8','generated_at':now.isoformat(),'classification':'PINNACLE_RESEARCH_V2','bookmaker':BOOKMAKER,'football_day':day,'football_day_timezone':'Asia/Bangkok','football_day_window_start':ws.isoformat(),'football_day_window_end':we.isoformat(),'scheduled_target_at':target.isoformat() if target else None,'actual_observed_at':now.astimezone(BANGKOK).isoformat(),'schedule_lag_minutes':lag,'recovery_window_minutes':RECOVERY_WINDOW_MINUTES,'observation_timing':'ON_TIME' if lag is not None and lag<=30 else ('LATE' if lag is not None and lag<=RECOVERY_WINDOW_MINUTES else 'OUTSIDE_WINDOW'),'force_run':force,'force_target_at':force_target or None,'research_only':True,'production_promotion_allowed':False,'core_quota_reserve':CORE_QUOTA_RESERVE}
    if _slot_done(root/SLOT_LEDGER_PATH,target) or _slot_done(root/AUDIT_PATH,target): report.update(status='SKIPPED_SLOT_ALREADY_OBSERVED',requests_used=0,planned_requests=0);return _write(report,root)
    if not force and (lag is None or lag>RECOVERY_WINDOW_MINUTES): report.update(status='MISSED_SLOT',requests_used=0,planned_requests=0);_record_slot(root/SLOT_LEDGER_PATH,report,'MISSED');return _write(report,root)
    targets=_load_json(root/TARGET_PATH) or {}; selected=targets.get('tournaments') or [] if isinstance(targets,dict) else []; ids=[x.get('tournament_id') for x in selected if isinstance(x,dict) and x.get('tournament_id') is not None]
    if not ids or len(ids)!=len(set(ids)):report.update(status='TARGET_MAP_INVALID',resolved_competitions=len(ids),requests_used=0,planned_requests=0);return _write(report,root)
    normal=(len(ids)+BATCH_SIZE-1)//BATCH_SIZE; maxplan=normal*MAX_ATTEMPTS_PER_BATCH; report.update(resolved_competitions=len(ids),planned_requests=normal,max_planned_requests_with_retries=maxplan)
    key=os.getenv(ENV_KEY,'').strip()
    if not key:report.update(status='API_KEY_NOT_CONFIGURED',requests_used=0);return _write(report,root)
    try:q=summarize_account(_get('/account',key))
    except Exception as e:report.update(status='SKIPPED_QUOTA_HEALTH_UNAVAILABLE',requests_used=0,errors=[f'{type(e).__name__}: {e}']);return _write(report,root)
    report['quota_remaining_before']=q.get('request_remaining')
    try: remaining=int(q.get('request_remaining'))
    except (TypeError,ValueError): remaining=-1
    if remaining-normal < CORE_QUOTA_RESERVE:report.update(status='SKIPPED_TO_PROTECT_CORE_QUOTA',requests_used=0);return _write(report,root)
    catalog=_load_json(root/CATALOG_PATH) or []; meta={int(x['tournament_id']):x for x in selected}; payloads=[]; used=0; retries=0
    for bn,batch in enumerate(_chunks(ids,BATCH_SIZE),1):
        if bn>1:time.sleep(INTER_BATCH_DELAY_SECONDS)
        payload=None
        for attempt in range(1,MAX_ATTEMPTS_PER_BATCH+1):
            try:payload=_get('/odds-by-tournaments',key,{'tournamentIds':','.join(str(x) for x in batch),'bookmakers':BOOKMAKER,'language':'en','verbosity':3},90);used+=1;break
            except Exception as e:
                used+=1
                if getattr(e,'code',None)==429 and attempt<MAX_ATTEMPTS_PER_BATCH:retries+=1;time.sleep(RATE_LIMIT_RETRY_DELAY_SECONDS);continue
                report.update(status='API_REQUEST_FAILED',requests_used=used,rate_limit_retries=retries,errors=[f'{type(e).__name__}: {e}']);return _write(report,root)
        payloads.append(payload)
    strict=[];diag=[];audit=[];alln=0;excluded=0
    for payload in payloads:
        for f in _rows(payload):
            alln+=1;k=_parse(f.get('startTime'))
            if k is None or not(ws<=k<we):excluded+=1;continue
            tm={**(meta.get(int(f.get('tournamentId') or -1)) or {}),'universe':'PINNACLE_RESEARCH_V2'};book=(f.get('bookmakerOdds') or {}).get(BOOKMAKER);active=isinstance(book,dict) and book.get('bookmakerIsActive') is True and book.get('suspended') is False;shape=mainline_shape(f,catalog,bookmaker=BOOKMAKER);snap,reason=extract_mainline_snapshot(f,catalog,observed_at=now,tournament_meta=tm,bookmaker=BOOKMAKER)
            diag.append({'country':tm.get('country'),'league':tm.get('tournament_name'),'fixture_id':f.get('fixtureId'),'bookmaker_active':active,'ah_main_count':shape.get('ah_main_count',0),'ou_main_count':shape.get('ou_main_count',0),'strict_snapshot':snap is not None,'reason':reason});audit.append({'football_day':day,'fixture_id':f.get('fixtureId'),'tournament_id':f.get('tournamentId'),'country':tm.get('country'),'league':tm.get('tournament_name'),'home':f.get('participant1Name'),'away':f.get('participant2Name'),'kickoff':f.get('startTime'),'observed_at':now.isoformat(),'scheduled_target_at':target.isoformat() if target else None,'schedule_lag_minutes':lag,'observation_timing':report['observation_timing'],'bookmaker':BOOKMAKER,'eligibility_status':'MATCH' if snap else 'NOT_MATCH','eligibility_reason':reason,'research_population':True})
            if snap:snap.update(football_day=day,research_only=True,scheduled_target_at=target.isoformat() if target else None,schedule_lag_minutes=lag,observation_timing=report['observation_timing']);strict.append(snap)
    ts=_merge_jsonl(root/SNAPSHOT_PATH,strict,('observed_at','fixture_id'));ta=_merge_jsonl(root/AUDIT_PATH,audit,('observed_at','fixture_id'));report.update(status='RESEARCH_V2_OBSERVED',requests_used=used,rate_limit_retries=retries,api_fixtures_returned=alln,excluded_outside_football_day=excluded,football_day_fixtures=len(audit),strict_snapshots_this_run=len(strict),persisted_snapshot_rows=ts,persisted_audit_rows=ta,**summarize_rows(diag));_record_slot(root/SLOT_LEDGER_PATH,report,'OBSERVED' if len(audit)>0 else 'ZERO_FIXTURES');return _write(report,root)

if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False))
