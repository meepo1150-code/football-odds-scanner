from datetime import datetime
from pathlib import Path
from odds_scanner.research_v2_scan_due import due
from odds_scanner.research_v2_slots import read_ledger
from odds_scanner.europe_pinnacle_discovery import _record_slot,SLOT_LEDGER_PATH




def test_real_failed_request_spacing_uses_completion_time():
    ledger=[{'state':'FAILED','requests_used':1,'actual_observed_at':'2026-10-12T21:00:00+07:00',
        'request_completed_at':'2026-10-12T21:15:00+07:00'}]
    assert not due(datetime.fromisoformat('2026-10-12T21:20:00+07:00'),{},ledger_rows=ledger)
    assert due(datetime.fromisoformat('2026-10-12T21:31:00+07:00'),{},ledger_rows=ledger)


def test_legacy_pinnwire_trigger_cannot_collect_or_use_provider_secrets():
    text = Path('.github/workflows/pinnwire-probe.yml').read_text()
    assert 'python -m odds_scanner.research_v2_slot_recovery' not in text
    assert 'python -m odds_scanner.pinnwire_probe' not in text
    assert 'secrets.ODDSPAPI_KEY' not in text
    assert '  schedule:' not in text
    assert 'if: ${{ false }}' in text
