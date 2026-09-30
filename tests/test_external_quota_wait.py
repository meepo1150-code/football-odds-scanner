import json
from odds_scanner import oddspapi_history_runner as history
from odds_scanner import oddspapi_tournament_universe as universe
from odds_scanner.provider_request_budget import QuotaBlocked


def blocked(*args, **kwargs):
    raise QuotaBlocked('known exhausted quota')


def test_history_wait_preserves_cursor_and_queue(tmp_path, monkeypatch):
    path=tmp_path/'reports/oddspapi_history_state.json'
    path.parent.mkdir()
    path.write_text(json.dumps({'discovery_cursor':'2026-07-27','fixture_queue':[{'fixtureId':'exact'}]}))
    monkeypatch.setattr(history,'_ROOT',tmp_path)
    monkeypatch.setattr(history.archive,'run_archive',blocked)
    history.main()
    result=json.loads(path.read_text())
    assert result['status']=='WAITING_EXTERNAL_DATA'
    assert result['discovery_cursor']=='2026-07-27'
    assert result['fixture_queue']==[{'fixtureId':'exact'}]


def test_universe_quota_wait_does_not_replace_candidates(tmp_path,monkeypatch):
    from odds_scanner import oddspapi_provider
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('ODDSPAPI_KEY','test-not-real')
    monkeypatch.setattr(oddspapi_provider,'_get',blocked)
    universe.OUT.parent.mkdir()
    universe.OUT.write_text('{"candidate_count":7}')
    universe.main()
    assert json.loads(universe.OUT.read_text())['candidate_count']==7
    health=json.loads((tmp_path/'reports/oddspapi_universe_health.json').read_text())
    assert health['requests_sent']==0 and health['status']=='WAITING_EXTERNAL_DATA'
