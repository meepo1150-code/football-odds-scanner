"""Manual, bounded, secret-isolated pilot. Never imported by production workflows."""
import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from research.historical_backfill import storage
from research.historical_backfill.normalizer import normalize
from research.historical_backfill.comparison import reconstruct_candidate, compare_observation
from research.historical_backfill.reconstruct import parse_time,finite

BKK=ZoneInfo('Asia/Bangkok')
SEVERITY={'PASS':0,'WARNING':1,'FAIL':2}


class StopPilot(Exception):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def quiet_window(now, allowance_seconds=45):
    """Protect production targets plus the entire existing 150-minute recovery window."""
    local=now.astimezone(BKK)
    for delta in (-1,0,1):
        day=local.date()+timedelta(days=delta)
        for hour in (0,15,18,21):
            target=datetime(day.year,day.month,day.day,hour,tzinfo=BKK)
            if local <= target+timedelta(minutes=150) and local+timedelta(seconds=allowance_seconds) >= target-timedelta(minutes=15):
                return False
    return True


def health_check(current, baseline, now):
    timestamp=parse_time(current['generated_at'])
    if not 0 <= (now-timestamp).total_seconds() <= 900:
        raise StopPilot('PRODUCTION_HEALTH_STALE')
    state=current.get('status')
    if state not in SEVERITY or state=='FAIL':raise StopPilot('PRODUCTION_HEALTH_UNSAFE')
    if SEVERITY[state]>SEVERITY.get(baseline.get('status'),-1):raise StopPilot('PRODUCTION_HEALTH_DEGRADED')
    if set(current.get('issues',[]))-set(baseline.get('issues',[])):raise StopPilot('NEW_PRODUCTION_HEALTH_ISSUE')


def summarize_account(payload,bookmakers,now):
    # Do not persist account payload: /account includes api_key and identifying fields.
    current=payload.get('current_subscription_id')
    subs=[s for s in payload.get('subscriptions',[]) if s.get('is_active') is True
          and (not current or s.get('subscription_id')==current)]
    if len(subs)!=1:raise StopPilot('ACCOUNT_SUBSCRIPTION_AMBIGUOUS')
    s=subs[0]
    if s.get('valid_until') and parse_time(s['valid_until'])<=now:raise StopPilot('ACCOUNT_EXPIRED')
    if s.get('valid_from') and parse_time(s['valid_from'])>now:raise StopPilot('ACCOUNT_NOT_STARTED')
    limit,count=s.get('request_limit'),s.get('request_count')
    if type(limit) is not int or type(count) is not int or not 0 <= count < limit:
        raise StopPilot('ACCOUNT_QUOTA_UNAVAILABLE_OR_EXHAUSTED')
    if 10 not in s.get('sport_ids',[]):raise StopPilot('SOCCER_NOT_ENTITLED')
    if not set(bookmakers).issubset(set(s.get('bookmakers',{}))):raise StopPilot('BOOKMAKER_NOT_ENTITLED')
    return dict(request_limit=limit,request_count=count,
                subscription_fingerprint=digest(s.get('subscription_id')),
                entitled_bookmakers=sorted(bookmakers),rate_limit=s.get('rate_limit'))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None


class HttpClient:
    def __init__(self,key):
        self.key=key
        self.opener=urllib.request.build_opener(NoRedirect())

    def __call__(self,path,params):
        if path not in ('/account','/historical-odds'):raise StopPilot('ENDPOINT_NOT_ALLOWED')
        if 'apiKey' in params:raise StopPilot('KEY_IN_REQUEST_MANIFEST')
        url='https://api.oddspapi.io/v4'+path+'?'+urllib.parse.urlencode({**params,'apiKey':self.key})
        try:
            with self.opener.open(url,timeout=45) as response:
                body=response.read(64*1024*1024+1)
                if len(body)>64*1024*1024:raise StopPilot('RESPONSE_TOO_LARGE')
                return response.status,dict(response.headers),body
        except urllib.error.HTTPError as exc:
            return exc.code,dict(exc.headers),b''
        except (urllib.error.URLError,TimeoutError,OSError):
            # Never stringify an exception: it can contain the key-bearing URL.
            raise StopPilot('TRANSPORT_ERROR') from None


def cache_path(root,candidate):
    return root/'cache'/(digest(candidate['request'])+'.json')


def load_cache(root,candidate):
    index=cache_path(root,candidate)
    if not index.exists():return None
    if index.is_symlink() or index.resolve().parent!=root/'cache':
        raise StopPilot('CACHE_INDEX_PATH_INVALID')
    receipt=json.loads(index.read_text())
    if receipt.get('request')!=candidate['request'] or receipt.get('origin') not in {'LIVE_HTTP_200','LIVE_HTTP_404'}:
        raise StopPilot('CACHE_PROVENANCE_INVALID')
    if receipt['origin']=='LIVE_HTTP_404':
        return dict(fixtureId=candidate['fixture_id'],bookmakers={},cached_http_status=404)
    if not isinstance(receipt.get('raw_sha256'),str) or not re.fullmatch('[0-9a-f]{64}',receipt['raw_sha256']):
        raise StopPilot('CACHE_HASH_INVALID')
    path=root/'raw'/(receipt['raw_sha256']+'.json')
    if path.is_symlink() or path.resolve().parent!=root/'raw':raise StopPilot('CACHE_RAW_PATH_INVALID')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=receipt['raw_sha256']:raise StopPilot('CACHE_HASH_MISMATCH')
    return json.loads(raw)


