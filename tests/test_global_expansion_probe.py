"""Only a bounded, identity-complete matchday probe may use shared request quota."""
import copy
import json
from datetime import datetime,timezone
from pathlib import Path
import pytest
import importlib.util
REPO=Path(__file__).resolve().parents[1]
_spec=importlib.util.spec_from_file_location('staging_expansion_probe',REPO/'data/research/global_expansion_readiness/probe.py')
probe=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(probe)
from odds_scanner.research_quota_checkpoint import ResearchQuotaBlocked
from odds_scanner.v2_mainline_observer import CATALOG_PATH

NOW=datetime(2026,10,15,8,15,tzinfo=timezone.utc)

@pytest.fixture
def ready(tmp_path):
    # Explicit synthetic unit-test identities; never persisted to any repository artifact.
    f=dict(fixture_id='test-fixture',tournament_id='955',kickoff='2026-10-15T13:00:00+00:00',
        provider_status_id=0,mapping_status='PASS',sides=[dict(club_id='SAU-ONE',provider_id='1'),dict(club_id='SAU-TWO',provider_id='2')])
    league=dict(competition_id='SAU-0001',competition_name='Saudi Pro League',competition_identity_verified=True,fixture_details=[f])
    r=dict(schedule_response_complete=True,schedule_observed_at='2026-10-15T08:03:00+00:00',
        counts=dict(returned_fixtures=1,matched_fixtures=1),leagues=[league])
    p=tmp_path/CATALOG_PATH;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('[{}]')
    return r


def harness(tmp_path,ready,*,account=None,payload=None,reservation=None,now=NOW,clock=None):
    calls=[]
    if account is None:account=dict(subscriptions=[dict(is_active=True,request_limit=250,request_count=180,
        sport_ids=[10],bookmakers={'pinnacle':{}})])
    def get(path,key,params=None,timeout=None):
        calls.append(path)
        if path=='/account':return account
        if isinstance(payload,Exception):raise payload
        return payload if payload is not None else []
    reservation=reservation or (lambda root,ids,now,**kw:(ids,{},'unit-test-grant',1))
    result=probe.collect('unit-test-key',tmp_path,now=now,get=get,reservation=reservation,
        audit_report=ready,clock=clock or (lambda:now))
    return result,calls


@pytest.mark.parametrize('field,value,status',[('schedule_response_complete',False,'BLOCKED_NO_COMPLETE_CURRENT_SCHEDULE'),
    ('schedule_observed_at',None,'BLOCKED_NO_COMPLETE_CURRENT_SCHEDULE')])
def test_no_transport_before_actual_fixture_evidence(tmp_path,ready,field,value,status):
    ready[field]=value;r,calls=harness(tmp_path,ready)
    assert r['status']==status and calls==[]


def test_missing_matchday_identity_blocks_all_price_requests(tmp_path,ready):
    ready['counts']['matched_fixtures']=0;r,calls=harness(tmp_path,ready)
    assert r['status']=='BLOCKED_UNMATCHED_RETURNED_FIXTURES' and not calls


@pytest.mark.parametrize('now,status',[(datetime(2026,10,15,7,tzinfo=timezone.utc),'WAITING_1500_SCAN'),
    (datetime(2026,10,16,8,tzinfo=timezone.utc),'SKIPPED_OUTSIDE_AUTHORIZED_DAY'),
    (datetime(2026,10,15,10,tzinfo=timezone.utc),'SKIPPED_PROBE_WINDOW_EXPIRED')])
def test_clock_window_is_fail_closed(tmp_path,ready,now,status):
    r,calls=harness(tmp_path,ready,now=now);assert r['status']==status and calls==[]


def test_more_than_one_batch_never_partially_probes(tmp_path,ready):
    ready['leagues']=[copy.deepcopy(ready['leagues'][0]) for _ in range(6)]
    ready['counts']=dict(returned_fixtures=6,matched_fixtures=6)
    for n,l in enumerate(ready['leagues']):
        l['fixture_details'][0]['tournament_id']=str(900+n);l['fixture_details'][0]['fixture_id']=str(n)
    r,calls=harness(tmp_path,ready);assert r['status']=='BLOCKED_ONE_REQUEST_BATCH_LIMIT' and not calls


