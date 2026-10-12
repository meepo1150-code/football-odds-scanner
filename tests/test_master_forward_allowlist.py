import json
from pathlib import Path
from odds_scanner.master_scan_scope import approved_competitions,forward_mappings,scan_scope_reason,filter_scan_targets
from odds_scanner.research_population import in_scope


def forbidden(*a,**kw):raise AssertionError('unmapped provider must not issue an HTTP request')


def test_92_approved_competitions_have_verified_namespaced_mapping():
    approved=approved_competitions();mapped=forward_mappings()
    assert len(approved)==92 and len(mapped)==92
    assert len([c for c in approved.values() if c.get('competition_type')=='DOMESTIC_CUP'])==8
    assert len([c for c in approved.values() if c.get('competition_type')=='UEFA_CLUB_COMPETITION'])==3
    assert {p for p,_ in mapped}=={'oddspapi'}
    assert set(mapped.values())==set(approved)


def test_verified_id_country_and_namespace_are_required_not_team_names():
    assert scan_scope_reason({'tournament_id':17,'country':'England'},provider='oddspapi') is None
    assert scan_scope_reason({'tournament_id':17,'country':'Spain'},provider='oddspapi')=='MASTER_COUNTRY_CONFLICT'
    assert scan_scope_reason({'tournament_id':17},provider='propline')=='MASTER_PROVIDER_COMPETITION_UNMAPPED'
    assert scan_scope_reason({'league':'Premier League','home':'Arsenal','away':'Chelsea'},provider='oddspapi')=='MASTER_PROVIDER_COMPETITION_ID_MISSING'
    assert scan_scope_reason({'tournament_id':17,'canonical_competition_id':'ESP-0001'},provider='oddspapi')=='MASTER_CANONICAL_ID_CONFLICT'
    assert filter_scan_targets([{'tournament_id':491},{'tournament_id':17}])==[{'tournament_id':17}]
    assert scan_scope_reason({'tournament_id':7,'country':'International Clubs'},provider='oddspapi') is None
    assert scan_scope_reason({'tournament_id':10783,'country':'International'},provider='oddspapi') is not None
    # Historical observations retain the separately reviewed population policy.
    assert in_scope({'tournament_id':491,'provider':'oddspapi','country':'Germany','league':'3. Liga'})


def test_propline_unmapped_catalog_and_fallback_issue_zero_requests(monkeypatch):
    from odds_scanner import propline_provider as p
    monkeypatch.setattr(p,'_get',forbidden)
    rows,errors=p.fetch('fake-test-key')
    assert rows==[] and errors==['MASTER_PROVIDER_MAPPING_UNAVAILABLE']
    assert p.LAST_FETCH_DIAGNOSTICS['http_requests_attempted']==0


def test_five_dollar_unmapped_provider_stops_before_fixture_and_odds_calls(tmp_path,monkeypatch):
    from odds_scanner import five_dollar_live_research_v2 as p
    monkeypatch.setattr(p,'_get',forbidden);monkeypatch.setenv(p.ENV_KEY,'fake-test-key')
    report=p.run(tmp_path)
    assert report['status']=='MASTER_PROVIDER_MAPPING_UNAVAILABLE' and report['requests_used']==0
    assert not (tmp_path/p.SNAPSHOT_PATH).exists()


def test_pinnwire_unmapped_provider_stops_before_global_prematch_fetch(tmp_path,monkeypatch):
    from odds_scanner import pinnwire_probe as p
    monkeypatch.setattr(p,'_fetch_payload',forbidden);monkeypatch.setattr(p,'REPORT',tmp_path/'report.json')
    report=p.collect()
    assert report['status']=='MASTER_PROVIDER_MAPPING_UNAVAILABLE' and report['request_attempts']==0
    assert p.probe()['requests_used']==0


def test_sgodds_unmapped_provider_stops_before_market_fetch(tmp_path,monkeypatch):
    from odds_scanner import sgodds_research_v2 as p
    monkeypatch.setattr(p,'fetch_current_markets',forbidden)
    report=p.run(tmp_path)
    assert report['status']=='MASTER_PROVIDER_MAPPING_UNAVAILABLE' and report['requests_used']==0


def test_propline_failed_catalog_cannot_reenable_unreviewed_fallback_sports(monkeypatch):
    from odds_scanner import propline_provider as p
    from odds_scanner import master_scan_scope as scope
    monkeypatch.setattr(scope,'forward_mappings',lambda:{('propline','soccer_epl'):'ENG-0001'})
    calls=[]
    def fail(path,*a,**kw):calls.append(path);raise TimeoutError('recorded catalog timeout')
    monkeypatch.setattr(p,'_get',fail)
    rows,errors=p.fetch('fake-test-key')
    assert rows==[] and errors and calls==['/sports']
    assert p.LAST_FETCH_DIAGNOSTICS['http_requests_attempted']==1
