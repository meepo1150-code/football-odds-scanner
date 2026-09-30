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
