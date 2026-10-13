from datetime import date, datetime, timedelta
import json
import pytest
from pathlib import Path
import yaml

from odds_scanner.research_v2_slots import targets, coverage, schedule_version
from odds_scanner.research_v2_scan_due import due, needs_finalization
from odds_scanner.europe_pinnacle_discovery import _football_day_bounds, _schedule_timing
from odds_scanner import research_v2_slot_recovery as recovery


def dt(value):
    return datetime.fromisoformat(value)


def test_versioned_preparation_slots_and_legacy_cutover():
    week = date(2026, 10, 12)
    assert sum(len(targets(week + timedelta(days=i))) for i in range(7)) == 26
    assert [t.hour for t in targets('2026-10-17')] == [15,18,21,0]
    assert targets('2026-10-17')[-1].date() == date(2026,10,18)
    assert [t.hour for t in targets('2026-10-11')] == [12,15,18,19,20,21,22]
    assert schedule_version('2026-10-11') == 'BKK_LEGACY_V1'
    assert schedule_version('2026-10-12') == 'BKK_18_SLOTS_V2'
    assert schedule_version('2026-10-13') == 'BKK_28_SLOTS_V4'
    assert sum(len(targets(date(2026,10,19)+timedelta(days=i))) for i in range(7))==28


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


def test_daily_midnight_and_no_retroactive_old_missing_slots():
    now=dt('2026-10-14T00:10:00+07:00')
    assert due(now,{},ledger_rows=[],snapshots=[])
    assert not due(dt('2026-10-13T00:10:00+07:00'),{},ledger_rows=[],snapshots=[])
    report=coverage(dt('2026-10-17T15:18:00+07:00'),'2026-10-17',[],[])
    assert report['expected_elapsed_slots']==1
    assert [r['target_time'][11:16] for r in report['canonical_slots']]==['15:00','18:00','21:00','00:00']


@pytest.mark.parametrize("football_day", ["2026-10-14", "2026-10-18"])
def test_zero_receipt_midnight_blocks_duplicate_provider_calls(tmp_path,monkeypatch,football_day):
    from odds_scanner.europe_pinnacle_discovery import _record_slot,SLOT_LEDGER_PATH
    target=targets(football_day)[-1];now=target+timedelta(minutes=20)
    _record_slot(tmp_path/SLOT_LEDGER_PATH,{'scheduled_target_at':target.isoformat(),
        'actual_observed_at':(target+timedelta(minutes=5)).isoformat(),
        'football_day':football_day,'generated_at':now.isoformat(),
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
    assert all(r['football_day']=='2026-10-18' and r['schedule_version']=='BKK_28_SLOTS_V4' for r in rows)


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


def test_old_empty_receipt_after_cutover_is_scope_unknown_not_full_scope_pass():
    target=targets('2026-10-17')[0];now=target+timedelta(minutes=20)
    ledger=[{'state':'ZERO_FIXTURES','scheduled_target_at':target.isoformat(),
        'actual_observed_at':(target+timedelta(minutes=5)).isoformat(),
        'football_day_fixtures':0,'requests_used':1,'collection_succeeded':True}]
    assert not due(now,{},ledger_rows=ledger,snapshots=[])
    report=coverage(now,'2026-10-17',ledger,[])
    assert report['collection_state']=='DEGRADED_SCOPE' and report['partial_scope_slots']==1
    assert ledger[0]['state']=='ZERO_FIXTURES'


def test_every_day_midnight_has_utc_schedule_and_recovery_heartbeats():
    for offset in range(7):
        day=date(2026,10,14)+timedelta(days=offset)
        target=targets(day)[-1]
        assert target.hour==0 and target.date()==day+timedelta(days=1)
        assert _football_day_bounds(target+timedelta(minutes=10))[2]==day.isoformat()
        assert due(target+timedelta(minutes=10),{},ledger_rows=[],snapshots=[])
    for name in ['free-research-v2-scanner','research-v2-scheduled-slot-recovery']:
        doc=yaml.safe_load(Path('.github/workflows/'+name+'.yml').read_text())
        events=doc.get('on',doc.get(True))
        crons=[r['cron'].split() for r in events['schedule']]
        for day in range(7):
            assert any(c[0]=='0' and '17' in c[1].split(',') and
                       (c[4]=='*' or c[4]=='1-5' and 1<=day<=5 or c[4]=='0,6' and day in (0,6)) for c in crons)
    for name in ['europe-pinnacle-daily-discovery','research-v2-slot-watchdog']:
        doc=yaml.safe_load(Path('.github/workflows/'+name+'.yml').read_text())
        crons=[r['cron'].split() for r in doc.get('on',doc.get(True))['schedule']]
        assert any('17' in c[1].split(',') and c[4]=='1-5' for c in crons)
        assert any('19' in c[1].split(',') and c[4]=='1-5' for c in crons)
