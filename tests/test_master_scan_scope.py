import json
from pathlib import Path
from odds_scanner.master_scan_scope import bindings, filter_scan_targets
from odds_scanner.research_population import exclusion_reason, in_scope


def test_excluded_ids_are_observed_catalog_facts():
    root = Path(__file__).resolve().parents[1]
    raw = json.loads((root / 'reports/master_provider_snapshot.json').read_text())
    catalog = {str(r['tournamentId']): r for r in raw['tournaments']}
    exclusions = json.loads((root / 'data/master/research/user_excluded_divisions_2026_10_09.json').read_text())
    assert {r['competition_id'] for r in bindings()} == set(exclusions['excluded_competition_ids'])
    for r in bindings():
        item = catalog[r['provider_id']]
        assert item['categoryName'] == r['provider_country']
        assert item['tournamentName'] == r['provider_name']
        assert exclusion_reason({'tournament_id': r['provider_id']}, provider='oddspapi')


def test_provider_namespaces_and_same_named_leagues():
    assert exclusion_reason({'provider':'api_football','tournament_id':229}) is None
    assert exclusion_reason({'tournament_id':229}) is None
    assert exclusion_reason({'source_semantics':'CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED','tournament_id':229})
    assert in_scope({'provider':'oddspapi','tournament_id':202,'country':'Poland','league':'Ekstraklasa'})
    assert in_scope({'provider':'oddspapi','tournament_id':204,'country':'Russia','league':'1. Liga'})
    assert in_scope({'country':'England','league':'Premier League'})
    assert in_scope({'country':'Czech Republic','league':'1. Liga'})
    assert in_scope({'league':'Premier League'})
    assert not in_scope({'country':'Russia','league':'Premier League'})
    assert not in_scope({'league':'Poland - 1. Liga'})
    assert not in_scope({'country':'Poland','league':'I liga'})
    assert not in_scope({'country':'Russia','league':'Russian Premier League'})
    assert in_scope({'country':'Poland','league':'Ekstraklasa'})


def test_target_filter_preserves_input_and_unreviewed_competitions():
    targets = [{'tournament_id':229}, {'tournament_id':202}, {'tournament_id':491}]
    original = json.dumps(targets)
    assert filter_scan_targets(targets) == targets[1:]
    assert json.dumps(targets) == original


def test_scope_does_not_rewrite_old_archive(tmp_path):
    p = tmp_path / 'archive.jsonl'
    old = {'fixture_id':'legacy-polish-match','provider':'oddspapi','tournament_id':229,'price':1.9}
    p.write_text(json.dumps(old) + '\n')
    before = p.read_bytes()
    assert not in_scope(json.loads(p.read_text()))
    assert p.read_bytes() == before


def test_pinnacle_filters_before_odds_request(monkeypatch, tmp_path):
    import odds_scanner.europe_pinnacle_discovery as collector
    from datetime import datetime, timezone
    target = datetime.now(timezone.utc).astimezone(collector.BANGKOK).isoformat()
    p = tmp_path / collector.TARGET_PATH
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({'tournaments':[{'tournament_id':229,'country':'Poland','tournament_name':'1. Liga'}, {'tournament_id':17,'country':'England','tournament_name':'Premier League'}]}))
    monkeypatch.setenv(collector.ENV_KEY, 'test-secret')
    monkeypatch.setenv('RESEARCH_V2_FORCE_RUN', 'true')
    monkeypatch.setenv('RESEARCH_V2_FORCE_TARGET_AT', target)
    monkeypatch.setattr(collector, 'summarize_account', lambda _: {'request_remaining':100})
    calls = []
    def get(path, key, params=None, *args, **kwargs):
        calls.append((path, params))
        if path == '/account': return {}
        assert path == '/odds-by-tournaments'
        assert params['tournamentIds'] == '17'
        return []
    monkeypatch.setattr(collector, '_get', get)
    report = collector.run(tmp_path)
    assert report['master_scope_excluded_targets'] == 1
    assert report['resolved_competitions'] == 1
    assert any(path == '/odds-by-tournaments' for path, _ in calls)


def test_all_excluded_targets_make_no_provider_request(monkeypatch, tmp_path):
    import odds_scanner.europe_pinnacle_discovery as collector
    from datetime import datetime, timezone
    p = tmp_path / collector.TARGET_PATH
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({'tournaments':[{'tournament_id':r['provider_id']} for r in bindings()]}))
    monkeypatch.setenv('RESEARCH_V2_FORCE_RUN', 'true')
    monkeypatch.setenv('RESEARCH_V2_FORCE_TARGET_AT', datetime.now(timezone.utc).isoformat())
    monkeypatch.setenv(collector.ENV_KEY, 'test-secret')
    def get(*args, **kwargs):
        raise AssertionError('No account or odds call for an entirely excluded target set')
    monkeypatch.setattr(collector, '_get', get)
    report = collector.run(tmp_path)
    assert report['master_scope_excluded_targets'] == 6
    assert report['requests_used'] == 0
    assert report['status'] == 'SKIPPED_USER_EXCLUDED_COMPETITIONS'


def test_propline_never_discovers_non_master_sports(monkeypatch):
    from odds_scanner import propline_provider as provider
    assert 'soccer_japan_j_league' not in provider.SPORTS
    assert 'soccer_usa_mls' not in provider.SPORTS
    monkeypatch.setattr(provider, '_get', lambda path, key: [
        {'key':'soccer_epl','title':'Premier League','country':'England','active':True},
        {'key':'soccer_japan_j_league','title':'J1 League','country':'Japan','active':True},
        {'key':'soccer_usa_mls','title':'MLS','country':'USA','active':True},
        {'key':'soccer_unknown','title':'Premier League','country':'England','active':True},
    ])
    assert provider.active_soccer_sports('test-key') == ('soccer_epl',)
    monkeypatch.setattr(provider, '_get', lambda path, key: (_ for _ in ()).throw(TimeoutError('catalog unavailable')))
    assert provider.active_soccer_sports('test-key') == provider.SPORTS
