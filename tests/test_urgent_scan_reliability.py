"""Runtime regressions for missing primaries, failed grants and fixed cohorts."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from odds_scanner.research_v2_scan_due import due
from odds_scanner.research_request_budget import allocation, usage, RESERVATIONS
from odds_scanner.research_quota_checkpoint import reserve, ResearchQuotaBlocked
from odds_scanner.scan_health import refresh

LEDGER = Path('data/normalized/research_v2_slot_ledger.jsonl')


def dt(value):
    return datetime.fromisoformat(value)


@pytest.mark.parametrize('hour', [8, 11, 14, 17])
def test_missing_primary_due_at_first_watchdog_and_same_day_midnight(hour):
    now = datetime(2026, 10, 14, hour, 13, tzinfo=timezone.utc)
    assert due(now, {}, event='schedule', ledger_rows=[], snapshots=[])


def test_immutable_failure_cooldown_survives_report_overwrite():
    target = '2026-10-14T21:00:00+07:00'
    receipt = {'scheduled_target_at':target, 'state':'FAILED', 'requests_used':1,
               'actual_observed_at':'2026-10-14T21:03:00+07:00',
               'request_completed_at':'2026-10-14T21:03:00+07:00'}
    # A subsequent local control check cannot erase the last paid API attempt.
    assert not due(dt('2026-10-14T21:53:00+07:00'), {}, ledger_rows=[receipt])
    assert due(dt('2026-10-14T22:03:00+07:00'), {}, ledger_rows=[receipt])


def test_today_remaining_two_requests_go_to_21_and_midnight(tmp_path):
    path=tmp_path/LEDGER;path.parent.mkdir(parents=True)
    prior={'finalized_at':'2026-10-14T12:14:10+00:00','requests_used':4}
    path.write_text(json.dumps(prior)+'\n')
    ids=[7,18,22,98,682]
    assert allocation(path, ids, dt('2026-10-14T12:55:00+00:00'), manual=True)[0]==[]
    for hour in (14,17):
        now=datetime(2026,10,14,hour,3,tzinfo=timezone.utc)
        chosen,budget=allocation(path,ids,now,prioritized=True)
        assert chosen==ids and budget['research_daily_limit']==6 and budget['research_monthly_limit']==180
        with path.open('a') as f:
            f.write(json.dumps({'finalized_at':now.isoformat(),'scheduled_target_at':str(hour),'requests_used':1})+'\n')
    assert usage(path,now)[0]==6
    assert allocation(path,ids,now,manual=True)[0]==[]


def test_manual_cannot_take_unobserved_current_canonical_request(tmp_path):
    path=tmp_path/LEDGER;path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'finalized_at':'2026-10-14T12:00:00+00:00','requests_used':4}))
    chosen,budget=allocation(path,[1],dt('2026-10-14T14:03:00+00:00'),manual=True)
    assert chosen==[] and budget['current_canonical_requests_reserved']==1


def test_cancelled_grant_blocks_duplicate_recovery_before_new_grant(tmp_path,monkeypatch):
    monkeypatch.delenv('RESEARCH_QUOTA_DURABLE',raising=False)
    now=dt('2026-10-14T11:13:00+00:00')
    reserve(tmp_path,[1],now)
    preserved=(tmp_path/RESERVATIONS).read_bytes()
    with pytest.raises(ResearchQuotaBlocked,match='outcome unconfirmed'):
        reserve(tmp_path,[1],now+timedelta(minutes=60))
    assert (tmp_path/RESERVATIONS).read_bytes()==preserved
    assert usage(tmp_path/LEDGER,now)[0]==1


def test_fixed_cohort_failure_never_scans_unrelated_fallback(tmp_path,monkeypatch):
    from odds_scanner import research_v2_slot_recovery as recovery
    monkeypatch.setattr(recovery,'primary',lambda root:{'status':'SKIPPED_QUOTA', 'daily_cohort_policy':'FIXED_1500_FIXTURE_COHORT_V1'})
    monkeypatch.setattr(recovery,'fallback',lambda *a,**kw:pytest.fail('unmapped broad fallback'))
    reports=recovery.run(tmp_path,dt('2026-10-14T14:13:00+00:00'))
    assert len(reports)==1 and reports[0]['status']=='SKIPPED_QUOTA'


def test_partial_cohort_is_missing_in_health_even_with_workflow_success(tmp_path,monkeypatch):
    from odds_scanner import research_v2_slots
    monkeypatch.setattr(research_v2_slots,'coverage',lambda *a:{'canonical_slots':[{'state':'PARTIAL'}]})
    value=refresh(tmp_path,dt('2026-10-14T14:13:00+00:00'))
    assert value['status']=='FAIL' and value['scan_missing_count']==1


def test_completed_query_without_valid_snapshot_never_displays_observed():
    from odds_scanner.research_v2_slots import coverage
    setup={'provider':'oddspapi','scheduled_target_at':'2026-10-14T15:00:00+07:00',
           'collection_succeeded':True,'master_competitions_considered':92}
    checked={'scheduled_target_at':'2026-10-14T21:00:00+07:00',
             'actual_observed_at':'2026-10-14T21:13:00+07:00',
             'daily_cohort_query_complete':True,'daily_cohort_fixtures':[{'reason':'NO_MARKET'}],
             'state':'FAILED','strict_snapshots':0}
    result=coverage(dt('2026-10-14T21:20:00+07:00'),'2026-10-14',[setup,checked],[])
    slot=result['canonical_slots'][2]
    assert slot['state']=='CHECKED_NO_VALID_CORE_ODDS' and slot['canonical_fixture_count']==0
    assert slot['observed_at']=='2026-10-14T21:13:00+07:00'
