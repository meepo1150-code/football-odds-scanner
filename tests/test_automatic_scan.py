import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import pytest
from odds_scanner import automatic_scan as auto
from odds_scanner import automatic_scan_manifest as manifest
from odds_scanner import automatic_scan_checkpoint as checkpoint
from odds_scanner import automatic_scan_collector as clone
from odds_scanner import europe_pinnacle_discovery as manual
from odds_scanner.automatic_scan_budget import allocation
from odds_scanner.research_request_budget import RESERVATIONS
from odds_scanner import master_schedule_plan as planner
from test_collector_observation_contract import setup

@pytest.mark.parametrize('stamp,day,hour',[
 ('2026-10-16T08:00:00Z','2026-10-16','15'),
 ('2026-10-16T11:00:00Z','2026-10-16','18'),
 ('2026-10-16T14:00:00Z','2026-10-16','21'),
 ('2026-10-16T17:00:00Z','2026-10-16','00'),
 ('2027-01-01T17:00:00Z','2027-01-01','00'),
 ('2026-12-31T17:00:00Z','2026-12-31','00'),
])
def test_slot_boundaries(stamp,day,hour):
    r=auto.slot_at(datetime.fromisoformat(stamp.replace('Z','+00:00')))
    assert r['slot_id']==f'{day}/{hour}00' and r['lag_minutes']==0


def test_manual_source_immutable_and_extractors_identical():
    paths={'.github/workflows/manual-current-day-odds.yml':'446366d65db1d31fd8a78d7a47a5350877f66e5c'}
    import subprocess
    for p,sha in paths.items():
        assert subprocess.check_output(['git','hash-object',p],text=True).strip()==sha
    assert clone.extract_mainline_snapshot is manual.extract_mainline_snapshot
    assert clone.mainline_shape is manual.mainline_shape
    assert clone._get is manual._get
    baseline_sha256 = {'europe_pinnacle_discovery.py': '1d8a4ac3f4c4671a224dc7c15bab32636167581d603b073bf47ca1ebc753b70b', 'research_request_budget.py': '493f37f4fdcec36c0f8917b8d440d4c0bfc9e4fecc07150be533a101eddd59e5', 'research_quota_checkpoint.py': '01e004977fd7204913d6b336388876974d5852df28b790d7991ddd53193940d5', 'oddspapi_provider.py': 'aa427cbd312b8cafe546ed110a0bb9411bcf1e83fe9e2364826160b56adf674b', 'provider_request_budget.py': '83dd84c1c0ff76e973863109bbe528f7f69726b02737a11486c05d0c982f841e'}
    for name, expected in baseline_sha256.items():
        assert hashlib.sha256(Path("src/odds_scanner",name).read_bytes()).hexdigest() == expected


def test_unlimited_internal_research_budget_but_guard_unchanged(tmp_path):
    p=tmp_path/'data/normalized/research_v2_slot_ledger.jsonl';p.parent.mkdir(parents=True)
    p.write_text(json.dumps(dict(finalized_at='2026-10-16T08:00:00Z',requests_used=200)))
    ids=list(range(92));chosen,b=allocation(p,ids,datetime(2026,10,16,11,tzinfo=timezone.utc))
    assert chosen==ids and b['research_monthly_limit'] is None and b['future_utc_requests_reserved']==0


def test_dry_run_and_missing_manifest_no_transport(tmp_path,monkeypatch):
    monkeypatch.setattr(clone,'run',lambda *a:pytest.fail('no collector permitted'))
    now=datetime(2026,10,16,11,3,tzinfo=timezone.utc)
    assert auto.run(tmp_path,dry_run=True,now=now)['requests_used']==0
    r=auto.run(tmp_path,now=now)
    assert r['scan_health']=='FAIL' and r['requests_used']==0
    assert not (tmp_path/manifest.MANIFESTS).exists()


