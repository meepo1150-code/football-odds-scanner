import json
from datetime import datetime, timezone
from odds_scanner.automatic_account_audit import run, REPORT


def test_account_only_distinct_subscriptions_never_enable_fallback(tmp_path):
    calls=[]
    def factory(key):
        def get(endpoint, params):
            calls.append(endpoint)
            return 200, {}, json.dumps(dict(current_subscription_id=key, api_key=key,
                subscriptions=[dict(subscription_id=key, is_active=True, request_limit=250,
                                    request_count=25, sport_ids=[10], bookmakers={'pinnacle':{}})])).encode()
        return get
    r=run(tmp_path, env=dict(ODDSPAPI_KEY='secret-one', HISTORICAL_ODDSPAPI_KEY='secret-two'), factory=factory)
    assert calls==['/account','/account']
    assert r['subscription_relationship']=='DISTINCT_SUBSCRIPTIONS'
    assert r['independent_quota']=='UNVERIFIED' and r['fallback_enabled'] is False
    assert r['metered_requests']==0
    assert 'secret-' not in (tmp_path/REPORT).read_text()


def test_missing_secrets_and_url_errors_are_safe(tmp_path):
    def factory(key):
        def get(*a): raise OSError('https://provider/?apiKey=private-key')
        return get
    r=run(tmp_path, env={'ODDSPAPI_KEY':'private-key'}, factory=factory)
    assert r['accounts']['secondary']['status']=='SECRET_NOT_AVAILABLE'
    assert r['subscription_relationship']=='UNVERIFIED'
    assert 'private-key' not in (tmp_path/REPORT).read_text()
