import json
from datetime import datetime, timezone
from pathlib import Path
from odds_scanner.scan_health import record, refresh, rows, HISTORY, write_latest
from odds_scanner.research_v2_persistence import merge_staged


def save(root, name, value):
    p=root/'reports'/f'{name}.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value))


def report(**values):
    return dict(generated_at='2026-10-13T08:01:00+00:00', actual_observed_at='2026-10-13T15:01:00+07:00',
                football_day='2026-10-13', scheduled_target_at='2026-10-13T15:00:00+07:00',
                status='ZERO_USABLE_FIXTURES', scheduled_approved_fixtures=0, football_day_fixtures=0,
                requests_used=1, coverage_complete=True, **values)


def test_full_scope_zero_pass_and_unknown_not_zero(tmp_path):
    assert record(tmp_path,report())['status']=='PASS'
    r=report();r.pop('scheduled_approved_fixtures');r.pop('football_day_fixtures')
    v=record(tmp_path,r)
    assert v['fixtures_found'] is None and v['fixtures_without_valid_odds'] is None
    assert v['status']=='WARNING'


def test_failed_and_quota_skip_are_not_clean_empty(tmp_path):
    r=report();r.update(status='API_REQUEST_FAILED',errors=['private key in exception'],coverage_complete=False)
    v=record(tmp_path,r);assert v['status']=='FAIL' and v['api_error_count']==1
    assert 'private key' not in (tmp_path/HISTORY).read_text()
    r=report();r.update(scheduled_approved_fixtures=8,competition_coverage=[{'reason':'QUOTA_SKIPPED','remaining_prematch_fixtures':8}])
    v=record(tmp_path,r);assert v['status']=='WARNING' and v['fixtures_unqueried']==8


def test_append_idempotence_merge_and_skip_cannot_replace_latest_scan(tmp_path):
    a=tmp_path/'a';b=tmp_path/'b'
    record(a,report());record(a,report());assert len(rows(a/HISTORY))==1
    r=report();r.update(generated_at='2026-10-13T08:02:00+00:00',status='SKIPPED_SLOT_ALREADY_OBSERVED')
    record(b,r);merge_staged(a,b);assert len(rows(a/HISTORY))==2
    assert write_latest(a)['latest_scan']['scan_status']=='ZERO_USABLE_FIXTURES'
    original=(a/HISTORY).read_bytes();merge_staged(a,b);assert (a/HISTORY).read_bytes()==original


def test_retired_approved_conflict_is_visible_but_postponed_not_ft_delay(tmp_path):
    save(tmp_path,'research_v2_missing_ft_ledger',{'fixtures':[
        {'fixture_id':'approved-conflict','kickoff':'2026-10-12T12:00:00Z','status':'IDENTITY_CONFLICT','retired_from_active_queue':True},
        {'fixture_id':'postponed','kickoff':'2026-10-12T12:00:00Z','status':'POSTPONED'}]})
    save(tmp_path,'research_v2_fixture_identity',{'rejected':[{'reason':'CONFLICT'}]})
    v=refresh(tmp_path,datetime(2026,10,13,11,tzinfo=timezone.utc))
    assert v['status']=='FAIL' and v['scan_missing_count']==2
    assert v['ft_delay_count']==1 and v['ft_delay'][0]['fixture_id']=='approved-conflict'
    assert v['verified_non_ft_lifecycle_count']==1 and v['unmatched_count']==1 and v['raw_deleted']==0


def test_collector_workflows_stage_archive_and_pages_publish_it():
    for p in Path('.github/workflows').glob('*.yml'):
        s=p.read_text()
        if 'python -m odds_scanner.research_v2_persistence' in s:
            assert 'data/normalized/scan_health_history.jsonl' in s
    s=Path('.github/workflows/pages.yml').read_text()
    assert 'scan_health_history.jsonl' in s and 'scan_health_monitor.json' in s


def test_quota_skip_is_warning_and_never_an_api_failure(tmp_path):
    from odds_scanner.scan_health import record
    r=report();r.update(status='SKIPPED_QUOTA',requests_used=0,errors=['prior diagnostic'],quota_skip_reason='UTC_DAILY_EXHAUSTED')
    receipt=record(tmp_path,r)
    assert receipt['status']=='WARNING'
    assert receipt['api_error_count']==0
    assert 'SKIPPED_QUOTA' in receipt['issues']
    assert 'API_OR_CONFIGURATION_FAILURE' not in receipt['issues']
    assert receipt['fixtures_with_valid_odds']==0