def test_expired_no_price_substitution(tmp_path,monkeypatch):
    monkeypatch.setattr(clone,'run',lambda *a:pytest.fail('late collector forbidden'))
    r=auto.run(tmp_path,now=datetime(2026,10,16,8,31,tzinfo=timezone.utc))
    assert r['status']=='DELAYED' and r['actual_scan_time'] is None


def test_completed_slot_no_requests(tmp_path,monkeypatch):
    p=tmp_path/auto.LEDGER;p.parent.mkdir(parents=True)
    p.write_text(json.dumps(dict(slot_id='2026-10-16/1800',complete=True))+'\n')
    monkeypatch.setattr(clone,'run',lambda *a:pytest.fail('duplicate'))
    assert auto.run(tmp_path,now=datetime(2026,10,16,11,5,tzinfo=timezone.utc))['status']=='ALREADY_COMPLETE'


def test_cancelled_grant_blocks_duplicate(tmp_path,monkeypatch):
    monkeypatch.delenv('RESEARCH_QUOTA_DURABLE',raising=False)
    now=datetime(2026,10,16,8,1,tzinfo=timezone.utc)
    checkpoint.reserve(tmp_path,[17],now)
    with pytest.raises(checkpoint.ResearchQuotaBlocked,match='unconfirmed'):
        checkpoint.reserve(tmp_path,[17],now)


def test_durable_checkpoint_failure_no_grant(tmp_path,monkeypatch):
    monkeypatch.setenv('RESEARCH_QUOTA_DURABLE','true')
    monkeypatch.setattr(checkpoint,'_refresh',lambda r:(_ for _ in ()).throw(OSError()))
    with pytest.raises(checkpoint.ResearchQuotaBlocked):
        checkpoint.reserve(tmp_path,[17],datetime(2026,10,16,8,tzinfo=timezone.utc))
    assert not (tmp_path/RESERVATIONS).exists()


def configure(root,monkeypatch,now='2026-10-16T08:01:00+00:00'):
    clock,f=setup(root,monkeypatch,now=now)
    monkeypatch.setattr(clone,'datetime',clock)
    monkeypatch.setattr(auto,'datetime',clock)
    monkeypatch.setattr(clone,'summarize_account',lambda _:dict(request_remaining=200))
    monkeypatch.delenv('RESEARCH_QUOTA_DURABLE',raising=False)
    f.update(fixtureId='baseline',startTime='2026-10-16T20:00:00Z',participant1Id=146,participant2Id=147)
    p=root/'data/master/provider_mappings.csv';p.parent.mkdir(parents=True,exist_ok=True);p.write_text('master mode')
    monkeypatch.setattr(planner,'registry',lambda:[dict(tournament_id=17,country='England',tournament_name='Premier League')])
    import odds_scanner.master_mapping as mapping
    monkeypatch.setattr(mapping,'load_mappings',lambda:{('oddspapi','competition','17'):'ENG-0001',('oddspapi','club','146'):'ENG-LFC',('oddspapi','club','147'):'ENG-ARS'})
    return clock,f


def test_preparation_followup_same_ids_midnight_and_duplicate(tmp_path,monkeypatch):
    clock,f=configure(tmp_path,monkeypatch)
    calls=[]
    def get(endpoint,*args):
        calls.append(endpoint)
        return {} if endpoint=='/account' else [f]
    monkeypatch.setattr(clone,'_get',get)
    first=auto.run(tmp_path,now=clock.current)
    assert first['complete'], first
    frozen=(tmp_path/manifest.MANIFESTS).read_bytes()
    assert first['total_fixtures']==1 and first['priced_fixtures']==1
    extra={**f,'fixtureId':'new-unapproved-fixture'}
    for stamp in ('2026-10-16T11:02:00+00:00','2026-10-16T14:02:00+00:00','2026-10-16T17:02:00+00:00'):
        clock.current=datetime.fromisoformat(stamp)
        monkeypatch.setattr(clone,'_get',lambda endpoint,*a:{} if endpoint=='/account' else [f,extra])
        r=auto.run(tmp_path,now=clock.current)
        assert r['complete'] and r['total_fixtures']==1 and r['priced_fixtures']==1,r
        assert auto.run(tmp_path,now=clock.current)['status']=='ALREADY_COMPLETE'
    assert (tmp_path/manifest.MANIFESTS).read_bytes()==frozen
    assert {r['fixture_id'] for r in manifest.rows(tmp_path/manual.SNAPSHOT_PATH)}=={'baseline'}


