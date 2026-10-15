"""One-off, one-request matchday price probe; never activates staged leagues."""
import json
import os
from datetime import datetime,timezone,timedelta
from pathlib import Path
import importlib.util
_spec=importlib.util.spec_from_file_location('isolated_expansion_audit',Path(__file__).with_name('audit.py'))
_audit=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_audit)
audit,stamp,BANGKOK=_audit.audit,_audit.stamp,_audit.BANGKOK
from odds_scanner.provider_request_budget import ACCOUNT_RESERVE,QuotaBlocked
from odds_scanner.research_request_budget import allocation
from odds_scanner.research_quota_checkpoint import reserve,ResearchQuotaBlocked
from odds_scanner.oddspapi_provider import _get,_safe_account_summary
from odds_scanner.oddspapi_quota_health import summarize_account
from odds_scanner.master_schedule_plan import items
from odds_scanner.v2_mainline_observer import CATALOG_PATH,extract_mainline_snapshot

DAY='2026-10-15'
OUT=Path('reports/global_expansion_matchday_probe.json')


def collect(key,root=Path('.'),*,now=None,get=None,reservation=None,audit_report=None,clock=None):
    now=now or datetime.now(timezone.utc);clock=clock or (lambda:datetime.now(timezone.utc))
    get=get or _get;reservation=reservation or reserve
    result=dict(schema_version='1.0',football_day=DAY,generated_at=now.isoformat(),
        scheduled_target_at=DAY+'T15:00:00+07:00',provider='oddspapi',bookmaker='pinnacle',
        provider_requests_attempted=0,max_provider_requests=1,account_requests_attempted=0,
        activation_allowed=False,phase3_expansion_allowed=False,research_only=True,
        certification_scope='ONLY_RETURNED_MATCHDAY_FIXTURES_NOT_ALL_588_CLUBS_OR_ALL_33_LEAGUE_MARKETS')
    if now.tzinfo is None:raise ValueError('Aware clock required')
    if now.astimezone(BANGKOK).date().isoformat()!=DAY:
        return {**result,'status':'SKIPPED_OUTSIDE_AUTHORIZED_DAY'}
    target=stamp(result['scheduled_target_at'])
    if now<target:return {**result,'status':'WAITING_1500_SCAN'}
    if now>target+timedelta(minutes=90):return {**result,'status':'SKIPPED_PROBE_WINDOW_EXPIRED'}
    if (root/OUT).exists():
        previous=json.loads((root/OUT).read_text())
        if previous.get('football_day')==DAY and previous.get('provider_requests_attempted',0)>0:
            return {**result,'status':'SKIPPED_ALREADY_PROBED','previous_report':previous}
    report=audit_report if audit_report is not None else audit(root,now=now,football_day=DAY)
    result['identity_counts']=report['counts']
    observed=stamp(report.get('schedule_observed_at'))
    if not report.get('schedule_response_complete') or not observed or not target<=observed<=now or now-observed>timedelta(minutes=90):
        return {**result,'status':'BLOCKED_NO_COMPLETE_CURRENT_SCHEDULE'}
    if report['counts']['returned_fixtures']!=report['counts']['matched_fixtures']:
        return {**result,'status':'BLOCKED_UNMATCHED_RETURNED_FIXTURES'}
    expected={};meta={}
    for league in report['leagues']:
        for fixture in league['fixture_details']:
            if fixture['mapping_status']!='PASS':return {**result,'status':'BLOCKED_UNMATCHED_RETURNED_FIXTURES'}
            if stamp(fixture['kickoff'])<=now or fixture['provider_status_id']!=0:continue
            if not league['competition_identity_verified'] or any(not s['club_id'] for s in fixture['sides']):
                return {**result,'status':'BLOCKED_UNVERIFIED_IDENTITY'}
            expected[fixture['fixture_id']]=fixture
            meta[fixture['tournament_id']]=league
    ids=sorted(meta)
    result.update(expected_fixture_ids=sorted(expected),requested_tournament_ids=ids)
    if not expected:return {**result,'status':'NO_RETURNED_PREMATCH_FIXTURES_TO_PROBE'}
    if len(ids)>5:return {**result,'status':'BLOCKED_ONE_REQUEST_BATCH_LIMIT'}
    try:
        catalog=json.loads((root/CATALOG_PATH).read_text())
        if not isinstance(catalog,list) or not catalog:raise ValueError('empty market catalog')
    except (OSError,ValueError):
        return {**result,'status':'BLOCKED_MARKET_CATALOG'}
    # No prices before all expected matchday identities pass. Full-season mapping
    # remains separately incomplete and cannot be certified by this small probe.
    chosen,budget=allocation(root/'data/normalized/research_v2_slot_ledger.jsonl',ids,now,prioritized=True,manual=True)
    result['quota_budget']=budget
    if set(chosen)!=set(ids):return {**result,'status':'SKIPPED_QUOTA'}
    if not key:return {**result,'status':'BLOCKED_PROVIDER_KEY_UNAVAILABLE'}
    try:
        result['account_requests_attempted']=1
        account=get('/account',key)
        safe=_safe_account_summary(account);summary=summarize_account(account);result['quota']=summary
    except Exception as exc:
        return {**result,'status':'BLOCKED_ACCOUNT_UNAVAILABLE','error_type':type(exc).__name__}
    if summary['status']!='QUOTA_AVAILABLE' or not summary.get('soccer_sport_id_10_allowed') or 'pinnacle' not in safe.get('bookmakers',[]):
        return {**result,'status':'BLOCKED_QUOTA_OR_PROVIDER_ENTITLEMENT'}
    if summary['request_remaining']-1<ACCOUNT_RESERVE+budget['future_utc_requests_reserved']:
        return {**result,'status':'SKIPPED_QUOTA_ACCOUNT_RESERVE'}
    try:
        selected,budget,reservation_id,grant=reservation(root,ids,now,manual=True)
    except ResearchQuotaBlocked:
        return {**result,'status':'SKIPPED_QUOTA_DURABLE_RESERVATION'}
    result.update(budget_reservation_id=reservation_id,reserved_requests=grant)
    if set(selected)!=set(ids) or grant!=1:return {**result,'status':'BLOCKED_INCOMPLETE_RESERVATION'}
    before=clock()
    if before.astimezone(timezone.utc).date()!=now.astimezone(timezone.utc).date() or before<target or before>target+timedelta(minutes=90):
        return {**result,'status':'SKIPPED_CLOCK_CHANGED_AFTER_RESERVATION'}
    params=dict(tournamentIds=','.join(ids),bookmakers='pinnacle',language='en',verbosity=3)
    try:
        result['provider_requests_attempted']=1
        payload=get('/odds-by-tournaments',key,params,90)
        fixtures=items(payload)
    except QuotaBlocked:
        return {**result,'status':'SKIPPED_QUOTA_PROVIDER_RESERVE','provider_requests_attempted':0}
    except Exception as exc:
        # Exceptions can include apiKey in URLs. Never persist repr, str or body.
        return {**result,'status':'API_REQUEST_FAILED','error_type':type(exc).__name__,'http_status':getattr(exc,'code',None)}
    observed=clock();result['actual_observed_at']=observed.isoformat()
    result['schedule_lag_minutes']=round((observed-target).total_seconds()/60,2)
    result['observation_timing']='ON_TIME' if observed<=target+timedelta(minutes=30) else 'LATE'
    quotes=[];diagnostics=[];seen=set()
    versions={}
    for f in fixtures:
        fid=str(f.get('fixtureId'));versions.setdefault(fid,set()).add(json.dumps(f,sort_keys=True))
    for f in fixtures:
        fid=str(f.get('fixtureId'))
        if fid not in expected or fid in seen:continue
        seen.add(fid);proof=expected[fid];tid=str(f.get('tournamentId'))
        if len(versions[fid])!=1:diagnostics.append(dict(fixture_id=fid,reason='CONFLICTING_PRICE_FIXTURE_VERSIONS'));continue
        if tid!=proof['tournament_id'] or any(str(f.get(f'participant{i}Id'))!=proof['sides'][i-1]['provider_id'] for i in (1,2)):
            diagnostics.append(dict(fixture_id=fid,reason='PRICE_FIXTURE_IDENTITY_MISMATCH'));continue
        try:
            quote,reason=extract_mainline_snapshot(f,catalog,observed_at=observed,
                tournament_meta=dict(tournament_id=int(tid),tournament_name=meta[tid]['competition_name']),bookmaker='pinnacle')
        except (TypeError,ValueError,KeyError):quote,reason=None,'INVALID_MARKET_PAYLOAD'
        if quote:
            quote.update(canonical_competition_id=meta[tid]['competition_id'],home_club_id=proof['sides'][0]['club_id'],
                away_club_id=proof['sides'][1]['club_id'],shadow_probe_only=True,promotion_eligible=False)
            quotes.append(quote)
        diagnostics.append(dict(fixture_id=fid,reason=reason))
    for fid in sorted(set(expected)-seen):diagnostics.append(dict(fixture_id=fid,reason='NO_ODDS_FIXTURE_RETURNED'))
    result.update(valid_price_fixtures=len(quotes),expected_fixtures=len(expected),fixture_diagnostics=diagnostics,
        status='PASS_RETURNED_MATCHDAY_PRICES' if len(quotes)==len(expected) else 'PARTIAL_PRICE_COVERAGE' if quotes else 'NO_VALID_PRICE_COVERAGE',
        raw_response=payload,shadow_snapshots=quotes)
    return result


def main():
    if os.getenv('RESEARCH_QUOTA_DURABLE')!='true':raise SystemExit('Durable shared quota reservation is required')
    result=collect(os.getenv('ODDSPAPI_KEY',''))
    payload=result.pop('raw_response',None);quotes=result.pop('shadow_snapshots',[])
    folder=Path('data/research/global_expansion_probe');folder.mkdir(parents=True,exist_ok=True)
    if payload is not None:(folder/'response-20261015.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    if quotes:(folder/'snapshots-20261015.json').write_text(json.dumps(quotes,ensure_ascii=False,indent=2)+'\n')
    OUT.parent.mkdir(parents=True,exist_ok=True)
    if result['status'] not in ('SKIPPED_ALREADY_PROBED','SKIPPED_OUTSIDE_AUTHORIZED_DAY'):
        OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k in ('status','provider_requests_attempted','expected_fixtures','valid_price_fixtures','actual_observed_at')},indent=2))


if __name__=='__main__':main()