def evaluate(candidate,payload,catalog,observations):
    markets=normalize(payload,candidate,catalog,active_semantics_verified=True)
    rows=reconstruct_candidate(candidate,markets,state_semantics_verified=True)
    comparisons=[compare_observation(o,markets,state_semantics_verified=True) for o in observations
                 if o.get('fixture_id')==candidate['fixture_id'] and o.get('bookmaker')==candidate['bookmaker']
                 and parse_time(o['observed_at'])<parse_time(o['kickoff'])]
    paired=sum(any(x['status']=='COMPLETE' for x in c.get('comparisons',[])) for c in comparisons)
    invalid=sum(r['status'] in {'INVALID_TIMESTAMP','INVALID_PRICE','AMBIGUOUS_LATEST_STATE'} for r in rows)
    return dict(fixture_id=candidate['fixture_id'],bookmaker=candidate['bookmaker'],
                historical_ah_available=bool(markets),reconstructed=rows,
                complete_slots=len({r['slot_utc'] for r in rows if r['status']=='COMPLETE'}),
                comparisons=comparisons,paired_observations=paired,invalid_rows=invalid)


def calibration_passed(items):
    return (len(items)==10 and len({x['fixture_id'] for x in items})==10
            and sum(x['historical_ah_available'] for x in items)>=8
            and sum(x['paired_observations']>0 for x in items)>=5
            and sum(x['complete_slots']>0 for x in items)>=5
            and sum(x['invalid_rows'] for x in items)==0)