def test_quota_exhaustion_stops_before_paid_request(tmp_path,monkeypatch):
    clock,f=configure(tmp_path,monkeypatch)
    monkeypatch.setattr(clone,'summarize_account',lambda _:dict(request_remaining=10))
    monkeypatch.setattr(clone,'_get',lambda endpoint,*a:{} if endpoint=='/account' else pytest.fail('paid request'))
    r=auto.run(tmp_path,now=clock.current)
    assert not r['complete'] and r['requests_used']==0
    assert not (tmp_path/manifest.MANIFESTS).exists()


def test_cached_response_preserves_time_and_never_crosses_slot(tmp_path):
    target=datetime(2026,10,16,8,tzinfo=timezone.utc);params={'tournamentIds':'17'}
    observed=target.replace(minute=1)
    planner.retain(tmp_path,'/odds-by-tournaments',params,[{'fixtureId':'x','tournamentId':17}],observed)
    r=manifest.cached_response(tmp_path,'/odds-by-tournaments',params,target,target.replace(minute=8))
    assert r['observed_at']==observed.isoformat()
    assert manifest.cached_response(tmp_path,'/odds-by-tournaments',params,target.replace(hour=11),target.replace(hour=11,minute=1)) is None


def test_invalid_preparation_never_freezes(tmp_path):
    with pytest.raises(ValueError):manifest.freeze(tmp_path,dict(football_day='2026-10-16',coverage_complete=False))
    assert not (tmp_path/manifest.MANIFESTS).exists()


def test_recovery_batch_plan_avoids_repaying_success_after_priorities_change(tmp_path):
    now=datetime(2026,10,16,8,9,tzinfo=timezone.utc);target=now.replace(minute=0)
    planner.retain(tmp_path,'/odds-by-tournaments',dict(tournamentIds='1,2,3,4,5'),[],now.replace(minute=1))
    batches=manifest.request_batches(tmp_path,[6,5,3,2,1],target,now)
    assert batches==[[1,2,3,4,5],[6]]


def test_manifest_publication_conflict_does_not_overwrite(tmp_path):
    from odds_scanner.automatic_scan_persistence import merge
    root=tmp_path/'root';stage=tmp_path/'stage'
    for p,id in ((root,'a'),(stage,'b')):
        f=p/manifest.MANIFESTS;f.parent.mkdir(parents=True)
        f.write_text(json.dumps(dict(football_day='2026-10-16',manifest_id=id))+'\n')
    with pytest.raises(ValueError):merge(root,stage)
    assert manifest.cohort(root,'2026-10-16')['manifest_id']=='a'


def test_failed_auto_run_can_publish_failure_evidence_but_not_forks():
    from types import SimpleNamespace as N
    import yaml
    gate=yaml.safe_load(Path('.github/workflows/pages.yml').read_text())['jobs']['deploy']['if']
    for repo,expected in [('owner/repo',True),('fork/repo',False)]:
        run=N(name='Automatic Four-Round Odds Observation',conclusion='failure',head_branch='main',event='schedule',head_repository=N(full_name=repo))
        github=N(event_name='workflow_run',ref='',repository='owner/repo',event=N(workflow_run=run))
        assert eval(gate.replace('&&',' and ').replace('||',' or '),{'__builtins__':{}},{'github':github}) is expected


