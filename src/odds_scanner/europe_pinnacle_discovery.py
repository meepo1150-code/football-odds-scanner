from __future__ import annotations

from .research_population import in_scope, exclusion_reason, POLICY
from .master_scan_scope import filter_scan_targets
from . import master_schedule_plan as schedule
import json, os, time
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from email.utils import parsedate_to_datetime
from .research_request_budget import allocation
from .research_quota_checkpoint import reserve, ResearchQuotaBlocked
from .provider_request_budget import QuotaBlocked, ACCOUNT_RESERVE
from .europe_bookmaker_coverage_probe import BOOKMAKER, quota_allows_probe, summarize_rows

# Research V2 is the primary forward data collector. Keep a small emergency reserve,
# while background/history jobs yield to the canonical weekend observations.
# OddsPapi /odds-by-tournaments rejects oversized tournament batches. Keep this at 5; tests lock the provider-safe ceiling.
CORE_QUOTA_RESERVE = 3
from .oddspapi_discovery import _rows
from .oddspapi_provider import ENV_KEY, _get
from .oddspapi_quota_health import summarize_account, read_account
from .v2_mainline_observer import CATALOG_PATH, _load_json, extract_mainline_snapshot, mainline_shape

TARGET_PATH=Path('reports/europe_discovery_tournaments.json'); SNAPSHOT_PATH=Path('data/normalized/europe_pinnacle_research_v2_snapshots.jsonl'); AUDIT_PATH=Path('data/normalized/europe_pinnacle_research_v2_audit.jsonl'); REPORT_PATH=Path('reports/europe_pinnacle_research_v2_status.json'); SLOT_LEDGER_PATH=Path('data/normalized/research_v2_slot_ledger.jsonl')
BANGKOK=ZoneInfo('Asia/Bangkok'); FOOTBALL_DAY_START_HOUR=12; FOOTBALL_DAY_END_HOUR=6; BATCH_SIZE=5; LOW_QUOTA_CORE_IDS=(17,23,8,35,34); LOW_QUOTA_THRESHOLD=6; INTER_BATCH_DELAY_SECONDS=2.0; MAX_ATTEMPTS_PER_BATCH=1; RECOVERY_WINDOW_MINUTES=150; WEEKEND_TARGET_HOURS=(12,15,18,19,20,21,22)

def _rate_limit_until(exc, now):
    """Persist a conservative cooldown; never shorten a provider Retry-After."""
    until = now + timedelta(hours=1)
    value = (getattr(exc, 'headers', None) or {}).get('Retry-After')
    if value:
        try:
            requested = now + timedelta(seconds=max(0, int(value)))
        except (TypeError, ValueError, OverflowError):
            try:
                requested = parsedate_to_datetime(value)
                if requested.tzinfo is None:
                    requested = requested.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError, OverflowError):
                requested = until
        until = max(until, requested)
    return until.isoformat()

def _merge_jsonl(path,new_rows,key_fields):
    # Exact-record dedupe only: divergent quotes with identical identity/time
    # remain forensic evidence, never silently replaced by a later record.
    existing=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()] if path.exists() else []
    keys={json.dumps(row,sort_keys=True,ensure_ascii=False) for row in existing}
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as handle:
        for row in new_rows:
            key=json.dumps(row,sort_keys=True,ensure_ascii=False)
            if key not in keys:
                handle.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
                keys.add(key)
    return len(keys)

def _football_day_bounds(now):
    local=now.astimezone(BANGKOK); label=local.date()-timedelta(days=1) if local.time()<dtime(FOOTBALL_DAY_END_HOUR) else local.date(); start=datetime.combine(label,dtime(12),BANGKOK); end=datetime.combine(label+timedelta(days=1),dtime(6),BANGKOK); return start.astimezone(timezone.utc),end.astimezone(timezone.utc),label.isoformat()