def run(manifest,catalog,observations,gate,health_reader,*,key=None,allow_expansion=False,
        client=None,clock=lambda:datetime.now(timezone.utc),sleeper=time.sleep,root=None):
    """Credentials, explicit evidence, fresh health and stage quality all fail closed."""
    report=dict(status='BLOCKED',actual_historical_requests=0,actual_account_requests=0,
                cache_hits=0,errors=[],results=[],calibration_passed=False,
                quota_comparisons=[],production_health_checks=0,expansion_started=False,
                execution_origin='LIVE_CLIENT' if client is None else 'TEST_INJECTED_CLIENT')
    candidates=manifest.get('candidates',[])
    try:
        if not 10 <= len(candidates) <= 100 or len({c['fixture_id'] for c in candidates})!=len(candidates):
            raise StopPilot('INVALID_MANIFEST')
        if [c.get('phase') for c in candidates[:10]]!=['CALIBRATION']*10:
            raise StopPilot('CALIBRATION_ORDER_INVALID')
        for c in candidates:
            if c.get('request')!={'endpoint':'/v4/historical-odds','params':{
                    'fixtureId':c['fixture_id'],'bookmakers':c['bookmaker']}}:
                raise StopPilot('REQUEST_CONTRACT_INVALID')
        if not key:raise StopPilot('ISOLATED_CREDENTIAL_NOT_CONFIGURED')
        if gate.get('credential_scope')!='DEDICATED_SUBSCRIPTION_VERIFIED' or not gate.get('credential_evidence'):
            raise StopPilot('CREDENTIAL_ISOLATION_UNVERIFIED')
        if gate.get('semantics_mode')!='PROVIDER_REPORTED_SNAPSHOT' or not gate.get('semantics_evidence'):
            raise StopPilot('SEMANTICS_UNVERIFIED')
        if gate.get('catalog_sha256')!=digest(catalog) or not catalog:
            raise StopPilot('REVIEWED_CATALOG_REQUIRED')
        for meta in catalog:
            if (meta.get('review_status')!='VERIFIED_FULL_MATCH_AH_HOME_LINE'
                or not finite(meta.get('home_line'))
                or abs(meta['home_line']*4-round(meta['home_line']*4))>1e-8
                or not all(meta.get(k) is not None for k in ('market_id','home_outcome_id','away_outcome_id','evidence'))):
                raise StopPilot('CATALOG_REVIEW_INCOMPLETE')
        if gate.get('manifest_sha256')!=digest(manifest):raise StopPilot('MANIFEST_NOT_REVIEWED')
        now=clock();baseline=health_reader();health_check(baseline,baseline,now)
        root=(storage.ROOT if root is None else root).resolve()
        if root!=storage.ROOT and storage.ROOT not in root.parents:raise StopPilot('STORAGE_OUTSIDE_ISOLATED_ROOT')
        client=client or HttpClient(key)
        books={c['bookmaker'] for c in candidates[:10]}

        def request(path,params):
            sleeper(5.2 if path=='/historical-odds' else 1.1)
            now=clock()
            if not quiet_window(now):raise StopPilot('PRODUCTION_QUIET_WINDOW_CLOSED')
            health_check(health_reader(),baseline,now);report['production_health_checks']+=1
            field='actual_account_requests' if path=='/account' else 'actual_historical_requests'
            report[field]+=1
            status,headers,raw=client(path,params)
            if status==429:raise StopPilot('HTTP_429_STOP_NO_RETRY')
            if status not in (200,404):raise StopPilot('HTTP_'+str(status))
            if status==404 and path=='/account':raise StopPilot('ACCOUNT_HTTP_404')
            return status,headers,raw

        def account():
            _,_,raw=request('/account',{})
            return summarize_account(json.loads(raw),books,clock())

        account() # Fresh isolated account/entitlement preflight, never a production ledger.
        ceiling=len(candidates) if allow_expansion else 10
        for i,candidate in enumerate(candidates[:ceiling]):
            if i==10:
                report['calibration_passed']=calibration_passed(report['results'])
                if not report['calibration_passed']:raise StopPilot('CALIBRATION_QUALITY_GATE_FAILED')
                report['expansion_started']=True
            books={candidate['bookmaker']}
            payload=load_cache(root,candidate)
            if payload is not None:report['cache_hits']+=1
            else:
                before=account()
                status,headers,raw=request('/historical-odds',candidate['request']['params'])
                # Preserve every returned historical body even if later quota/QA checks stop.
                raw_path=storage.append_bytes(raw,root=root) if status==200 else None
                after=account()
                report['quota_comparisons'].append(dict(fixture_id=candidate['fixture_id'],before=before,after=after))
                if (before['request_count'],before['request_limit'],before['subscription_fingerprint']) != (after['request_count'],after['request_limit'],after['subscription_fingerprint']):
                    raise StopPilot('QUOTA_OR_SUBSCRIPTION_ANOMALY')
                if status==404:
                    index=cache_path(root,candidate);index.parent.mkdir(parents=True,exist_ok=True)
                    with index.open('x') as stream:
                        json.dump(dict(request=candidate['request'],origin='LIVE_HTTP_404',
                            http_status=404,fetched_at=clock().isoformat()),stream,sort_keys=True)
                    report['results'].append(dict(fixture_id=candidate['fixture_id'],bookmaker=candidate['bookmaker'],
                        historical_ah_available=False,reconstructed=[],complete_slots=0,comparisons=[],paired_observations=0,invalid_rows=0,http_status=404))
                    continue
                payload=json.loads(raw)
                if payload.get('fixtureId')!=candidate['fixture_id']:raise StopPilot('RESPONSE_FIXTURE_MISMATCH')
                receipt=dict(request=candidate['request'],origin='LIVE_HTTP_200',raw_sha256=raw_path.stem,
                             fetched_at=clock().isoformat(),etag=headers.get('ETag'),http_status=200)
                index=cache_path(root,candidate);index.parent.mkdir(parents=True,exist_ok=True)
                with index.open('x') as stream:json.dump(receipt,stream,sort_keys=True)
            item=evaluate(candidate,payload,catalog,observations);report['results'].append(item)
            if item['invalid_rows']:raise StopPilot('QUALITY_ANOMALY')
            if (i+1)%10==0:
                health_check(health_reader(),baseline,clock());report['production_health_checks']+=1
        report['calibration_passed']=calibration_passed(report['results'][:10])
        report['status']='COMPLETED' if report['calibration_passed'] else 'CALIBRATION_FAILED_NO_EXPANSION'
    except (StopPilot,ValueError,KeyError,TypeError,OSError) as exc:
        # Only controlled StopPilot codes may be persisted; other exception text may leak secrets.
        report['errors'].append(str(exc) if isinstance(exc,StopPilot) else type(exc).__name__)
        report['status']='STOPPED' if report['actual_historical_requests'] else 'BLOCKED'
    report.update(actual_total_requests=report['actual_historical_requests']+report['actual_account_requests'],
                  live_coverage_measured=bool(report['actual_historical_requests']) and report['execution_origin']=='LIVE_CLIENT',
                  manifest_sha256=digest(manifest),generated_at=clock().isoformat())
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--manifest',required=True);p.add_argument('--catalog',required=True)
    p.add_argument('--gate',required=True);p.add_argument('--health',required=True)
    p.add_argument('--observations',nargs='+',required=True);p.add_argument('--expand',action='store_true')
    a=p.parse_args();read=lambda path:json.loads(Path(path).read_text())
    observations=[json.loads(s) for path in a.observations for s in Path(path).read_text().splitlines() if s.strip()]
    report=run(read(a.manifest),read(a.catalog),observations,read(a.gate),lambda:read(a.health),
               key=os.getenv('HISTORICAL_ODDSPAPI_KEY'),allow_expansion=a.expand)
    dest=storage.ROOT/'runs'/(uuid.uuid4().hex+'.json');dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('x') as stream:json.dump(report,stream,indent=2)
    print(json.dumps({k:v for k,v in report.items() if k not in ('results','quota_comparisons')},indent=2))


if __name__=='__main__':main()