def test_publication_preserves_existing_raw_bytes(tmp_path):
    from odds_scanner.automatic_scan_persistence import append_union
    p=tmp_path/'raw';q=tmp_path/'incoming'
    original=b'{"z": 1, "a": "old"}\n'
    p.write_bytes(original);q.write_text('{"a":"old","z":1}\n{"a":"new","z":2}\n')
    append_union(p,q);assert p.read_bytes().startswith(original)
    assert len(p.read_text().splitlines())==2
    before=p.read_bytes();append_union(p,q);assert p.read_bytes()==before


def test_local_failures_are_not_reported_as_api_errors(tmp_path):
    r=auto.run(tmp_path,now=datetime(2026,10,16,11,2,tzinfo=timezone.utc))
    assert r['scan_health']=='FAIL' and r['api_errors']==0 and r['actual_scan_time'] is None


def test_invalid_cached_payload_does_not_prevent_real_retry(tmp_path):
    target=datetime(2026,10,16,8,tzinfo=timezone.utc);params=dict(tournamentIds='17')
    planner.retain(tmp_path,'/odds-by-tournaments',params,{'error':'invalid'},target.replace(minute=1))
    assert manifest.cached_response(tmp_path,'/odds-by-tournaments',params,target,target.replace(minute=2)) is None
    assert manifest.request_batches(tmp_path,[17],target,target.replace(minute=2))==[[17]]


def test_cached_schedule_budget_uses_only_actual_fixture_tournaments(tmp_path, monkeypatch):
    clock, f = configure(tmp_path, monkeypatch)
    monkeypatch.setattr(planner, 'registry', lambda: [dict(tournament_id=n, country='England', tournament_name='Premier League') for n in range(1, 93)])
    monkeypatch.setattr(clone, 'summarize_account', lambda _: dict(request_remaining=11))
    start, end, _ = clone._football_day_bounds(clock.current)
    planner.retain(tmp_path, '/fixtures', dict(sportId=10, **{'from':start.isoformat(), 'to':end.isoformat()}, limit=1000, language='en'), [f], clock.current)
    calls = []
    def get(endpoint, *args):
        calls.append(endpoint)
        return {} if endpoint == '/account' else [f]
    monkeypatch.setattr(clone, '_get', get)
    report = auto.run(tmp_path, now=clock.current)
    assert report['complete'], report
    assert report['requests_used'] == 1
    assert calls == ['/account', '/odds-by-tournaments']
    assert report['research_requests_reserved_this_run'] == 1


def test_auto_provider_exception_does_not_publish_credential_url(tmp_path, monkeypatch):
    clock, f = configure(tmp_path, monkeypatch)
    def get(endpoint, *args):
        if endpoint == '/account': return {}
        if endpoint == '/fixtures': return [f]
        raise OSError('https://api.oddspapi.io/v4/odds?apiKey=DO_NOT_PUBLISH')
    monkeypatch.setattr(clone, '_get', get)
    report = auto.run(tmp_path, now=clock.current)
    assert not report['complete']
    for path in tmp_path.rglob('*'):
        if path.is_file(): assert 'DO_NOT_PUBLISH' not in path.read_text()


def test_malformed_incoming_tail_cannot_partially_append_history(tmp_path):
    from odds_scanner.automatic_scan_persistence import merge, PATHS
    root, stage = tmp_path/'root', tmp_path/'stage'
    first, last = PATHS[0], PATHS[-1]
    target = root/first; target.parent.mkdir(parents=True)
    target.write_text('{"original":true}\n'); before = target.read_bytes()
    incoming = stage/first; incoming.parent.mkdir(parents=True)
    incoming.write_text('{"new":true}\n')
    malformed = stage/last; malformed.parent.mkdir(parents=True, exist_ok=True)
    malformed.write_text('{broken\n')
    with pytest.raises(ValueError): merge(root, stage)
    assert target.read_bytes() == before
