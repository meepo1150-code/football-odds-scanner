from datetime import datetime
from odds_scanner.research_v2_slots import coverage, targets
from odds_scanner.research_v2_scan_due import due


def dt(value):
    return datetime.fromisoformat(value)


def test_monday_before_first_slot_is_not_due():
    r=coverage(dt('2026-10-05T15:18:00+07:00'),'2026-10-05',[],[])
    assert [t.hour for t in targets('2026-10-05')]==[18,21]
    assert r['expected_elapsed_slots']==0
    assert r['coverage_fraction'] is None
    assert r['collection_state']=='NOT_DUE'


def test_sunday_missing_elapsed_slots_cannot_be_green():
    r=coverage(dt('2026-10-04T15:18:00+07:00'),'2026-10-04',[],[])
    assert r['expected_elapsed_slots']==2
    assert r['coverage_fraction']==0
    assert [x['state'] for x in r['canonical_slots'][:2]]==['MISSED','MISSING']


def test_duplicate_fallback_scans_only_complete_one_slot():
    rows=[{'provider':'propline','fixture_id':'x','scheduled_target_at':f'2026-10-04T21:{m}:00+07:00',
           'observed_at':f'2026-10-04T21:{m}:00+07:00'} for m in ('05','10','15')]
    r=coverage(dt('2026-10-04T22:30:00+07:00'),'2026-10-04',[],rows)
    assert r['observed_slots']==1
    assert r['missing_elapsed_slots']==6


def test_failed_empty_unverified_future_and_expired_evidence_are_not_completed():
    target='2026-10-04T21:00:00+07:00'
    rows=[{'scheduled_target_at':target,'actual_observed_at':'2026-10-04T21:05:00+07:00',
           'strict_snapshots':2,'state':state} for state in ('FAILED','MISSED',None)]
    rows += [{'scheduled_target_at':target,'actual_observed_at':when,'strict_snapshots':2,'state':'OBSERVED'}
             for when in ('2026-10-04T20:59:00+07:00','2026-10-05T00:00:00+07:00')]
    r=coverage(dt('2026-10-04T22:00:00+07:00'),'2026-10-04',rows,[])
    assert r['observed_slots']==0


def test_ledger_zero_fixtures_is_completed_without_provider_call():
    rows=[{'scheduled_target_at':'2026-10-05T18:00:00+07:00',
           'actual_observed_at':'2026-10-05T18:05:00+07:00','state':'ZERO_FIXTURES','football_day_fixtures':0}]
    now=dt('2026-10-05T18:37:00+07:00')
    assert coverage(now,'2026-10-05',rows,[])['coverage_fraction']==1
    assert not due(now,{},ledger_rows=rows)


def test_newest_success_does_not_hide_older_recoverable_slot():
    now=dt('2026-10-04T21:37:00+07:00')
    rows=[{'scheduled_target_at':f'2026-10-04T{h}:00:00+07:00',
           'actual_observed_at':f'2026-10-04T{h}:05:00+07:00','state':'OBSERVED','strict_snapshots':1}
          for h in (19,21)]
    assert due(now,{'generated_at':'2026-10-04T21:05:00+07:00','status':'RESEARCH_V2_OBSERVED',
                    'strict_snapshots_this_run':1},ledger_rows=rows)
