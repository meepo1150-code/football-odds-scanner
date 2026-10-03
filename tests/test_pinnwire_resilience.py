from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from odds_scanner.pinnwire_probe import _cooldown_until
from odds_scanner.research_v2_scan_due import due

def test_repeated_429_backoff_and_retry_after_floor():
    now=datetime(2026,10,3,tzinfo=timezone.utc)
    e=HTTPError('https://example.test',429,'limited',{},None)
    assert datetime.fromisoformat(_cooldown_until(e,now,4))==now+timedelta(hours=8)
    e.headers={'Retry-After':'172800'}
    assert datetime.fromisoformat(_cooldown_until(e,now,9))==now+timedelta(days=2)

def test_failed_slot_retry_bounded_and_fallback_success_stops_retry():
    now=datetime.fromisoformat('2026-10-05T19:05:00+07:00')
    report={'generated_at':'2026-10-05T18:00:00+07:00','status':'RATE_LIMITED'}
    assert due(now,report)
    report['generated_at']='2026-10-05T18:30:00+07:00'
    assert not due(now,report)
    fallback={'generated_at':'2026-10-05T18:01:00+07:00','status':'RESEARCH_V2_OBSERVED','strict_snapshots_this_run':9}
    report['generated_at']='2026-10-05T18:00:00+07:00'
    assert not due(now,report,fallback=fallback)
