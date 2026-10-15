import json
from datetime import datetime
from odds_scanner import scan_stabilization as s


def save(root, name, values):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(values) if name.endswith('.json') else ''.join(json.dumps(v)+'\n' for v in values))


def test_midnight_same_utc_day_cached_cohort_and_final_request(monkeypatch,tmp_path):
    monkeypatch.setattr(s,'cohort',lambda root,day: dict(policy='FIXED_1500_FIXTURE_COHORT_V1',schedule_response_id='raw',fixtures=[
        dict(fixture_id='pending',tournament_id=7,kickoff='2026-10-14T19:00:00Z'),
        dict(fixture_id='exact-kickoff',tournament_id=22,kickoff='2026-10-14T17:00:00Z')]))
    # Five durable requests, including one transport which failed, are consumed.
    save(tmp_path,str(s.RESERVATIONS),[dict(reservation_id=str(i),provider='oddspapi',requests_used=1,
        finalized_at='2026-10-14T14:04:05Z') for i in range(5)])
    save(tmp_path,'reports/europe_pinnacle_research_v2_status.json',dict(
        collection_started_at='2026-10-14T14:04:03Z',quota_remaining_before=75,account_safety_reserve=10))
    now=datetime.fromisoformat('2026-10-14T15:00:00+00:00')
    result=s.readiness(tmp_path,now)
    assert result['target_at']=='2026-10-15T00:00:00+07:00'
    assert result['quota_utc_day']=='2026-10-14'
    assert result['status']=='READY_FROM_RETAINED_EVIDENCE'
    assert result['remaining_prematch_at_target']==1
    assert result['research_usage']['day']==5 and result['allocated_tournament_ids']==[7]
    assert result['account_remaining_estimate']==70
    assert result['network_requests']==0 and not result['runtime_verified']
    save(tmp_path,str(s.RESERVATIONS),[dict(reservation_id='spent',requests_used=6,finalized_at='2026-10-14T14:04:05Z')])
    assert s.readiness(tmp_path,now)['status']=='UNVERIFIED_OR_CAPACITY_BLOCKED'


def test_fixture_diagnostics_preserve_scope_and_do_not_infer_missing_market(monkeypatch,tmp_path):
    monkeypatch.setattr(s,'registry',lambda:[dict(tournament_id=17),dict(tournament_id=18)])
    monkeypatch.setattr(s,'cohort',lambda *a:dict(fixtures=[dict(fixture_id='valid')]))
    from odds_scanner import research_population,master_scan_scope,research_v2_slots
    monkeypatch.setattr(research_population,'exclusion_reason',lambda *a,**k:None)
    monkeypatch.setattr(master_scan_scope,'scan_scope_reason',lambda *a,**k:None)
    monkeypatch.setattr(research_v2_slots,'collection_snapshot',lambda r:r.get('fixture_id')=='valid')
    fixtures=[dict(fixtureId=fid,tournamentId=tid,startTime=ko) for fid,tid,ko in [
        ('started',17,'2026-10-14T14:00:00Z'),('unqueried',18,'2026-10-14T19:00:00Z'),
        ('valid',17,'2026-10-14T19:00:00Z'),('rejected',17,'2026-10-14T19:00:00Z'),
        ('missing',17,'2026-10-14T19:00:00Z')]]
    observed='2026-10-14T14:04:08Z'
    save(tmp_path,str(s.RAW_PATH),[dict(endpoint='/fixtures',response_id='raw',payload=fixtures),
        dict(endpoint='/odds-by-tournaments',observed_at=observed,payload=fixtures[:4])])
    save(tmp_path,'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl',[dict(fixture_id='valid',observed_at=observed)])
    save(tmp_path,'data/normalized/europe_pinnacle_research_v2_audit.jsonl',[
        dict(fixture_id='rejected',observed_at=observed,eligibility_reason='OK')])
    result=s.diagnostics(tmp_path,dict(schedule_response_id='raw',actual_observed_at=observed,
        football_day='2026-10-14',football_day_window_start='2026-10-14T05:00:00Z',
        football_day_window_end='2026-10-14T23:00:00Z',coverage_tournament_ids=[17]))
    assert result['reason_counts']==dict(ALREADY_KICKOFF=1,QUOTA_SKIPPED=1,VALID_ODDS=1,VALIDATION_REJECTED=1,MARKET_UNAVAILABLE=1)


def test_reviewed_ft_batch_has_exact_identity_and_final_source_assertions():
    from pathlib import Path
    from odds_scanner.web_result_evidence import _quality,_same_identity
    evidence=s.rows(Path('data/research/web_result_evidence_20261014_midnight.jsonl'))
    snapshots=s.rows(Path('data/normalized/europe_pinnacle_research_v2_snapshots.jsonl'))
    assert len(evidence)==2
    for result in evidence:
        assert _quality(result)[0]
        retained=[r for r in snapshots if r['fixture_id']==result['fixture_id']]
        assert retained and all(_same_identity(result,r) for r in retained)


def test_diagnostics_include_first_batch_and_exclude_other_attempts(monkeypatch, tmp_path):
    monkeypatch.setattr(s, 'registry', lambda: [dict(tournament_id=17)])
    monkeypatch.setattr(s, 'cohort', lambda *a: dict(fixtures=[]))
    from odds_scanner import research_population, master_scan_scope, research_v2_slots
    monkeypatch.setattr(research_population, 'exclusion_reason', lambda *a, **k: None)
    monkeypatch.setattr(master_scan_scope, 'scan_scope_reason', lambda *a, **k: None)
    monkeypatch.setattr(research_v2_slots, 'collection_snapshot', lambda r: True)
    fixtures = [dict(fixtureId=fid, tournamentId=17, startTime='2026-10-14T19:00:00Z')
                for fid in ('first-batch', 'last-batch', 'previous-attempt', 'not-returned')]
    save(tmp_path, str(s.RAW_PATH), [dict(endpoint='/fixtures', response_id='raw', payload=fixtures),
        dict(endpoint='/odds-by-tournaments', observed_at='2026-10-14T14:04:05Z', payload=fixtures[:1]),
        dict(endpoint='/odds-by-tournaments', observed_at='2026-10-14T14:04:08Z', payload=fixtures[1:2]),
        dict(endpoint='/odds-by-tournaments', observed_at='2026-10-14T14:03:59Z', payload=fixtures[2:])])
    save(tmp_path, 'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl', [
        dict(fixture_id='first-batch', observed_at='2026-10-14T14:04:05Z'),
        dict(fixture_id='last-batch', observed_at='2026-10-14T14:04:08Z'),
        dict(fixture_id='previous-attempt', observed_at='2026-10-14T14:03:59Z'),
        dict(fixture_id='not-returned', provider='pinnwire', observed_at='2026-10-14T14:04:05Z')])
    report = dict(schedule_response_id='raw', actual_observed_at='2026-10-14T14:04:08Z',
        collection_started_at='2026-10-14T14:04:03Z', request_completed_at='2026-10-14T14:04:08Z',
        football_day='2026-10-14', football_day_window_start='2026-10-14T05:00:00Z',
        football_day_window_end='2026-10-14T23:00:00Z', coverage_tournament_ids=[17])
    result = s.diagnostics(tmp_path, report)
    assert result['reason_counts'] == {'VALID_ODDS': 2, 'MARKET_UNAVAILABLE': 2}
    report['request_completed_at'] = '2026-10-14T14:04:04Z'
    assert s.diagnostics(tmp_path, report)['status'] == 'INSUFFICIENT_EVIDENCE'
