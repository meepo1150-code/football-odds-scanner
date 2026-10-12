import json
from datetime import datetime,timezone
from odds_scanner import europe_pinnacle_discovery as collector
from odds_scanner.research_v2_slots import read_ledger
from test_v2_mainline_observer import _catalog,_fixture


def setup(root,monkeypatch,now='2026-10-12T14:00:00+00:00',ids=(17,)):
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return cls.current.astimezone(tz) if tz else cls.current
    Clock.current=datetime.fromisoformat(now)
    monkeypatch.setattr(collector,'datetime',Clock)
    monkeypatch.setenv(collector.ENV_KEY,'offline-test-key')
    monkeypatch.setenv('RESEARCH_V2_FORCE_RUN','false')
    monkeypatch.delenv('RESEARCH_V2_FORCE_TARGET_AT',raising=False)
    monkeypatch.setattr(collector,'summarize_account',lambda _: {'request_remaining':200})
    for path,data in [(collector.TARGET_PATH,{'tournaments':[{'tournament_id':i} for i in ids]}),(collector.CATALOG_PATH,_catalog())]:
        p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data))
    f=_fixture();f['startTime']='2026-10-12T15:00:00Z'
    f['bookmakerOdds']={'pinnacle':f['bookmakerOdds']['bet365']}
    return Clock,f


def test_real_response_time_is_preserved_not_request_start(tmp_path,monkeypatch):
    clock,f=setup(tmp_path,monkeypatch)
    def get(path,*args):
        if path=='/account':return {}
        clock.current=datetime.fromisoformat('2026-10-12T14:02:00+00:00');return [f]
    monkeypatch.setattr(collector,'_get',get)
    r=collector.run(tmp_path);s=json.loads((tmp_path/collector.SNAPSHOT_PATH).read_text())
    assert s['observed_at']=='2026-10-12T14:02:00+00:00'
    assert r['actual_observed_at']=='2026-10-12T21:02:00+07:00'
    assert r['collection_started_at']=='2026-10-12T14:00:00+00:00'


def test_response_after_kickoff_cannot_be_persisted_as_prematch(tmp_path,monkeypatch):
    clock,f=setup(tmp_path,monkeypatch);f['startTime']='2026-10-12T14:01:00Z'
    def get(path,*args):
        if path=='/account':return {}
        clock.current=datetime.fromisoformat('2026-10-12T14:02:00+00:00');return [f]
    monkeypatch.setattr(collector,'_get',get)
    r=collector.run(tmp_path)
    assert r['strict_snapshots_this_run']==0 and r['status']=='NO_VERIFIED_PREMATCH_QUOTES'
    assert not (tmp_path/collector.SNAPSHOT_PATH).read_text()


def test_timeout_in_second_batch_does_not_drop_first_valid_batch(tmp_path,monkeypatch):
    clock,f=setup(tmp_path,monkeypatch,ids=(17,23,8,35,34,37));calls=[]
    monkeypatch.setattr(collector.time,'sleep',lambda _:None)
    def get(path,key,params=None,*args):
        if path=='/account':return {}
        calls.append(params['tournamentIds'])
        if len(calls)==2:
            clock.current=datetime.fromisoformat('2026-10-12T14:02:00+00:00');raise TimeoutError('recorded failure')
        clock.current=datetime.fromisoformat('2026-10-12T14:01:00+00:00')
        f['tournamentId']=int(params['tournamentIds'].split(',')[0]);return [f]
    monkeypatch.setattr(collector,'_get',get)
    r=collector.run(tmp_path)
    assert r['strict_snapshots_this_run']==1 and r['requests_used']==2 and r['errors']
    assert r['coverage_complete'] is False
    assert json.loads((tmp_path/collector.SNAPSHOT_PATH).read_text())['observed_at']=='2026-10-12T14:01:00+00:00'
    assert r['request_completed_at']=='2026-10-12T14:02:00+00:00'


def test_account_delay_expiring_window_makes_no_odds_request(tmp_path,monkeypatch):
    clock,_=setup(tmp_path,monkeypatch,now='2026-10-12T16:29:00+00:00');calls=[]
    def get(path,*args):
        calls.append(path);assert path=='/account'
        clock.current=datetime.fromisoformat('2026-10-12T16:31:00+00:00');return {}
    monkeypatch.setattr(collector,'_get',get)
    r=collector.run(tmp_path)
    assert calls==['/account'] and r['requests_used']==0
    assert r['status']=='RECOVERY_WINDOW_EXPIRED_BEFORE_ODDS'


def test_forced_expired_slot_cannot_bypass_deadline(tmp_path,monkeypatch):
    setup(tmp_path,monkeypatch,now='2026-10-12T16:31:00+00:00')
    monkeypatch.setenv('RESEARCH_V2_FORCE_RUN','true')
    monkeypatch.setenv('RESEARCH_V2_FORCE_TARGET_AT','2026-10-12T21:00:00+07:00')
    def forbidden(*a,**kw):raise AssertionError('expired slot requested provider')
    monkeypatch.setattr(collector,'_get',forbidden)
    r=collector.run(tmp_path);assert r['status']=='MISSED_SLOT' and r['requests_used']==0


def test_unrequested_or_malformed_response_cannot_certify_empty_slot(tmp_path,monkeypatch):
    _,f=setup(tmp_path,monkeypatch);f['tournamentId']=491
    monkeypatch.setattr(collector,'_get',lambda path,*args:{} if path=='/account' else [f])
    r=collector.run(tmp_path)
    assert r['status']=='PROVIDER_RESPONSE_REJECTED' and r['excluded_unrequested_scope_fixtures']==1
    assert read_ledger(tmp_path)[-1]['state']=='FAILED'
    monkeypatch.setattr(collector,'_get',lambda path,*args:{} if path=='/account' else {'error':'recorded malformed response'})
    r=collector.run(tmp_path)
    assert r['status']=='PROVIDER_RESPONSE_REJECTED' and r['invalid_payload_batches']==1
