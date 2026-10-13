import json
import subprocess
from datetime import datetime,timezone
from pathlib import Path
import pytest
from odds_scanner.research_quota_checkpoint import reserve, ResearchQuotaBlocked
from odds_scanner.research_request_budget import allocation, RESERVATIONS
from odds_scanner import research_quota_checkpoint as checkpoint

NOW=datetime(2026,10,14,14,tzinfo=timezone.utc)
LEDGER=Path('data/normalized/research_v2_slot_ledger.jsonl')


def test_cancelled_run_and_finalized_receipt_count_once(tmp_path,monkeypatch):
    monkeypatch.delenv('RESEARCH_QUOTA_DURABLE',raising=False)
    ids,budget,rid,count=reserve(tmp_path,list(range(10)),NOW)
    assert count==1
    assert allocation(tmp_path/LEDGER,list(range(10)),NOW)[1]['research_requests_used_today']==1
    (tmp_path/LEDGER).write_text(json.dumps({'budget_reservation_id':rid,'finalized_at':NOW.isoformat(),'requests_used':1}))
    assert allocation(tmp_path/LEDGER,list(range(10)),NOW)[1]['research_requests_used_today']==1


def test_persistence_failure_blocks_before_transport(tmp_path,monkeypatch):
    monkeypatch.setenv('RESEARCH_QUOTA_DURABLE','true')
    monkeypatch.setattr(checkpoint,'_refresh',lambda root: (_ for _ in ()).throw(OSError('offline')))
    with pytest.raises(ResearchQuotaBlocked,match='checkpoint unavailable'):
        reserve(tmp_path,[1],NOW)
    assert not (tmp_path/RESERVATIONS).exists()


def git(root,*args):
    return subprocess.check_output(['git',*args],cwd=root,text=True).strip()


def test_durable_grant_preserves_main_and_refreshes_stale_usage(tmp_path,monkeypatch):
    remote=tmp_path/'remote';remote.mkdir();git(remote,'init','--bare','--initial-branch=main')
    root=tmp_path/'clone';git(tmp_path,'clone',str(remote),str(root))
    git(root,'config','user.name','test');git(root,'config','user.email','test@example.test')
    (root/'unrelated').write_text('keep main content\n')
    (root/LEDGER).parent.mkdir(parents=True)
    (root/LEDGER).write_text(json.dumps({'finalized_at':NOW.isoformat(),'requests_used':4})+'\n')
    git(root,'add','.');git(root,'commit','-m','base');git(root,'push','origin','main')
    monkeypatch.setenv('RESEARCH_QUOTA_DURABLE','true')
    # Emulate a stale checkout with a locally changed unrelated file. Grant CAS
    # updates only the quota path and does not reset or overwrite this checkout.
    (root/LEDGER).write_text('')
    (root/'unrelated').write_text('keep local content\n')
    ids,budget,rid,count=reserve(root,[1,2],NOW)
    assert budget['research_requests_used_today']==4 and count==1
    git(root,'fetch','origin','main')
    assert git(root,'show','origin/main:unrelated')=='keep main content'
    assert (root/'unrelated').read_text()=='keep local content\n'
    assert json.loads(git(root,'show',f'origin/main:{RESERVATIONS}'))['reservation_id']==rid
    # The sixth request remains reserved for 17:00 UTC (00:00 Bangkok).
    with pytest.raises(ResearchQuotaBlocked):reserve(root,[1],NOW,manual=True)


def test_every_collector_workflow_persists_grants():
    for path in Path('.github/workflows').glob('*.yml'):
        text=path.read_text()
        if 'research_v2_slot_recovery' in text or 'europe_pinnacle_discovery' in text:
            assert "RESEARCH_QUOTA_DURABLE: 'true'" in text
            assert str(RESERVATIONS) in text
            assert 'research-v2-collectors' in text


def test_shared_transport_quota_block_is_not_api_failure(tmp_path,monkeypatch):
    from odds_scanner import europe_pinnacle_discovery as collector
    from odds_scanner.provider_request_budget import QuotaBlocked
    from test_collector_observation_contract import setup
    setup(tmp_path,monkeypatch)
    def get(path,*args):
        if path=='/account':return {}
        raise QuotaBlocked('no metered request sent')
    monkeypatch.setattr(collector,'_get',get)
    result=collector.run(tmp_path)
    assert result['status']=='SKIPPED_QUOTA' and result['requests_used']==0
    health=json.loads((tmp_path/'reports/scan_health_latest.json').read_text())['recent_reports'][0]
    assert health['status']=='WARNING' and health['api_error_count']==0


def test_exhausted_account_stops_before_grant_or_billable_transport(tmp_path,monkeypatch):
    from odds_scanner import europe_pinnacle_discovery as collector
    from test_collector_observation_contract import setup
    setup(tmp_path,monkeypatch)
    monkeypatch.setattr(collector,'summarize_account',lambda _: {'request_remaining':0})
    calls=[]
    def get(path,*args):
        calls.append(path);assert path=='/account';return {}
    monkeypatch.setattr(collector,'_get',get)
    result=collector.run(tmp_path)
    assert result['status']=='SKIPPED_QUOTA' and result['requests_used']==0
    assert calls==['/account'] and not (tmp_path/RESERVATIONS).exists()
