import json
from datetime import datetime, timezone, timedelta
import pytest
from odds_scanner.research_request_budget import allocation
from odds_scanner import europe_pinnacle_discovery as collector

NOW=datetime(2026,10,4,5,tzinfo=timezone.utc)


def row(stamp=NOW,used=2,target='slot'):
    return {'finalized_at':stamp.isoformat(),'scheduled_target_at':target,'requests_used':used}


def test_budget_rotation_caps_and_deduplicates(tmp_path):
    path=tmp_path/'ledger'
    ids=list(range(54))
    first, report=allocation(path,ids,NOW)
    assert first==ids[:10] and not report['coverage_complete']
    path.write_text('\n'.join(json.dumps(x) for x in [row(),row()]))
    second, report=allocation(path,ids,NOW)
    assert second==ids[10:20] and report['research_requests_used_today']==2
    path.write_text(json.dumps(row(used=6)))
    assert allocation(path,ids,NOW)[0]==[]
    assert len(allocation(path,ids,NOW+timedelta(days=1))[0])<=10
    path.write_text(json.dumps(row(NOW-timedelta(days=1),180)))
    assert allocation(path,ids,NOW)[0]==[]
    assert allocation(path,ids,datetime(2026,11,1,tzinfo=timezone.utc))[0]==first


def test_exhausted_daily_budget_calls_no_provider_even_when_forced(tmp_path,monkeypatch):
    monkeypatch.setenv('RESEARCH_V2_FORCE_RUN','true')
    target=tmp_path/collector.TARGET_PATH;target.parent.mkdir(parents=True)
    target.write_text(json.dumps({'tournaments':[{'tournament_id':n} for n in range(54)]}))
    ledger=tmp_path/collector.SLOT_LEDGER_PATH;ledger.parent.mkdir(parents=True)
    ledger.write_text(json.dumps(row(datetime.now(timezone.utc),6)))
    monkeypatch.setattr(collector,'_get',lambda *a:pytest.fail('budget blocked before API call'))
    result=collector.run(tmp_path)
    assert result['status']=='SKIPPED_RESEARCH_REQUEST_BUDGET'
    assert result['requests_used']==0
    assert result['coverage_complete'] is False


def test_failed_attempts_remain_in_ledger_for_same_slot(tmp_path):
    ledger=tmp_path/'ledger'
    for i in range(3):
        report={'generated_at':(NOW+timedelta(minutes=i)).isoformat(),
                'scheduled_target_at':'same-slot','requests_used':2}
        collector._record_slot(ledger,report,'FAILED')
    assert len(ledger.read_text().splitlines())==3
    assert allocation(ledger,list(range(54)),NOW)[0]==[]


def test_corrupt_usage_fails_closed(tmp_path):
    path=tmp_path/'ledger';path.write_text('{broken')
    with pytest.raises(ValueError):allocation(path,list(range(54)),NOW)


def test_old_backfilled_unknown_usage_does_not_block_new_month(tmp_path):
    path=tmp_path/'ledger'
    path.write_text(json.dumps(row(NOW.replace(month=9),None)))
    assert allocation(path,list(range(54)),NOW)[0]
    path.write_text(json.dumps(row(NOW,None)))
    with pytest.raises(TypeError):allocation(path,list(range(54)),NOW)