def _schedule_timing(now):
    from .research_v2_slots import targets
    local=now.astimezone(BANGKOK); candidates=[]
    for delta in (-1,0):
        day=local.date()+timedelta(days=delta)
        candidates.extend(targets(day))
    eligible=[x for x in candidates if x<=local]; target=max(eligible) if eligible else None
    return (target,round((local-target).total_seconds()/60,2)) if target else (None,None)

def _slot_done(path,target):
    from .research_v2_slots import completed, read_snapshots
    if target is None or not path.exists(): return False
    rows=[]
    for line in path.read_text().splitlines():
        try: row=json.loads(line)
        except ValueError: continue
        if isinstance(row,dict): rows.append(row)
    return completed(target, datetime.now(timezone.utc), rows, read_snapshots(path.parents[2]))

def _record_slot(path,report,state,reason=None):
    from .research_v2_slots import schedule_version
    if state == 'ZERO_FIXTURES' and report.get('coverage_complete') is False:
        state = 'ZERO_COHORT'
    row={'scheduled_target_at':report.get('scheduled_target_at'),'provider':report.get('provider','oddspapi'),'football_day':report.get('football_day'),'state':state,'actual_observed_at':report.get('actual_observed_at'),'schedule_lag_minutes':report.get('schedule_lag_minutes'),'observation_timing':report.get('observation_timing'),'requests_used':report.get('requests_used',0),'football_day_fixtures':report.get('football_day_fixtures'),'strict_snapshots':report.get('strict_snapshots_this_run'),'reason':reason or report.get('status'),'finalized_at':report.get('generated_at'),'collection_succeeded':report.get('status') in {'RESEARCH_V2_OBSERVED','ZERO_USABLE_FIXTURES'} and not report.get('errors')}
    row['schedule_version'] = schedule_version(row.get('football_day') or '')
    row['coverage_complete'] = report.get('coverage_complete')
    row['coverage_tournament_ids'] = report.get('coverage_tournament_ids')
    row['http_requests_attempted'] = report.get('http_requests_attempted',report.get('requests_used',0))
    row['request_completed_at'] = report.get('request_completed_at')
    row['budget_reservation_id'] = report.get('budget_reservation_id')
    for field in ('master_competitions_considered', 'daily_cohort_policy', 'daily_cohort_query_complete', 'daily_cohort_fixture_count', 'daily_cohort_fixtures'):
        if field in report:
            row[field] = report[field]
    _merge_jsonl(path,[row],('scheduled_target_at','finalized_at'))

def _parse(v):
    try:
        x=datetime.fromisoformat(str(v).replace('Z','+00:00')); return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
    except (TypeError,ValueError):return None

def _write(r,root):
    from .scan_health import record
    if r.get('daily_cohort_policy') and not r.get('daily_cohort_query_complete'):
        from .daily_scan_cohort import cohort, annotate
        setup = cohort(root, r['football_day'])
        if setup is not None and 'collection_started_at' not in r:
            requested = r.get('coverage_tournament_ids', []) if r.get('status') == 'API_REQUEST_FAILED' else []
            annotate(r, setup, datetime.now(timezone.utc), requested, errors=True)
    if r.get('status') == 'SKIPPED_QUOTA' or str(r.get('status', '')).startswith('SKIPPED_QUOTA_PROVIDER_'):
        _record_slot(root/SLOT_LEDGER_PATH, r, 'SKIPPED_QUOTA')
    record(root, r, 'oddspapi')
    p=root/REPORT_PATH;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');return r

def _chunks(v,n):
    for i in range(0,len(v),n):yield v[i:i+n]