def test_prior_attempt_blocks_duplicate_request(tmp_path,ready):
    p=tmp_path/probe.OUT;p.parent.mkdir(parents=True);p.write_text(json.dumps(dict(football_day=probe.DAY,provider_requests_attempted=1)))
    r,calls=harness(tmp_path,ready);assert r['status']=='SKIPPED_ALREADY_PROBED' and calls==[]


def test_exhausted_account_never_reaches_reservation(tmp_path,ready):
    account=dict(subscriptions=[dict(is_active=True,request_limit=250,request_count=250,sport_ids=[10],bookmakers={'pinnacle':{}})])
    r,calls=harness(tmp_path,ready,account=account)
    assert r['status']=='BLOCKED_QUOTA_OR_PROVIDER_ENTITLEMENT' and calls==['/account']


def test_unavailable_durable_quota_never_reaches_prices(tmp_path,ready):
    def denied(*a,**k):raise ResearchQuotaBlocked('test')
    r,calls=harness(tmp_path,ready,reservation=denied)
    assert r['status']=='SKIPPED_QUOTA_DURABLE_RESERVATION' and calls==['/account']


def test_api_failure_is_counted_without_retry_or_secret_log(tmp_path,ready):
    r,calls=harness(tmp_path,ready,payload=RuntimeError('apiKey=DO_NOT_LOG'))
    assert calls==['/account','/odds-by-tournaments']
    assert r['provider_requests_attempted']==1 and r['status']=='API_REQUEST_FAILED'
    assert 'DO_NOT_LOG' not in json.dumps(r)


def test_empty_prices_are_not_reported_as_pass(tmp_path,ready):
    r,calls=harness(tmp_path,ready)
    assert r['status']=='NO_VALID_PRICE_COVERAGE' and r['valid_price_fixtures']==0
    assert r['fixture_diagnostics'][0]['reason']=='NO_ODDS_FIXTURE_RETURNED'
    assert calls==['/account','/odds-by-tournaments']


def test_price_fixture_must_keep_both_participant_ids(tmp_path,ready):
    f=dict(fixtureId='test-fixture',tournamentId=955,participant1Id=999,participant2Id=2)
    r,_=harness(tmp_path,ready,payload=[f])
    assert r['fixture_diagnostics'][0]['reason']=='PRICE_FIXTURE_IDENTITY_MISMATCH'


def test_strict_price_parser_is_used_and_never_promotes(tmp_path,ready,monkeypatch):
    seen=[]
    def parser(f,catalog,**kwargs):
        seen.append(kwargs);return dict(fixture_id=f['fixtureId'],ah={'home_line':-0.5}), 'OK'
    monkeypatch.setattr(probe,'extract_mainline_snapshot',parser)
    f=dict(fixtureId='test-fixture',tournamentId=955,participant1Id=1,participant2Id=2)
    r,calls=harness(tmp_path,ready,payload=[f])
    assert r['status']=='PASS_RETURNED_MATCHDAY_PRICES' and r['valid_price_fixtures']==1
    assert seen[0]['bookmaker']=='pinnacle'
    assert r['activation_allowed'] is False and r['shadow_snapshots'][0]['promotion_eligible'] is False
    assert r['shadow_snapshots'][0]['home_club_id']=='SAU-ONE'
    assert r['identity_counts']['returned_fixtures']==1


def test_retired_global_expansion_probe_cannot_run_or_mutate_snapshots():
    p = Path(__file__).resolve().parents[1] / '.github/workflows/global-expansion-matchday-probe.yml'
    assert not p.exists()


def test_local_quota_skip_is_not_api_failure(tmp_path,ready):
    from odds_scanner.provider_request_budget import QuotaBlocked
    r,calls=harness(tmp_path,ready,payload=QuotaBlocked('not sent'))
    assert r['status']=='SKIPPED_QUOTA_PROVIDER_RESERVE' and r['provider_requests_attempted']==0
    assert calls==['/account','/odds-by-tournaments']
