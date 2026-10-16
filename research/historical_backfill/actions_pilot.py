"""Manual environment entrypoint. No scheduler, production writes, retries or secret output."""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from research.historical_backfill.isolated_runner import HttpClient, StopPilot, summarize_account, digest, run

BRANCH='refs/heads/research/historical-backfill-isolated-20261015'
BASE=Path('research/historical_backfill')
OUT=BASE/'data/actions'


def context_gate(env):
    if env.get('GITHUB_REF')!=BRANCH or env.get('GITHUB_EVENT_NAME')!='workflow_dispatch':
        raise StopPilot('MANUAL_RESEARCH_BRANCH_ONLY')
    if env.get('PILOT_ENVIRONMENT')!='historical-research':raise StopPilot('ENVIRONMENT_REQUIRED')


def probe(key,books):
    if not key:raise StopPilot('CREDENTIAL_MISSING')
    # Pace across workflow steps and credentials; the endpoint has a 1000ms cooldown.
    time.sleep(1.2)
    status,_,body=HttpClient(key)('/account',{})
    if status!=200:raise StopPilot('ACCOUNT_HTTP_'+str(status))
    payload=json.loads(body)
    if not payload.get('current_subscription_id'):raise StopPilot('SUBSCRIPTION_ID_MISSING')
    # Raw account response includes the secret and is never written or logged.
    return summarize_account(payload,books,datetime.now(timezone.utc))


def verify_isolation(research,production):
    if research['subscription_fingerprint']==production['subscription_fingerprint']:
        raise StopPilot('SHARED_PRODUCTION_SUBSCRIPTION')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['production-before','pilot','production-after'])
    parser.add_argument('--expand',action='store_true')
    a=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    report={'status':'BLOCKED','mode':a.mode,'account_requests':0,'historical_requests':0,'errors':[]}
    try:
        context_gate(os.environ)
        if a.mode.startswith('production-'):
            report['account_requests']=1
            summary=probe(os.getenv('ACCOUNT_PROBE_KEY'),set())
            # This credential can only reach /account; never passed to the historical runner.
            report['account']=summary
            if a.mode=='production-after':
                before=json.loads((OUT/'production-before.json').read_text())
                if before['status']!='PASS':raise StopPilot('PRODUCTION_BASELINE_MISSING')
                old=before['account']
                if old['subscription_fingerprint']!=summary['subscription_fingerprint']:
                    raise StopPilot('PRODUCTION_SUBSCRIPTION_CHANGED')
                report['production_request_delta']=summary['request_count']-old['request_count']
                if report['production_request_delta']!=0:raise StopPilot('PRODUCTION_QUOTA_CHANGED_REQUIRES_REVIEW')
            report['status']='PASS'
        else:
            manifest=json.loads((BASE/'reports/multiday_manifest.json').read_text())
            production=json.loads((OUT/'production-before.json').read_text())
            if a.expand:
                from research.historical_backfill.revalidate import authorize_expansion, require_cached_prefix
                from research.historical_backfill import storage
                authorize_expansion(json.loads((BASE/'data/quality/calibration.json').read_text()),manifest,
                    json.loads((BASE/'reports/reviewed_catalog.json').read_text()),storage.ROOT)
                if os.getenv('PILOT_ALLOW_EXPANSION')!='true':raise StopPilot('EXPANSION_NOT_REQUESTED')
                report['cached_prefix_verified']=require_cached_prefix(manifest,
                    int(os.getenv('PILOT_MIN_CACHED_FIXTURES','10')),storage.ROOT)
            if production['status']!='PASS':raise StopPilot('PRODUCTION_BASELINE_MISSING')
            books={c['bookmaker'] for c in (manifest['candidates'] if a.expand else manifest['candidates'][:10])}
            report['account_requests']=1
            research=probe(os.getenv('HISTORICAL_ODDSPAPI_KEY'),books)
            report['research_account']=research
            verify_isolation(research,production['account'])
            report['credential_isolation']='DISTINCT_ACTIVE_SUBSCRIPTION_IDS_VERIFIED'
            report['historical_access']='DOCUMENTED_FREE_ENDPOINT_PENDING_LIVE_RESPONSE'
            catalog=json.loads((BASE/'reports/reviewed_catalog.json').read_text())
            report['reviewed_ah_markets']=len(catalog)
            gate=json.loads((BASE/'reports/isolated_gate_pending.json').read_text())
            gate.update(credential_scope='DEDICATED_SUBSCRIPTION_VERIFIED',
                credential_evidence='Live unmetered account checks: distinct active subscription fingerprints',
                catalog_sha256=digest(catalog),manifest_sha256=digest(manifest))
            # main is checked out separately read-only by Actions; never change production state.
            health=lambda:json.loads((OUT/'health.json').read_text())
            observations=[]
            for name in ('europe_pinnacle_research_v2_snapshots.jsonl','v2_mainline_snapshots.jsonl'):
                p=Path('data/normalized')/name
                if p.exists():observations.extend(json.loads(s) for s in p.read_text().splitlines() if s.strip())
            result=run(manifest,catalog,observations,gate,health,
                       key=os.getenv('HISTORICAL_ODDSPAPI_KEY'),allow_expansion=a.expand)
            report['pilot']=result
            if any(x.get('historical_ah_available') for x in result['results']):
                report['historical_access']='LIVE_RESPONSE_OR_IMMUTABLE_LIVE_CACHE_VERIFIED'
            from research.historical_backfill.quality_coverage import coverage
            report['balanced_coverage']=coverage(manifest,result,catalog)
            report['account_requests']+=result['actual_account_requests']
            report['historical_requests']=result['actual_historical_requests']
            report['status']=result['status']
            report['errors']=result['errors']
            report['coverage']={'fixtures_evaluated':len(result['results']),
                'fixtures_with_ah':sum(x['historical_ah_available'] for x in result['results']),
                'complete_fixture_slots':sum(x['complete_slots'] for x in result['results']),
                'recovered_line_snapshots':sum(r['status']=='COMPLETE' for x in result['results'] for r in x['reconstructed'])}
    except (StopPilot,ValueError,KeyError,TypeError,OSError) as exc:
        report['errors'].append(str(exc) if isinstance(exc,StopPilot) else type(exc).__name__)
    report['generated_at']=datetime.now(timezone.utc).isoformat()
    text=json.dumps(report,indent=2,allow_nan=False)
    # Defense in depth: no secret may be persisted, even from an unexpected provider response.
    for name in ('HISTORICAL_ODDSPAPI_KEY','ACCOUNT_PROBE_KEY'):
        value=os.getenv(name)
        if value and value in text:raise SystemExit('SECRET_OUTPUT_BLOCKED')
    (OUT/(a.mode+'.json')).write_text(text+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('pilot','research_account','account','balanced_coverage')},indent=2))
    summary=os.getenv('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a') as f:f.write('### Historical pilot: '+a.mode+'\n\nStatus: **'+report['status']+'**\n\n'+', '.join(report['errors'])+'\n')
    return 0 if report['status'] in ('PASS','COMPLETED','CALIBRATION_FAILED_NO_EXPANSION') else 1

if __name__=='__main__':sys.exit(main())
