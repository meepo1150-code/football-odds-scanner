import json
from datetime import datetime, timezone, timedelta
import pytest
from odds_scanner.research_request_budget import allocation
from odds_scanner import europe_pinnacle_discovery as collector

NOW=datetime(2026,10,12,14,tzinfo=timezone.utc)


def row(stamp=NOW,used=2,target='slot'):
    return {'finalized_at':stamp.isoformat(),'scheduled_target_at':target,'requests_used':used}


def test_unrestricted_batches_and_usage_reporting(tmp_path):
    path = tmp_path/'ledger'
    ids = list(range(54))
    chosen, report = allocation(path, ids, NOW)
    assert sorted(chosen) == ids
    assert report['coverage_complete'] is True
    assert report['research_daily_limit'] is None
    assert report['research_monthly_limit'] is None
    assert report['future_month_requests_reserved'] == 0
    path.write_text(json.dumps(row(used=999)))
    chosen, report = allocation(path, ids, NOW, manual=True)
    assert sorted(chosen) == ids
    assert report['research_requests_used_today'] == 999


def test_four_rounds_keep_full_cohort(tmp_path):
    path = tmp_path/'ledger'
    ids = list(range(54))
    for hour in (8, 11, 14, 17):
        now = datetime(2026, 10, 14, hour, tzinfo=timezone.utc)
        chosen, report = allocation(path, ids, now, prioritized=True)
        assert chosen == ids
        assert report['coverage_complete']


def test_failed_attempts_preserved_without_internal_block(tmp_path):
    ledger = tmp_path/'ledger'
    for i in range(4):
        report = {'generated_at': (NOW + timedelta(minutes=i)).isoformat(),
                  'scheduled_target_at': 'same-slot', 'requests_used': 2}
        collector._record_slot(ledger, report, 'FAILED')
    assert len(ledger.read_text().splitlines()) == 4
    assert allocation(ledger, list(range(54)), NOW)[0]


def test_corrupt_usage_fails_closed(tmp_path):
    path = tmp_path/'ledger'
    path.write_text('{broken')
    with pytest.raises(ValueError):
        allocation(path, list(range(54)), NOW)


def test_invalid_current_month_usage_fails_closed(tmp_path):
    path = tmp_path/'ledger'
    path.write_text(json.dumps(row(NOW, None)))
    with pytest.raises(ValueError):
        allocation(path, list(range(54)), NOW)


def test_provider_fallback_receipts_do_not_consume_oddspapi_usage(tmp_path):
    path = tmp_path/'ledger'
    path.write_text(json.dumps({**row(used=99), 'provider': 'propline'}))
    assert allocation(path, list(range(54)), NOW)[1]['research_requests_used_today'] == 0


def test_bangkok_midnight_uses_utc_usage_day(tmp_path):
    path = tmp_path/'ledger'
    path.write_text(json.dumps(row(datetime(2026,10,31,14,tzinfo=timezone.utc),6)))
    now = datetime.fromisoformat('2026-11-01T00:00:00+07:00')
    chosen, report = allocation(path, list(range(54)), now)
    assert chosen
    assert report['research_requests_used_today'] == 6
    reset = datetime.fromisoformat('2026-11-01T07:00:00+07:00')
    assert allocation(path, list(range(54)), reset)[1]['research_requests_used_month'] == 0
