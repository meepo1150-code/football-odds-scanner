from datetime import datetime
from odds_scanner import scan_stabilization as s
from test_scan_stabilization import save


def setup(monkeypatch, root):
    monkeypatch.setattr(s,'cohort',lambda *args: dict(policy='FIXED_1500_FIXTURE_COHORT_V1',schedule_response_id='raw',fixtures=[
        dict(fixture_id='pending',tournament_id=7,kickoff='2026-10-14T19:00:00Z'),
        dict(fixture_id='kickoff-at-primary',tournament_id=22,kickoff='2026-10-14T17:03:00Z')]))
    save(root,'reports/europe_pinnacle_research_v2_status.json',dict(
        collection_started_at='2026-10-14T14:04:03Z',quota_remaining_before=75,account_safety_reserve=10))
    save(root,str(s.RESERVATIONS),[dict(reservation_id='earlier',provider='oddspapi',requests_used=4,finalized_at='2026-10-14T14:04:05Z')])
    return datetime.fromisoformat('2026-10-14T15:00:00+00:00')


def test_unconfirmed_future_grant_blocks_readiness_even_with_capacity(monkeypatch,tmp_path):
    now=setup(monkeypatch,tmp_path)
    grants=s.rows(tmp_path/s.RESERVATIONS)+[dict(reservation_id='unknown-midnight',requests_used=1,finalized_at='2026-10-14T14:30:00Z',scheduled_target_at='2026-10-14T17:00:00+00:00')]
    save(tmp_path,str(s.RESERVATIONS),grants)
    result=s.readiness(tmp_path,now)
    assert result['allocated_tournament_ids']==[7]  # One daily call still fits.
    assert result['status']=='UNVERIFIED_OR_CAPACITY_BLOCKED'
    assert result['unconfirmed_grants']==['unknown-midnight']
    assert 'CANONICAL_GRANT_OUTCOME_UNCONFIRMED' in result['blocked_reasons']
    assert not result['runtime_verified'] and result['network_requests']==0


def test_forecast_excludes_kickoff_at_actual_primary(monkeypatch,tmp_path):
    now=setup(monkeypatch,tmp_path)
    result=s.readiness(tmp_path,now)
    assert result['remaining_prematch_at_target']==1
    assert result['pending_fixture_ids']==['pending']
    assert result['prematch_forecast_at']=='2026-10-15T00:03:00+07:00'
    assert result['blocked_reasons']==[]


def test_usage_is_utc_even_when_health_clock_is_bangkok(monkeypatch,tmp_path):
    setup(monkeypatch,tmp_path)
    result=s.readiness(tmp_path,datetime.fromisoformat('2026-10-15T00:00:00+07:00'))
    assert result['research_usage']['day']==4


def test_unknown_or_future_account_observation_is_not_ready(monkeypatch,tmp_path):
    now=setup(monkeypatch,tmp_path)
    for report in ({},{'collection_started_at':'2026-10-14T16:00:00Z','quota_remaining_before':75}):
        save(tmp_path,'reports/europe_pinnacle_research_v2_status.json',report)
        result=s.readiness(tmp_path,now)
        assert result['status']=='UNVERIFIED_OR_CAPACITY_BLOCKED'
        assert 'ACCOUNT_CAPACITY_UNCONFIRMED_OR_INSUFFICIENT' in result['blocked_reasons']
