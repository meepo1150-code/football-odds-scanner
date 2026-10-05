import json
from datetime import datetime, timezone
from odds_scanner.research_v2_operational_audit import build


def test_workflow_success_does_not_turn_missing_data_green(tmp_path):
    r=build(tmp_path)
    assert not r['data_assertions_passed']
    assert r['status']=='BROKEN_DATA_ASSERTIONS'
    assert not r['production_promotion_allowed']


def test_stale_fallback_does_not_claim_current_health(tmp_path):
    reports=tmp_path/'reports'; reports.mkdir()
    for n,d in {'research_v2_pattern_statistics':{'raw_snapshot_rows':0,'snapshot_rows':0,'quarantined_snapshot_rows':0},'research_v2_movement_status':{'source_snapshot_rows':0},'propline_research_v2_status':{'status':'RESEARCH_V2_OBSERVED','generated_at':'2026-09-01T00:00:00Z'},'oddspapi_quota_health':{'status':'QUOTA_EXHAUSTED','quota_exhausted':True}}.items():
        (reports/f'{n}.json').write_text(json.dumps(d))
    r=build(tmp_path,datetime(2026,9,29,tzinfo=timezone.utc))
    assert r['status']=='WAITING_EXTERNAL_DATA'
    assert r['data_assertions_passed']
    assert not r['providers']['propline']['usable_recent_output']
    assert r['providers']['oddspapi']['status']=='QUOTA_EXHAUSTED'


def test_overnight_audit_uses_dashboard_football_day(tmp_path):
    path=tmp_path/'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'fixture_id':'sample','provider':'pinnwire','football_day':'2026-09-30','observed_at':'2026-09-30T14:00:00Z','kickoff':'2026-09-30T19:00:00Z'})+'\n')
    result=build(tmp_path, datetime.fromisoformat('2026-10-01T01:00:00+07:00'))
    assert result['football_day']=='2026-09-30'
    assert result['counts']['current_day_valid_scans']==1


def test_weekend_missing_slots_are_degraded_even_when_files_are_consistent(tmp_path):
    reports=tmp_path/'reports'; reports.mkdir()
    for n,d in {
        'research_v2_pattern_statistics':{'raw_snapshot_rows':1,'snapshot_rows':1,'quarantined_snapshot_rows':0},
        'research_v2_movement_status':{'source_snapshot_rows':1},
        'propline_research_v2_status':{'status':'RESEARCH_V2_OBSERVED','generated_at':'2026-10-04T14:05:00Z'}
    }.items():
        (reports/f'{n}.json').write_text(json.dumps(d))
    path=tmp_path/'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        'fixture_id':'sample','provider':'propline','source':'propline:pinnacle',
        'bookmaker':'pinnacle','football_day':'2026-10-04',
        'observed_at':'2026-10-04T14:05:00Z','scheduled_target_at':'2026-10-04T21:05:00+07:00',
        'kickoff':'2026-10-04T20:00:00Z','research_only':True,
        'mainline_verified':True,'promotion_eligible':True,
        'source_semantics':'PROPLINE_PINNACLE_TWO_SIDED_CORE_MAINLINE',
        'favorite_side':'H',
        'ah':{'home_line':-0.5,'away_line':0.5,'home_price':1.95,'away_price':1.95,
              'selected_side_line':-0.5,'selected_side_price':1.95}
    })+'\n')
    r=build(tmp_path,datetime.fromisoformat('2026-10-04T15:30:00+00:00'))
    assert r['status']=='DEGRADED_DATA_COVERAGE'
    assert 'CURRENT_DAY_SLOT_COVERAGE_INCOMPLETE' in r['assertion_failures']
    assert r['counts']['expected_elapsed_slots']==7
    assert r['counts']['observed_slots']==1
    assert r['counts']['missing_elapsed_slots']==6
