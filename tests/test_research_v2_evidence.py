import json
from odds_scanner.research_v2_evidence import build


def test_offline_bundle_rebuilds_all_reports_from_same_raw_population(tmp_path,monkeypatch):
    import urllib.request
    monkeypatch.setattr(urllib.request,'urlopen',lambda *a,**k:(_ for _ in ()).throw(AssertionError('network request')))
    paths={'provider_mappings.csv':'entity_type,internal_id,provider,provider_id,verification_status\n','competitions.csv':'competition_id,country_id,competition_name,status\n','countries.csv':'country_id,country_name,status\n'}
    for name,content in paths.items():
        p=tmp_path/'data/master'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
    raw=tmp_path/'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl';raw.parent.mkdir(parents=True)
    row={'fixture_id':'test','provider':'pinnwire','bookmaker':'pinnacle','source_semantics':'PINNWIRE_PREMATCH_FULL_SNAPSHOT','football_day':'2026-10-11','kickoff':'2026-10-11T15:00:00Z','observed_at':'2026-10-11T12:00:00Z','favorite_side':'H','ah':{'home_line':-.75,'away_line':.75,'home_price':1.95,'away_price':1.95,'selected_side_line':-.75,'selected_side_price':1.95}}
    raw.write_text(json.dumps(row)+'\n');before=raw.read_bytes()
    (raw.parent/'oddspapi_finished_results.jsonl').write_text(json.dumps({'fixture_id':'test','ft_home_goals':1,'ft_away_goals':0})+'\n')
    outcome=build(tmp_path)
    assert outcome['settled_identity_groups']==1 and outcome['network_requests']==0
    stats=json.loads((tmp_path/'reports/research_v2_pattern_statistics.json').read_text())
    e2e=json.loads((tmp_path/'reports/research_v2_end_to_end_audit.json').read_text())
    assert e2e['settled_fixtures']==stats['settled_fixtures']==1
    assert e2e['movement_classification_counts']=={'SINGLE_OBSERVATION':1}
    assert raw.read_bytes()==before
    assert (tmp_path/'reports/dashboard_scope.json').exists()
