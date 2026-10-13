import json
from odds_scanner.pinnwire_result_join import enrich_snapshot_names, run, SNAPSHOTS_PATH
from odds_scanner.oddspapi_result_cache import RESULTS_PATH
from odds_scanner.research_population import exclusion_reason

def test_scope_removal_never_removes_retained_selected_identities():
    assert exclusion_reason({'fixture_id':'pinnwire:1637069553'}) is None
    assert exclusion_reason({'fixture_id':'api_football:1555155'}) is None
    assert exclusion_reason({'fixture_id':'api_football:1528862'})=='USER_APPROVED_FT_UNMATCHED_OUTSIDE_SELECTED_MASTER_SCOPE'

def test_missing_names_enrich_only_from_exact_persisted_provider_identity():
    s={'provider':'api_football','provider_fixture_id':'1','kickoff':'2026-09-24T16:00:00Z','league':'Liga Leumit','home':None,'away':None}
    f={**s,'home':'Alpha','away':'Beta'}
    assert enrich_snapshot_names([s],[f])[0]['home']=='Alpha'
    assert s['home'] is None
    for changed in ({'provider_fixture_id':'2'},{'league':'Other'},{'kickoff':'2026-09-24T16:01:00Z'}):
        assert enrich_snapshot_names([s],[{**f,**changed}])[0]['home'] is None
    assert enrich_snapshot_names([s],[f,{**f,'away':'Wrong'}])[0]['home'] is None

def test_verified_other_provider_result_is_not_unmatched_and_conflict_stays_blocked(tmp_path):
    s={'provider':'pinnwire','fixture_id':'pinnwire:test','home':'Alpha','away':'Beta','kickoff':'2026-09-24T16:00:00Z','observed_at':'2026-09-24T15:00:00Z','favorite_side':'H','ah':{'selected_side_line':-0.5,'selected_side_price':1.95}}
    p=tmp_path/SNAPSHOTS_PATH;p.parent.mkdir(parents=True);p.write_text(json.dumps(s)+'\n')
    r=tmp_path/RESULTS_PATH;r.write_text(json.dumps({'fixture_id':'pinnwire:test','ft_home_goals':2,'ft_away_goals':1,'result_source':'FOTMOB_EXACT'})+'\n')
    assert run(tmp_path)['unmatched']==0
    r.with_suffix('.conflicts.jsonl').write_text(json.dumps({'fixture_id':'pinnwire:test'})+'\n')
    assert run(tmp_path)['unmatched']==1

def test_official_reversed_identity_is_blocked_even_with_symmetric_score(tmp_path):
    from odds_scanner.research_v2_pattern_stats import build
    s={'provider':'pinnwire','bookmaker':'pinnacle','fixture_id':'pinnwire:reversed','home':'Alpha','away':'Beta','league':'Test league','football_day':'2026-09-24','kickoff':'2026-09-24T16:00:00Z','observed_at':'2026-09-24T15:00:00Z','favorite_side':'H','ah':{'selected_side_line':-0.5,'selected_side_price':1.95}}
    s['source_semantics']='PINNWIRE_PREMATCH_FULL_SNAPSHOT'
    s['ah'].update(home_line=-0.5,away_line=0.5,home_price=1.95,away_price=1.95)
    p=tmp_path/SNAPSHOTS_PATH;p.parent.mkdir(parents=True);p.write_text(json.dumps(s)+'\n')
    r=tmp_path/RESULTS_PATH;r.write_text(json.dumps({'fixture_id':s['fixture_id'],'ft_home_goals':1,'ft_away_goals':1,'result_source':'WEB_EVIDENCE_TIER_A_OFFICIAL'})+'\n')
    review={**s,'source':{'tier':'A_OFFICIAL','verification_method':'MANUAL_WEB_REVIEW','home':'Beta','away':'Alpha','kickoff':s['kickoff']}}
    q=tmp_path/'data/research/selected_fixture_identity_conflicts.jsonl';q.parent.mkdir(parents=True);q.write_text(json.dumps(review)+'\n')
    report=build(tmp_path)
    assert report['settled_fixtures']==0 and report['raw_unresolved_ft_fixtures']==1
