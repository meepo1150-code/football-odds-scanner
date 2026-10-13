import json
from datetime import datetime, timezone, timedelta
import pytest
from odds_scanner.research_request_budget import allocation
from odds_scanner import europe_pinnacle_discovery as collector

NOW=datetime(2026,10,12,14,tzinfo=timezone.utc)


def row(stamp=NOW,used=2,target='slot'):
    return {'finalized_at':stamp.isoformat(),'scheduled_target_at':target,'requests_used':used}


def test_budget_rotation_caps_and_deduplicates(tmp_path):
    path=tmp_path/'ledger'
    ids=list(range(54))
    first, report=allocation(path,ids,NOW)
    assert len(first)==10 and not report['coverage_complete']
    path.write_text('\n'.join(json.dumps(x) for x in [row(),row()]))
    second, report=allocation(path,ids,NOW)
    assert second==first and report['research_requests_used_today']==2
    path.write_text(json.dumps(row(used=6)))
    assert allocation(path,ids,NOW)[0]==[]
    assert len(allocation(path,ids,NOW+timedelta(days=1))[0])<=10
    path.write_text(json.dumps(row(NOW-timedelta(days=1),180)))
    assert allocation(path,ids,NOW)[0]==[]
    assert len(allocation(path,ids,datetime(2026,11,1,tzinfo=timezone.utc))[0])==5


@pytest.mark.parametrize("day", [14, 17])
def test_four_daily_slots_have_primary_budget_and_same_cohort(tmp_path, day):
    path=tmp_path/'ledger';ids=list(range(54));cohorts=[];receipts=[]
    for hour in (8,11,14,17):
        now=datetime(2026,10,day,hour,tzinfo=timezone.utc)
        chosen,report=allocation(path,ids,now)
        assert 0 < len(chosen) <= 5 and report['research_run_limit']==1
        cohorts.append(chosen)
        receipts.append(row(now,1,str(hour)))
        path.write_text('\n'.join(json.dumps(x) for x in receipts))
    assert all(x==cohorts[0] for x in cohorts)
    assert report['research_requests_used_today']==3


def test_exhausted_daily_budget_calls_no_provider_even_when_forced(tmp_path,monkeypatch):
    now=datetime(2026,10,12,14,tzinfo=timezone.utc)
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):
            return now.astimezone(tz) if tz else now.replace(tzinfo=None)
    monkeypatch.setattr(collector,'datetime',Clock)
    monkeypatch.delenv('RESEARCH_V2_FORCE_TARGET_AT',raising=False)
    monkeypatch.setenv('RESEARCH_V2_FORCE_RUN','true')
    target=tmp_path/collector.TARGET_PATH;target.parent.mkdir(parents=True)
    target.write_text(json.dumps({'tournaments':[{'tournament_id':n} for n in range(54)]}))
    ledger=tmp_path/collector.SLOT_LEDGER_PATH;ledger.parent.mkdir(parents=True)
    ledger.write_text(json.dumps(row(now,6)))
    monkeypatch.setattr(collector,'_get',lambda *a:pytest.fail('budget blocked before API call'))
    result=collector.run(tmp_path)
    assert result['status']=='SKIPPED_QUOTA'
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
    with pytest.raises(ValueError):allocation(path,list(range(54)),NOW)


def test_manual_and_recovery_cannot_spend_midnight_reserve(tmp_path):
    path=tmp_path/'ledger';ids=list(range(54))
    now=datetime(2026,10,14,14,tzinfo=timezone.utc)
    path.write_text(json.dumps(row(now,5)))
    for manual in (False,True):
        chosen,report=allocation(path,ids,now,manual=manual)
        assert chosen==[]
        assert report['future_utc_slots']==['2026-10-14T17:00:00+00:00']
        assert report['future_utc_requests_reserved']==1
    midnight=now.replace(hour=17)
    assert len(allocation(path,ids,midnight,prioritized=True)[0])==5
    assert allocation(path,ids,midnight)[1]['quota_utc_day']=='2026-10-14'


def test_preparation_discovery_and_four_slots_fit_every_utc_day(tmp_path):
    path=tmp_path/'ledger';receipts=[];ids=list(range(54))
    for day in range(14,18):
        for hour in (8,11,14,17):
            now=datetime(2026,10,day,hour,tzinfo=timezone.utc)
            overhead=int(hour==8)
            chosen,report=allocation(path,ids,now,overhead=overhead,prioritized=True)
            assert len(chosen)==5
            receipts.append(row(now,1+overhead,f'{day}-{hour}'))
            path.write_text('\n'.join(json.dumps(r) for r in receipts))
        assert allocation(path,ids,now)[1]['research_requests_used_today']==5


def test_bangkok_midnight_does_not_reset_utc_budget(tmp_path):
    path=tmp_path/'ledger';path.write_text(json.dumps(row(datetime(2026,10,31,14,tzinfo=timezone.utc),6)))
    now=datetime.fromisoformat('2026-11-01T00:00:00+07:00')
    assert allocation(path,list(range(54)),now)[0]==[]
    reset=datetime.fromisoformat('2026-11-01T07:00:00+07:00')
    assert allocation(path,list(range(54)),reset,manual=True)[1]['research_requests_used_month']==0


def test_monthly_capacity_reserved_for_future_days(tmp_path):
    path=tmp_path/'ledger';now=datetime(2026,10,30,14,tzinfo=timezone.utc)
    path.write_text(json.dumps(row(now-timedelta(days=1),174)))
    chosen,report=allocation(path,list(range(54)),now)
    assert chosen==[] and report['future_month_requests_reserved']==5
    path.write_text(json.dumps(row(now-timedelta(days=1),173)))
    assert len(allocation(path,list(range(54)),now)[0])==5


def test_provider_fallback_receipts_do_not_consume_oddspapi_budget(tmp_path):
    path=tmp_path/'ledger';r={**row(used=99),'provider':'propline'}
    path.write_text(json.dumps(r))
    assert allocation(path,list(range(54)),NOW)[1]['research_requests_used_today']==0


@pytest.mark.parametrize('month', [11, 12])
def test_complete_month_preserves_all_four_slots_with_optional_breadth(tmp_path, month):
    """Optional calls yield before they exhaust later discovery or midnight."""
    import calendar
    from odds_scanner.research_request_budget import usage
    path = tmp_path/'ledger'
    ids = list(range(54))
    receipts = []
    for day in range(1, calendar.monthrange(2026, month)[1]+1):
        for hour in (8, 11, 14, 17):
            now = datetime(2026, month, day, hour, 5, tzinfo=timezone.utc)
            overhead = int(hour == 8)
            chosen, _ = allocation(path, ids, now, prioritized=True, overhead=overhead)
            assert len(chosen) == 5
            receipts.append(row(now, 1+overhead, f'{day}-{hour}'))
            path.write_text('\n'.join(json.dumps(r) for r in receipts))
        extra_at = now.replace(hour=20)
        chosen, _ = allocation(path, ids, extra_at, prioritized=True, manual=True)
        if chosen:
            receipts.append(row(extra_at, len(chosen)//5, f'extra-{day}'))
            path.write_text('\n'.join(json.dumps(r) for r in receipts))
        daily, monthly = usage(path, extra_at)
        assert daily <= 6 and monthly <= 180
    assert monthly == 180
