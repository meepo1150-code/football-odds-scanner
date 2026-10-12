from datetime import date, datetime, timedelta
import json

from odds_scanner.research_v2_slots import targets, coverage, schedule_version
from odds_scanner.research_v2_scan_due import due, needs_finalization
from odds_scanner.europe_pinnacle_discovery import _football_day_bounds, _schedule_timing
from odds_scanner import research_v2_slot_recovery as recovery


def dt(value):
    return datetime.fromisoformat(value)


def test_exactly_18_weekly_slots_and_legacy_cutover():
    week = date(2026, 10, 12)
    assert sum(len(targets(week + timedelta(days=i))) for i in range(7)) == 18
    assert [t.hour for t in targets('2026-10-17')] == [15,18,21,0]
    assert targets('2026-10-17')[-1].date() == date(2026,10,18)
    assert [t.hour for t in targets('2026-10-11')] == [12,15,18,19,20,21,22]
    assert schedule_version('2026-10-11') == 'BKK_LEGACY_V1'
    assert schedule_version('2026-10-12') == 'BKK_18_SLOTS_V2'


def test_both_weekend_midnights_and_utc_conversion():
    for midnight,day in [('2026-10-18T00:10:00+07:00','2026-10-17'),
                         ('2026-10-19T00:10:00+07:00','2026-10-18')]:
        now=dt(midnight)
        assert _football_day_bounds(now)[2] == day
        target,lag=_schedule_timing(now)
        assert target == targets(day)[-1] and lag==10
        assert target.astimezone(dt('2026-10-01T00:00:00+00:00').tzinfo).hour == 17
        assert due(now,{},ledger_rows=[],snapshots=[])
        assert due(now+timedelta(minutes=140),{},ledger_rows=[],snapshots=[])
        assert not due(now+timedelta(minutes=141),{},ledger_rows=[],snapshots=[])


def test_no_weekday_midnight_and_no_retroactive_old_missing_slots():
    now=dt('2026-10-14T00:10:00+07:00')
    assert not due(now,{},ledger_rows=[],snapshots=[])
    report=coverage(dt('2026-10-17T15:18:00+07:00'),'2026-10-17',[],[])
    assert report['expected_elapsed_slots']==1
    assert [r['target_time'][11:16] for r in report['canonical_slots']]==['15:00','18:00','21:00','00:00']


def test_zero_receipt_midnight_blocks_duplicate_provider_calls(tmp_path,monkeypatch):
    from odds_scanner.europe_pinnacle_discovery import _record_slot,SLOT_LEDGER_PATH
    now=dt('2026-10-19T00:20:00+07:00');target=targets('2026-10-18')[-1]
    _record_slot(tmp_path/SLOT_LEDGER_PATH,{'scheduled_target_at':target.isoformat(),
        'actual_observed_at':(target+timedelta(minutes=5)).isoformat(),
        'football_day':'2026-10-18','generated_at':now.isoformat(),
        'status':'ZERO_USABLE_FIXTURES','football_day_fixtures':0,'requests_used':1},'ZERO_FIXTURES')
    def forbidden(*a,**kw):raise AssertionError('duplicate provider request')
    monkeypatch.setattr(recovery,'primary',forbidden);monkeypatch.setattr(recovery,'fallback',forbidden)
    assert not due(now,{},ledger_rows=recovery.read_ledger(tmp_path),snapshots=[])
    assert recovery.run(tmp_path,now)==[]


def test_missing_midnight_is_finalized_after_150_minutes_without_fetch(tmp_path,monkeypatch):
    now=dt('2026-10-19T02:31:00+07:00')
    assert needs_finalization(now,[],[])
    def forbidden(*a,**kw):raise AssertionError('expired provider request')
    monkeypatch.setattr(recovery,'primary',forbidden);monkeypatch.setattr(recovery,'fallback',forbidden)
    recovery.run(tmp_path,now)
    rows=recovery.read_ledger(tmp_path)
    assert len(rows)==4 and all(r['state']=='MISSED' and r['requests_used']==0 for r in rows)
    assert all(r['football_day']=='2026-10-18' and r['schedule_version']=='BKK_18_SLOTS_V2' for r in rows)


def test_partial_cohort_empty_receipt_blocks_duplicates_but_never_certifies_full_scope(tmp_path):
    from odds_scanner.europe_pinnacle_discovery import _record_slot,SLOT_LEDGER_PATH
    now=dt('2026-10-17T15:20:00+07:00');target=targets('2026-10-17')[0]
    _record_slot(tmp_path/SLOT_LEDGER_PATH,{'scheduled_target_at':target.isoformat(),
        'actual_observed_at':(target+timedelta(minutes=5)).isoformat(),
        'football_day':'2026-10-17','generated_at':now.isoformat(),
        'status':'RESEARCH_V2_OBSERVED','football_day_fixtures':0,'requests_used':1,
        'strict_snapshots_this_run':0,'coverage_complete':False,'coverage_tournament_ids':[17]},'ZERO_FIXTURES')
    ledger=recovery.read_ledger(tmp_path)
    assert ledger[-1]['state']=='ZERO_COHORT'
    assert not due(now,{},ledger_rows=ledger,snapshots=[])
    report=coverage(now,'2026-10-17',ledger,[])
    assert report['observed_slots']==1 and report['partial_scope_slots']==1
    assert report['collection_state']=='DEGRADED_SCOPE'
