import json
import urllib.error
from datetime import datetime, timezone, timedelta
from email.message import Message
import pytest
from odds_scanner import provider_request_budget as budget
from odds_scanner import pinnwire_probe as pinn

@pytest.fixture(autouse=True)
def clean_budget(monkeypatch):
    monkeypatch.setattr(budget, '_ACCOUNT', None)
    monkeypatch.setattr(budget, '_SPENT', 0)
    monkeypatch.setattr(budget, '_BLOCKED', False)

def test_exhausted_report_blocks_without_probe(tmp_path):
    (tmp_path/'reports').mkdir()
    (tmp_path/'reports/oddspapi_quota_health.json').write_text(json.dumps({'generated_at':'2026-01-01T00:00:00+00:00','status':'QUOTA_EXHAUSTED','active_subscription':True,'request_limit':250,'request_count':279}))
    with pytest.raises(budget.QuotaBlocked, match='EXTERNALLY_QUOTA_BLOCKED'):
        budget.reserve_request('/fixtures',tmp_path)
    budget.reserve_request('/account',tmp_path)

def test_unknown_fails_closed(tmp_path):
    with pytest.raises(budget.QuotaBlocked): budget.reserve_request('/historical-odds',tmp_path)

def test_budget_reserved_before_each_call(monkeypatch):
    monkeypatch.setattr(budget,'_ACCOUNT',{'active_subscription':True,'request_limit':250,'request_count':249})
    budget.reserve_request('/odds')
    with pytest.raises(budget.QuotaBlocked): budget.reserve_request('/fixtures')

def test_retry_after_never_shortened():
    now=datetime.now(timezone.utc); headers=Message(); headers['Retry-After']='7200'
    exc=urllib.error.HTTPError('https://pinnwire.com',429,'limited',headers,None)
    assert datetime.fromisoformat(pinn._cooldown_until(exc,now)) == now+timedelta(hours=2)

def test_429_not_retried_and_cooldown_persists(tmp_path,monkeypatch):
    monkeypatch.setattr(pinn,'REPORT',tmp_path/'report.json')
    calls=[]
    def fail(*args,**kwargs):
        calls.append(1)
        raise urllib.error.HTTPError('https://pinnwire.com',429,'limited',{},None)
    monkeypatch.setattr(pinn.urllib.request,'urlopen',fail)
    first=pinn.collect(); second=pinn.collect()
    assert len(calls)==1
    assert first['request_attempts']==1 and first['data_source_health']=='RATE_LIMITED'
    assert second['requests_used']==0 and second['status']=='RATE_LIMIT_COOLDOWN'
    assert second['workflow_success'] is True


def test_historical_free_but_blocked_on_exhaustion(monkeypatch):
    monkeypatch.setattr(budget,'_ACCOUNT',{'active_subscription':True,'request_limit':250,'request_count':249})
    for _ in range(4): budget.reserve_request('/historical-odds')
    assert budget._SPENT == 0
    budget.reserve_request('/fixtures')
    with pytest.raises(budget.QuotaBlocked): budget.reserve_request('/historical-odds')


def test_propline_fetch_failure_is_not_valid_empty_scan(tmp_path,monkeypatch):
    from odds_scanner import propline_research_v2 as propline
    monkeypatch.setattr(propline,'fetch',lambda: ([],['provider HTTP 429']))
    report=propline.run(tmp_path)
    assert report['status']=='API_REQUEST_FAILED'
    assert report['data_source_health']=='UNAVAILABLE'
    assert report['strict_snapshots_this_run']==0


def test_propline_true_empty_scan_keeps_honest_available_status(tmp_path,monkeypatch):
    from odds_scanner import propline_research_v2 as propline
    monkeypatch.setattr(propline,'fetch',lambda: ([],[]))
    report=propline.run(tmp_path)
    assert report['status']=='ZERO_USABLE_FIXTURES'
    assert report['data_source_health']=='AVAILABLE'
