from datetime import datetime
from pathlib import Path
from odds_scanner.research_v2_scan_due import due
from odds_scanner import research_v2_slot_recovery as recovery
from odds_scanner.europe_pinnacle_discovery import _record_slot,SLOT_LEDGER_PATH


def test_zero_http_mapping_failure_does_not_block_primary(tmp_path,monkeypatch):
    now=datetime.fromisoformat('2026-10-12T21:16:00+07:00')
    report={'generated_at':'2026-10-12T21:15:00+07:00','scheduled_target_at':'2026-10-12T21:00:00+07:00',
        'actual_observed_at':'2026-10-12T21:15:00+07:00','football_day':'2026-10-12',
        'status':'API_REQUEST_FAILED','requests_used':0,'http_requests_attempted':0}
    _record_slot(tmp_path/SLOT_LEDGER_PATH,report,'FAILED')
    assert due(now,report,ledger_rows=recovery.read_ledger(tmp_path),snapshots=[])
    calls=[]
    def primary(root):
        calls.append('primary')
        _record_slot(root/SLOT_LEDGER_PATH,{**report,'generated_at':now.isoformat(),'actual_observed_at':now.isoformat(),
            'status':'ZERO_USABLE_FIXTURES','requests_used':1,'football_day_fixtures':0},'ZERO_FIXTURES')
        return {}
    monkeypatch.setattr(recovery,'primary',primary)
    monkeypatch.setattr(recovery,'fallback',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('successful slot called fallback')))
    recovery.run(tmp_path,now);assert calls==['primary']


def test_real_failed_request_spacing_uses_completion_time():
    ledger=[{'state':'FAILED','requests_used':1,'actual_observed_at':'2026-10-12T21:00:00+07:00',
        'request_completed_at':'2026-10-12T21:15:00+07:00'}]
    assert not due(datetime.fromisoformat('2026-10-12T21:20:00+07:00'),{},ledger_rows=ledger)
    assert due(datetime.fromisoformat('2026-10-12T21:31:00+07:00'),{},ledger_rows=ledger)


def test_legacy_pinnwire_trigger_uses_same_coordinator_and_new_schedule():
    text=Path('.github/workflows/pinnwire-probe.yml').read_text()
    assert 'python -m odds_scanner.research_v2_slot_recovery' in text
    assert 'python -m odds_scanner.pinnwire_probe' not in text
    assert "'odds_scanner.propline_research_v2'" not in text
    assert 'ODDSPAPI_KEY:' in text
    assert '  schedule:' not in text
