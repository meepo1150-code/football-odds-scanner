from datetime import datetime
from odds_scanner import research_v2_slot_recovery as recovery
from odds_scanner.europe_pinnacle_discovery import _record_slot, SLOT_LEDGER_PATH
from odds_scanner.research_v2_slots import read_ledger


def test_recovers_every_missing_target_and_preserves_late_time(tmp_path,monkeypatch):
    now=datetime.fromisoformat('2026-10-04T21:37:00+07:00')
    calls=[]
    def primary(root):
        calls.append(recovery.os.environ['RESEARCH_V2_FORCE_TARGET_AT'])
        return {'status':'API_REQUEST_FAILED'}
    def fallback(root,target_at):
        r={'scheduled_target_at':target_at.isoformat(),'actual_observed_at':now.isoformat(),
           'generated_at':now.isoformat(),'football_day':'2026-10-04','provider':'propline',
           'strict_snapshots_this_run':1,'football_day_fixtures':1,'schedule_lag_minutes':(now-target_at).total_seconds()/60}
        _record_slot(root/SLOT_LEDGER_PATH,r,'OBSERVED')
        return r
    monkeypatch.setattr(recovery,'primary',primary)
    monkeypatch.setattr(recovery,'fallback',fallback)
    _record_slot(tmp_path/SLOT_LEDGER_PATH,{'scheduled_target_at':'2026-10-04T21:00:00+07:00',
                 'actual_observed_at':'2026-10-04T21:05:00+07:00','generated_at':now.isoformat(),
                 'strict_snapshots_this_run':1},'OBSERVED')
    recovery.run(tmp_path,now)
    assert calls==['2026-10-04T20:00:00+07:00']
    assert sum(r['state']=='MISSED' for r in read_ledger(tmp_path))==4
    recovery.run(tmp_path,now)
    assert len(calls)==1


def test_expired_slots_do_not_request_or_fabricate_prices(tmp_path,monkeypatch):
    monkeypatch.setattr(recovery,'primary',lambda root: (_ for _ in ()).throw(AssertionError('provider called')))
    recovery.run(tmp_path,datetime.fromisoformat('2026-10-04T17:40:00+07:00'))
    rows=read_ledger(tmp_path)
    assert len(rows)==2
    assert all(r['state']=='MISSED' and r['requests_used']==0 for r in rows)
    assert all(r['actual_observed_at'] is None for r in rows)
