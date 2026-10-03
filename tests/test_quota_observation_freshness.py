from odds_scanner.research_v2_operational_audit import quota_observation

def test_balance_not_current_after_newer_consumption():
    q={'generated_at':'2026-10-03T11:33:00Z','request_remaining':230}
    s={'generated_at':'2026-10-03T12:44:00Z','requests_used':11}
    result=quota_observation(q,s)
    assert result['request_remaining'] is None
    assert result['request_remaining_last_observed']==230
    assert result['balance_status']=='STALE_AFTER_RECORDED_USAGE'
    s['requests_used']=0
    assert quota_observation(q,s)['request_remaining']==230
