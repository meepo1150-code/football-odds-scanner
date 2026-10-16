"""Bounded Sep15–17 football-day experiment. Existing subscription, health and quote quality gates apply."""
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from research.historical_backfill.actions_pilot import context_gate, probe, verify_isolation
from research.historical_backfill.health_preflight import rebuild
from research.historical_backfill.isolated_runner import (StopPilot, HttpClient, quiet_window,
    health_check, load_cache, cache_path, evaluate)
from research.historical_backfill import storage
from research.historical_backfill.representative import select

def sep15_17_matchdays_context(env):
    if env.get('GITHUB_REF')!='refs/heads/research/historical-backfill-isolated-20261015' or env.get('GITHUB_EVENT_NAME') not in ('push','workflow_dispatch'):
        raise StopPilot('SEP15_17_RESEARCH_BRANCH_EVENT_REQUIRED')
    if env.get('PILOT_ENVIRONMENT')!='historical-research':
        raise StopPilot('ENVIRONMENT_REQUIRED')

BASE=Path('research/historical_backfill/sep15_17_matchdays')
BATCH=int(os.getenv('MANIFEST_BATCH_ID','0'))
OUT=BASE/'results'/('batch-'+str(BATCH))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    report=dict(status='BLOCKED',historical_requests=0,account_requests=0,cache_hits=0,
                results=[],requests=[],errors=[],research_only=True,production_writes=0)
    def save():
        report['generated_at']=datetime.now(timezone.utc).isoformat()
        text=json.dumps(report,indent=2,allow_nan=False)
        for name in ('HISTORICAL_ODDSPAPI_KEY','ACCOUNT_PROBE_KEY'):
            key=os.getenv(name)
            if key and key in text:raise SystemExit('SECRET_OUTPUT_BLOCKED')
        (OUT/'report.json').write_text(text+'\n')
    def account(key,books):
        report['account_requests']+=1
        return probe(key,books)
    production=None
    try:
        sep15_17_matchdays_context(os.environ)
        manifest=json.loads((BASE/'manifest.json').read_text())
        all_candidates=manifest['candidates']
        candidates=all_candidates
        report['batch_index']=BATCH
        report['date_range']=manifest['date_range']
        if BATCH!=0 or len(all_candidates)!=58 or manifest['max_historical_requests']!=15:
            raise StopPilot('MANIFEST_LIMIT_INVALID')
        for c in candidates:
            p=Path(c['evidence']['path'])
            line=p.read_text().splitlines()[c['evidence']['line']-1]
            if hashlib.sha256(line.encode()).hexdigest()!=c['evidence']['sha256']:
                raise StopPilot('OBSERVATION_EVIDENCE_CHANGED')
            for evidence in c['all_source_evidence']:
                source_line=p.read_text().splitlines()[evidence['line']-1]
                if hashlib.sha256(source_line.encode()).hexdigest()!=evidence['sha256']:
                    raise StopPilot('SOURCE_DAY_EVIDENCE_CHANGED')
                source_row=json.loads(source_line)
                if any(source_row[k]!=c[k] for k in ('fixture_id','home','away','kickoff','bookmaker')):
                    raise StopPilot('SOURCE_DAY_IDENTITY_MISMATCH')
            original=json.loads(line)
            if any(original[k]!=c[k] for k in ('fixture_id','home','away','kickoff','bookmaker')):
                raise StopPilot('FIXTURE_MAPPING_MISMATCH')
            if c['request']!={'endpoint':'/v4/historical-odds','params':{'fixtureId':c['fixture_id'],'bookmakers':c['bookmaker']}}:
                raise StopPilot('REQUEST_CONTRACT_INVALID')
        for candidate in candidates:
            if candidate['request'] not in manifest['allowed_uncached_requests'] and load_cache(storage.ROOT,candidate) is None:
                raise StopPilot('REQUIRED_EXISTING_CACHE_MISSING_NO_REFETCH')
        report['manifest_sha256']=hashlib.sha256((BASE/'manifest.json').read_bytes()).hexdigest()
        report['verified_fixture_count']=len(candidates)
        baseline=rebuild(context_validator=sep15_17_matchdays_context)
        now=datetime.now(timezone.utc)
        health_check(baseline,baseline,now)
        if not quiet_window(now,allowance_seconds=600):raise StopPilot('PRODUCTION_QUIET_WINDOW_CLOSED')
        production=account(os.getenv('ACCOUNT_PROBE_KEY'),set())
        report['production_before']=production
        books={c['bookmaker'] for c in candidates}
        research=account(os.getenv('HISTORICAL_ODDSPAPI_KEY'),books)
        report['research_before']=research
        verify_isolation(research,production)
        report['credential_isolation']='DISTINCT_ACTIVE_SUBSCRIPTIONS_VERIFIED'
        catalog=json.loads(Path('research/historical_backfill/reports/reviewed_catalog.json').read_text())
        observations=json.loads((BASE/'observations.json').read_text())
        client=HttpClient(os.getenv('HISTORICAL_ODDSPAPI_KEY'))
        root=storage.ROOT.resolve()
        for c in candidates:
            if not c['missing_rounds']:
                report['results'].append(dict(fixture_id=c['fixture_id'],bookmaker=c['bookmaker'],home=c['home'],away=c['away'],kickoff=c['kickoff'],historical_ah_available=None,retrieval_status='NOT_REQUESTED_NO_PREMATCH_TARGET',reconstructed=[],comparisons=[],invalid_rows=0,slots=[dict(slot_utc=s,status='NOT_PREMATCH_SLOT',selected=None) for s in c['all_requested_rounds']]))
                save()
                continue
            payload=load_cache(root,c)
            if payload is not None:
                report['cache_hits']+=1
            else:
                if report['historical_requests']>=15:raise StopPilot('REQUEST_CAP_REACHED')
                if not quiet_window(datetime.now(timezone.utc),allowance_seconds=60):raise StopPilot('PRODUCTION_QUIET_WINDOW_CLOSED')
                health_check(json.loads(Path('research/historical_backfill/data/actions/health.json').read_text()),baseline,datetime.now(timezone.utc))
                before=account(os.getenv('HISTORICAL_ODDSPAPI_KEY'),books)
                time.sleep(5.2)
                report['historical_requests']+=1
                receipt={'fixture_id':c['fixture_id'],'bookmaker':c['bookmaker'],'attempted_at':datetime.now(timezone.utc).isoformat()}
                report['requests'].append(receipt);save()
                status,headers,raw=client('/historical-odds',c['request']['params'])
                receipt['http_status']=status
                if status==429:raise StopPilot('HTTP_429_STOP_NO_RETRY')
                if status not in (200,404):raise StopPilot('HISTORY_HTTP_'+str(status))
                if status==200:
                    if os.getenv('HISTORICAL_ODDSPAPI_KEY').encode() in raw:raise StopPilot('SECRET_IN_RESPONSE_BLOCKED')
                    rawpath=storage.append_bytes(raw,root=root)
                    payload=json.loads(raw)
                    if payload.get('fixtureId')!=c['fixture_id']:raise StopPilot('RESPONSE_FIXTURE_MISMATCH')
                    entry=dict(request=c['request'],origin='LIVE_HTTP_200',raw_sha256=rawpath.stem,fetched_at=datetime.now(timezone.utc).isoformat(),http_status=200,etag=headers.get('ETag'))
                else:
                    payload={'fixtureId':c['fixture_id'],'bookmakers':{}}
                    entry=dict(request=c['request'],origin='LIVE_HTTP_404',fetched_at=datetime.now(timezone.utc).isoformat(),http_status=404)
                index=cache_path(root,c);index.parent.mkdir(parents=True,exist_ok=True)
                with index.open('x') as f:json.dump(entry,f)
                after=account(os.getenv('HISTORICAL_ODDSPAPI_KEY'),books)
                receipt.update(quota_before=before['request_count'],quota_after=after['request_count'])
                if before!=after:raise StopPilot('RESEARCH_QUOTA_OR_SUBSCRIPTION_CHANGED')
            item=evaluate(c,payload,catalog,observations)
            item.update(home=c['home'],away=c['away'],kickoff=c['kickoff'],retrieval_status='CACHE_OR_LIVE_RESPONSE_EVALUATED')
            item['slots']=[]
            for slot in c['all_requested_rounds']:
                if slot not in c['missing_rounds']:
                    pick=dict(slot_utc=slot,status='NOT_PREMATCH_SLOT',selected=None)
                else:
                    rs=[r for r in item['reconstructed'] if r['slot_utc']==slot]
                    pick=select(rs,fixture_id=c['fixture_id'],bookmaker=c['bookmaker'],kickoff=c['kickoff'],slot=slot,catalog=catalog)
                item['slots'].append(pick)
            report['results'].append(item);save()
            print(json.dumps({'completed':len(report['results']),'batch':BATCH,'fixture_id':c['fixture_id'],'historical_requests':report['historical_requests'],'cache_hits':report['cache_hits']}),flush=True)
            if item['invalid_rows']:raise StopPilot('QUOTE_QUALITY_ANOMALY')
        report['status']='COMPLETED'
    except (StopPilot,ValueError,KeyError,TypeError,OSError) as exc:
        report['errors'].append(str(exc) if isinstance(exc,StopPilot) else type(exc).__name__)
        report['status']='STOPPED' if report['historical_requests'] else 'BLOCKED'
    finally:
        if production is not None:
            try:
                after=account(os.getenv('ACCOUNT_PROBE_KEY'),set())
                report['production_after']=after
                report['production_quota_delta']=after['request_count']-production['request_count']
                if after!=production:raise StopPilot('PRODUCTION_ACCOUNT_CHANGED')
            except (StopPilot,ValueError,KeyError,TypeError,OSError):
                report['status']='STOPPED';report['errors'].append('PRODUCTION_POSTCHECK_FAILED')
        save()
    counts={}
    for item in report['results']:
        for slot in item['slots']:counts[slot['status']]=counts.get(slot['status'],0)+1
    report['slot_status_counts']=counts
    report['complete_all_requested_slots_fixture_bookmaker_pairs']=sum(all(s['status']=='BALANCED_LINE' for s in i['slots']) for i in report['results'])
    save()
    print(json.dumps({k:v for k,v in report.items() if k not in ('results','requests')},indent=2))
    summary=os.getenv('GITHUB_STEP_SUMMARY')
    if summary:Path(summary).write_text('# Sep15–17 football-day Historical Recovery\n\n```json\n'+json.dumps({k:v for k,v in report.items() if k not in ('results','requests')},indent=2)+'\n```\n')
    return 0 if report['status']=='COMPLETED' else 1

if __name__=='__main__':raise SystemExit(main())