def run(root=Path('.')):
    now=datetime.now(timezone.utc); ws,we,day=_football_day_bounds(now); target,lag=_schedule_timing(now); force=os.getenv('RESEARCH_V2_FORCE_RUN','').strip().lower() in {'1','true','yes'}; force_target=os.getenv('RESEARCH_V2_FORCE_TARGET_AT','').strip()
    if force and force_target:
        parsed=_parse(force_target)
        if parsed is not None:
            target=parsed.astimezone(BANGKOK); lag=round((now.astimezone(BANGKOK)-target).total_seconds()/60,2)
    report={'schema_version':'2.9','generated_at':now.isoformat(),'classification':'PINNACLE_RESEARCH_V2','bookmaker':BOOKMAKER,'football_day':day,'football_day_timezone':'Asia/Bangkok','football_day_window_start':ws.isoformat(),'football_day_window_end':we.isoformat(),'scheduled_target_at':target.isoformat() if target else None,'actual_observed_at':now.astimezone(BANGKOK).isoformat(),'schedule_lag_minutes':lag,'recovery_window_minutes':RECOVERY_WINDOW_MINUTES,'observation_timing':'ON_TIME' if lag is not None and lag<=30 else ('LATE' if lag is not None and lag<=RECOVERY_WINDOW_MINUTES else 'OUTSIDE_WINDOW'),'force_run':force,'force_target_at':force_target or None,'research_only':True,'production_promotion_allowed':False,'core_quota_reserve':CORE_QUOTA_RESERVE}
    previous = _load_json(root/REPORT_PATH) or {}
    cooldown = _parse(previous.get('rate_limit_cooldown_until'))
    if cooldown is not None and now < cooldown:
        report.update(status='SKIPPED_QUOTA_PROVIDER_COOLDOWN', data_source_health='RATE_LIMITED_COOLDOWN',
                      rate_limit_cooldown_until=cooldown.isoformat(), requests_used=0,
                      planned_requests=0, quota_skip_reason='PROVIDER_COOLDOWN')
        return _write(report, root)
    manual=os.getenv('RESEARCH_V2_MANUAL_BREADTH','').lower()=='true'
    report['manual_supplementary_scan']=manual
    if manual:
        from .research_v2_slots import read_ledger,provider_attempt_receipt,stamp
        recent=[stamp(r.get('request_completed_at') or r.get('actual_observed_at')) for r in read_ledger(root) if provider_attempt_receipt(r)]
        recent=[x for x in recent if x]
        if recent and now-max(recent)<timedelta(minutes=15):
            report.update(status='SKIPPED_MINIMUM_OBSERVATION_SPACING',requests_used=0);return _write(report,root)
    if not manual and _slot_done(root/SLOT_LEDGER_PATH,target): report.update(status='SKIPPED_SLOT_ALREADY_OBSERVED',requests_used=0,planned_requests=0);return _write(report,root)
    if lag is None or lag<0 or lag>RECOVERY_WINDOW_MINUTES: report.update(status='MISSED_SLOT',requests_used=0,planned_requests=0);_record_slot(root/SLOT_LEDGER_PATH,report,'MISSED');return _write(report,root)
    master_mode=(root/'data/master/provider_mappings.csv').exists()
    cached=schedule.cached_schedule(root,ws,we,now) if master_mode else None
    overhead=1 if master_mode and cached is None else 0
    targets=_load_json(root/TARGET_PATH) or {}; selected=targets.get('tournaments') or [] if isinstance(targets,dict) else []
    if master_mode:
        selected=schedule.registry()
        saved=_load_json(root/'reports/master_provider_snapshot.json') or {}
        _,scope=schedule.plan(saved.get('fixtures',[]),ws,we,now,complete=False)
        report.update(scope)
    original_count = len(selected)
    from .master_scan_scope import scan_scope_reason
    report['forward_scope_policy']='VERIFIED_ACTIVE_MASTER_81_DIVISIONS_PLUS_8_DOMESTIC_CUPS_AND_3_UEFA_CLUB_COMPETITIONS'
    report['master_scope_rejections']=[{'provider':'oddspapi','tournament_id':r.get('tournament_id'),
        'country':r.get('country'),'league':r.get('tournament_name'),
        'reason':exclusion_reason(r,provider='oddspapi') or scan_scope_reason(r,provider='oddspapi')}
        for r in selected if exclusion_reason(r,provider='oddspapi') or scan_scope_reason(r,provider='oddspapi')]
    selected = filter_scan_targets(selected)
    fixed = None
    if master_mode and not manual and day >= '2026-10-14' and target.hour != 15:
        from .daily_scan_cohort import cohort, annotate
        fixed = cohort(root, day)
        if fixed is None:
            report.update(status='DAILY_COHORT_UNAVAILABLE', requests_used=0,
                          errors=['Retained 15:00 setup evidence is required; no new cohort substituted'])
            return _write(report, root)
        pending = {str(f['tournament_id']) for f in fixed['fixtures'] if schedule.stamp(f['kickoff']) > now}
        selected = [r for r in selected if str(r['tournament_id']) in pending]
        annotate(report, fixed, now)
        if not pending:
            report.update(status='ZERO_USABLE_FIXTURES', requests_used=0, football_day_fixtures=0,
                          strict_snapshots_this_run=0, coverage_complete=True)
            _record_slot(root/SLOT_LEDGER_PATH, report, 'ZERO_FIXTURES')
            return _write(report, root)
    report['master_scope_excluded_targets'] = original_count - len(selected)
    ids=[x.get('tournament_id') for x in selected if isinstance(x,dict) and x.get('tournament_id') is not None]
    if original_count and not selected:
        report.update(status='SKIPPED_USER_EXCLUDED_COMPETITIONS',resolved_competitions=0,requests_used=0,planned_requests=0)
        return _write(report,root)
    if not ids or len(ids)!=len(set(ids)):report.update(status='TARGET_MAP_INVALID',resolved_competitions=len(ids),requests_used=0,planned_requests=0);return _write(report,root)
    normal=(len(ids)+BATCH_SIZE-1)//BATCH_SIZE; maxplan=normal*MAX_ATTEMPTS_PER_BATCH; report.update(resolved_competitions=len(ids),planned_requests=normal,max_planned_requests_with_retries=maxplan,coverage_mode='FULL_RESEARCH_UNIVERSE')
    try:
        ids, budget = allocation(root/SLOT_LEDGER_PATH, ids, now, BATCH_SIZE, prioritized=master_mode, overhead=overhead, manual=manual)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        report.update(status='TARGET_MAP_INVALID', requests_used=0, errors=['Request budget ledger invalid: '+str(exc)])
        return _write(report, root)
    report.update(budget)
    if not ids:
        if master_mode:schedule.finish_coverage(report,[],[])
        report.update(status='SKIPPED_QUOTA', requests_used=0, planned_requests=0,
                      quota_skip_reason='RESEARCH_CAPACITY_RESERVED_OR_EXHAUSTED', data_source_health='NOT_PROBED_BUDGET_LIMIT', next_action='FREE_COLLECTORS_CONTINUE')
        return _write(report, root)
    selected=[x for x in selected if x.get('tournament_id') in ids]
    normal=(len(ids)+BATCH_SIZE-1)//BATCH_SIZE
    report.update(resolved_competitions=len(ids), planned_requests=normal, max_planned_requests_with_retries=normal)
    key=os.getenv(ENV_KEY,'').strip()
    if not key:report.update(status='API_KEY_NOT_CONFIGURED',requests_used=0);return _write(report,root)
    try:q=summarize_account(read_account(key, getter=_get, diagnostics=report))
    except Exception as e:
        report.update(status='SKIPPED_QUOTA_HEALTH_UNAVAILABLE',requests_used=0,
                      data_source_health='ACCOUNT_UNAVAILABLE',errors=[type(e).__name__])
        return _write(report,root)
    report['quota_remaining_before']=q.get('request_remaining')
    try: remaining=int(q.get('request_remaining'))
    except (TypeError,ValueError): remaining=-1
    if not master_mode and 0 <= remaining <= LOW_QUOTA_THRESHOLD:
        selected=[x for x in selected if int(x.get('tournament_id') or -1) in LOW_QUOTA_CORE_IDS]
        ids=[x.get('tournament_id') for x in selected]
        normal=(len(ids)+BATCH_SIZE-1)//BATCH_SIZE
        maxplan=normal*MAX_ATTEMPTS_PER_BATCH
        report.update(coverage_mode='LOW_QUOTA_BIG5_TOP_FLIGHT',resolved_competitions=len(ids),planned_requests=normal,max_planned_requests_with_retries=maxplan,coverage_tournament_ids=ids)
    # The reserve protects future canonical observations, not the current canonical
    # observation itself. Once quota falls to the reserve, spend it only on a current
    # canonical slot; background/history workflows remain responsible for yielding.
    effective_reserve = ACCOUNT_RESERVE + budget['future_utc_requests_reserved']
    month_minimum = (budget['future_month_requests_reserved']
                     + budget['future_utc_requests_reserved'] + overhead + 1)
    report['account_safety_reserve'] = ACCOUNT_RESERVE
    report['account_minimum_requests_through_month_end'] = month_minimum
    report['account_month_capacity_shortfall'] = max(0, month_minimum + ACCOUNT_RESERVE - remaining)
    # Breadth is optional. Keep the minimum market call available today even
    # when earlier account usage makes all remaining days impossible to fund.
    if fixed is None and normal > 1 and remaining - normal - overhead < ACCOUNT_RESERVE + month_minimum - overhead - 1:
        ids = ids[:BATCH_SIZE]
        selected = [x for x in selected if x.get('tournament_id') in ids]
        normal = 1
        report.update(planned_requests=normal, coverage_tournament_ids=ids,
                      account_optional_breadth_deferred=True)
    report['effective_quota_reserve']=effective_reserve
    if not ids or remaining-normal-overhead < effective_reserve:report.update(status='SKIPPED_QUOTA',quota_skip_reason='ACCOUNT_CAPACITY_RESERVED_OR_EXHAUSTED',requests_used=0);return _write(report,root)
    try:
        ids, budget, reservation_id, grant = reserve(root, ids, datetime.now(timezone.utc), overhead=overhead, manual=manual)
    except ResearchQuotaBlocked as exc:
        report.update(status='SKIPPED_QUOTA', quota_skip_reason=str(exc), requests_used=0, planned_requests=0)
        return _write(report, root)
    report.update(budget, budget_reservation_id=reservation_id, research_requests_reserved_this_run=grant)
    selected=[x for x in selected if x['tournament_id'] in ids]
    quota_day=datetime.fromisoformat(budget['quota_utc_day']).date()
    used=0;retries=0
    def metered_get(endpoint, params, timeout):
        nonlocal used
        if used >= grant or datetime.now(timezone.utc).date() != quota_day:
            raise ResearchQuotaBlocked('Grant exhausted or UTC day changed before transport')
        try:
            payload=_get(endpoint,key,params,timeout)
        except QuotaBlocked:
            # The shared transport guard rejected before issuing HTTP.
            raise
        except Exception:
            used+=1
            raise
        used+=1
        return payload
    if master_mode:
        try:
            if cached is None:
                if datetime.now(timezone.utc)>target+timedelta(minutes=RECOVERY_WINDOW_MINUTES):
                    report.update(status='RECOVERY_WINDOW_EXPIRED_BEFORE_ODDS',requests_used=0);return _write(report,root)
                params={'sportId':10,'from':ws.isoformat(),'to':we.isoformat(),'limit':schedule.SCHEDULE_LIMIT,'language':'en'}
                payload=metered_get('/fixtures',params,60)
                response_at=datetime.now(timezone.utc)
                cached=schedule.retain(root,'/fixtures',params,payload,response_at)
                report['request_completed_at']=response_at.isoformat()
            schedule_rows=schedule.items(cached['payload'])
            # A limit-sized or explicitly paginated response cannot prove absence.
            complete=len(schedule_rows)<schedule.SCHEDULE_LIMIT and isinstance(cached['payload'],list)
            selected,scope=schedule.plan(schedule_rows,ws,we,datetime.now(timezone.utc),complete=complete)
            report.update(scope,schedule_response_id=cached['response_id'],schedule_observed_at=cached['observed_at'],schedule_requests_used=used)
            selected=schedule.prioritize(root,selected,report,datetime.now(timezone.utc))
            if fixed is not None:
                pending = {str(f['tournament_id']) for f in fixed['fixtures'] if schedule.stamp(f['kickoff']) > datetime.now(timezone.utc)}
                # The follow-up cannot rotate into unseen tournaments.
                selected = [r for r in selected if str(r['tournament_id']) in pending]
                selected.sort(key=lambda r: r['tournament_id'])
            ids=[x['tournament_id'] for x in selected][:max(0,grant-used)*BATCH_SIZE]
            report['coverage_tournament_ids']=ids
            selected=[x for x in selected if x['tournament_id'] in ids]
            report.update(resolved_competitions=len(ids),planned_requests=used+(len(ids)+BATCH_SIZE-1)//BATCH_SIZE,coverage_tournament_ids=ids)
            if not ids:
                schedule.finish_coverage(report,[],[])
                report.update(status='SKIPPED_QUOTA' if scope['remaining_prematch_competitions'] else 'ZERO_USABLE_FIXTURES',quota_skip_reason='RUN_GRANT_EXHAUSTED' if scope['remaining_prematch_competitions'] else None,requests_used=used,strict_snapshots_this_run=0,football_day_fixtures=0,coverage_complete=complete and not scope['remaining_prematch_competitions'])
                _record_slot(root/SLOT_LEDGER_PATH,report,'ZERO_FIXTURES');return _write(report,root)
        except (QuotaBlocked, ResearchQuotaBlocked) as exc:
            report.update(status='SKIPPED_QUOTA', quota_skip_reason=str(exc), requests_used=used)
            _record_slot(root/SLOT_LEDGER_PATH,report,'SKIPPED_QUOTA');return _write(report,root)
        except Exception as exc:
            failed_at=datetime.now(timezone.utc)
            report.update(status='SCHEDULE_REQUEST_FAILED',requests_used=used,errors=[type(exc).__name__],request_completed_at=failed_at.isoformat())
            if getattr(exc,'code',None)==429:report['rate_limit_cooldown_until']=_rate_limit_until(exc,failed_at)
            _record_slot(root/SLOT_LEDGER_PATH,report,'FAILED');return _write(report,root)
    catalog=_load_json(root/CATALOG_PATH) or []; meta={int(x['tournament_id']):x for x in selected}; payloads=[]
    request_failed=False
    for bn,batch in enumerate(_chunks(ids,BATCH_SIZE),1):
        if bn>1:time.sleep(INTER_BATCH_DELAY_SECONDS)
        if datetime.now(timezone.utc)>target+timedelta(minutes=RECOVERY_WINDOW_MINUTES):
            report['recovery_window_expired_during_collection']=True
            break
        payload=None
        for attempt in range(1,MAX_ATTEMPTS_PER_BATCH+1):
            try:payload=metered_get('/odds-by-tournaments',{'tournamentIds':','.join(str(x) for x in batch),'bookmakers':BOOKMAKER,'language':'en','verbosity':3},90);break
            except (QuotaBlocked, ResearchQuotaBlocked) as e:
                report.update(status='SKIPPED_QUOTA',quota_skip_reason=str(e),requests_used=used)
                request_failed=True
                break
            except Exception as e:
                failed_at=datetime.now(timezone.utc)
                report.update(generated_at=failed_at.isoformat(),actual_observed_at=failed_at.astimezone(BANGKOK).isoformat(),request_completed_at=failed_at.isoformat())
                if getattr(e,'code',None)==429:
                    report.update(data_source_health='RATE_LIMITED', rate_limit_cooldown_until=_rate_limit_until(e, failed_at))
                report.update(status='API_REQUEST_FAILED',requests_used=used,rate_limit_retries=retries,errors=[f'{type(e).__name__}: {e}'])
                request_failed=True
                break
        if request_failed:break
        response_at=datetime.now(timezone.utc)
        report['request_completed_at']=response_at.isoformat()
        schedule.retain(root,'/odds-by-tournaments',{'tournamentIds':','.join(map(str,batch)),'bookmakers':BOOKMAKER,'language':'en','verbosity':3},payload,response_at)
        payloads.append((payload,response_at,set(map(str,batch))))
    if not payloads:
        if request_failed:
            if fixed is not None:
                from .daily_scan_cohort import annotate
                annotate(report, fixed, datetime.now(timezone.utc), ids, errors=True)
            _record_slot(root/SLOT_LEDGER_PATH,report,'FAILED');return _write(report,root)
        report.update(status='RECOVERY_WINDOW_EXPIRED_BEFORE_ODDS',requests_used=used,actual_observed_at=None,generated_at=datetime.now(timezone.utc).isoformat())
        _record_slot(root/SLOT_LEDGER_PATH,report,'MISSED');return _write(report,root)
    observed_at=payloads[-1][1]
    lag=round((observed_at-target).total_seconds()/60,2)
    report.update(generated_at=datetime.now(timezone.utc).isoformat(),actual_observed_at=observed_at.astimezone(BANGKOK).isoformat(),
        schedule_lag_minutes=lag,observation_timing='ON_TIME' if lag<=30 else 'LATE' if lag<=RECOVERY_WINDOW_MINUTES else 'OUTSIDE_WINDOW',
        collection_started_at=now.isoformat(),excluded_unrequested_scope_fixtures=0,invalid_payload_batches=0)
    strict=[];diag=[];audit=[];alln=0;excluded=0
    for payload,observed_at,requested_ids in payloads:
        batch_lag=round((observed_at-target).total_seconds()/60,2)
        timing='ON_TIME' if batch_lag<=30 else 'LATE' if batch_lag<=RECOVERY_WINDOW_MINUTES else 'OUTSIDE_WINDOW'
        items=payload if isinstance(payload,list) else next((payload.get(k) for k in ('data','fixtures','results') if isinstance(payload.get(k),list)),None) if isinstance(payload,dict) else None
        if items is None or any(not isinstance(r,dict) for r in items):
            report['invalid_payload_batches']+=1
            continue
        for f in _rows(payload):
            alln+=1;k=_parse(f.get('startTime'))
            if str(f.get('tournamentId')) not in requested_ids or scan_scope_reason(f,provider='oddspapi'):
                report['excluded_unrequested_scope_fixtures']+=1
                continue
            if k is None or not(ws<=k<we):excluded+=1;continue
            if fixed is not None and str(f.get('fixtureId')) not in {r['fixture_id'] for r in fixed['fixtures']}:
                report['excluded_outside_daily_cohort'] = report.get('excluded_outside_daily_cohort', 0) + 1
                continue
            tm={**(meta.get(int(f.get('tournamentId') or -1)) or {}),'universe':'PINNACLE_RESEARCH_V2'};book=(f.get('bookmakerOdds') or {}).get(BOOKMAKER);active=isinstance(book,dict) and book.get('bookmakerIsActive') is True and book.get('suspended') is False;shape=mainline_shape(f,catalog,bookmaker=BOOKMAKER)
            try:snap,reason=extract_mainline_snapshot(f,catalog,observed_at=observed_at,tournament_meta=tm,bookmaker=BOOKMAKER)
            except ValueError:snap=None;reason='MASTER_CANONICAL_ID_CONFLICT'
            if master_mode and snap and not all(snap.get(k) for k in ('canonical_competition_id','home_club_id','away_club_id')):
                snap=None;reason='MASTER_CLUB_UNMAPPED'
            diag.append({'country':tm.get('country'),'league':tm.get('tournament_name'),'fixture_id':f.get('fixtureId'),'bookmaker_active':active,'ah_main_count':shape.get('ah_main_count',0),'ou_main_count':shape.get('ou_main_count',0),'strict_snapshot':snap is not None,'reason':reason});audit.append({'football_day':day,'fixture_id':f.get('fixtureId'),'tournament_id':f.get('tournamentId'),'country':tm.get('country'),'league':tm.get('tournament_name'),'home':f.get('participant1Name'),'away':f.get('participant2Name'),'kickoff':f.get('startTime'),'observed_at':observed_at.isoformat(),'scheduled_target_at':target.isoformat() if target else None,'schedule_lag_minutes':batch_lag,'observation_timing':timing,'bookmaker':BOOKMAKER,'eligibility_status':'MATCH' if snap else 'NOT_MATCH','eligibility_reason':reason,'research_population':True})
            if snap and in_scope(snap):snap.update(football_day=day,research_only=True,scheduled_target_at=target.isoformat() if 0<=batch_lag<=RECOVERY_WINDOW_MINUTES else None,attempted_target_at=target.isoformat(),schedule_lag_minutes=batch_lag,observation_timing=timing);strict.append(snap)
    if fixed is not None:
        for snapshot in strict:
            snapshot.update(daily_cohort_policy=fixed['policy'], daily_cohort_setup_target_at=fixed['setup_target_at'])
    ts=_merge_jsonl(root/SNAPSHOT_PATH,strict,('observed_at','fixture_id'));ta=_merge_jsonl(root/AUDIT_PATH,audit,('observed_at','fixture_id'));report.update(status='RESEARCH_V2_OBSERVED',requests_used=used,rate_limit_retries=retries,api_fixtures_returned=alln,excluded_outside_football_day=excluded,football_day_fixtures=len(audit),strict_snapshots_this_run=len(strict),persisted_snapshot_rows=ts,persisted_audit_rows=ta,**summarize_rows(diag))
    if master_mode:
        schedule.finish_coverage(report,ids,audit,request_failed)
        schedule.prioritize(root,[],report,datetime.now(timezone.utc))
        report['additional_market_requests_required']= (sum(r['reason']=='QUOTA_SKIPPED' for r in report['competition_coverage'])+BATCH_SIZE-1)//BATCH_SIZE
    invalid=report['invalid_payload_batches'] or report['excluded_unrequested_scope_fixtures']
    if invalid:
        report.setdefault('errors',[]).append('PROVIDER_PAYLOAD_OR_REQUESTED_SCOPE_REJECTED')
    if request_failed or invalid or report.get('recovery_window_expired_during_collection'):
        report['coverage_complete']=False
        report['data_source_health']=report.get('data_source_health','PARTIAL')
    state='OBSERVED' if strict else 'FAILED' if report.get('errors') or audit else 'ZERO_FIXTURES'
    if master_mode:report['coverage_complete']=not (request_failed or invalid or report.get('recovery_window_expired_during_collection')) and report.get('schedule_response_complete',False) and not any(x['reason'] in {'QUOTA_SKIPPED','PROVIDER_ERROR','AWAITING_ODDS','NO_SCHEDULE_EVIDENCE'} for x in report.get('competition_coverage',[]))
    if state=='FAILED':report['status']='PROVIDER_RESPONSE_REJECTED' if invalid else report.get('status','API_REQUEST_FAILED') if request_failed else 'NO_VERIFIED_PREMATCH_QUOTES'
    if fixed is not None:
        from .daily_scan_cohort import annotate
        annotate(report, fixed, datetime.now(timezone.utc), ids, audit, strict,
                 errors=bool(request_failed or invalid or report.get('recovery_window_expired_during_collection')))
    _record_slot(root/SLOT_LEDGER_PATH,report,state);return _write(report,root)

if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False))
