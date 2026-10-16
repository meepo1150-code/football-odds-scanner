"""Proven isolated pilot transport/account/quiet-window gates; no live collector imports."""
import hashlib
import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from .reconstruct import parse_time

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


def health_check(current, baseline, now, *, account_isolation=None):
    # Only a live-verified distinct-subscription manual runner may retain an
    # already-failing production baseline. Default pilot behavior stays strict.
    isolated = False
    if account_isolation is not None:
        values = [account_isolation.get(k) for k in ('research', 'production')]
        if not all(isinstance(v, str) and len(v) == 64 for v in values) or values[0] == values[1]:
            raise StopPilot('CREDENTIAL_ISOLATION_UNVERIFIED')
        isolated = True
    timestamp=parse_time(current['generated_at'])
    if not 0 <= (now-timestamp).total_seconds() <= 900:
        raise StopPilot('PRODUCTION_HEALTH_STALE')
    state=current.get('status')
    if state not in SEVERITY or (state=='FAIL' and not isolated):raise StopPilot('PRODUCTION_HEALTH_UNSAFE')
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
