from copy import deepcopy
from odds_scanner.observation_movement import describe
from odds_scanner.research_v2_end_to_end_audit import evaluate


def quote():
    return dict(fixture_id='x',provider='pinnwire',bookmaker='pinnacle',source_semantics='PINNWIRE_PREMATCH_FULL_SNAPSHOT',favorite_side='H',observed_at='2026-10-11T12:00:00Z',kickoff='2026-10-11T16:00:00Z',ah=dict(selected_side_line=-.75,selected_side_price=1.95))


def test_single_duplicate_and_inplay_are_never_flat():
    a=quote()
    assert describe([a])['movement']=='SINGLE_OBSERVATION'
    assert describe([a,a])['movement']=='SINGLE_OBSERVATION'
    b={**a,'observed_at':a['kickoff']}
    assert describe([a,b])['movement']=='SINGLE_OBSERVATION'


def test_flat_requires_same_contract_and_distinct_prematch_times():
    a=quote();b={**a,'observed_at':'2026-10-11T14:00:00Z'}
    r=describe([a,b]);assert r['movement']=='AH_LINE_UNCHANGED__PRICE_FLAT'
    assert r['observation_gap_minutes']==120
    for field,value in [('provider','other'),('bookmaker','other'),('period','1H'),('market','OU'),('source_semantics','OTHER')]:
        switched={**b,field:value}
        assert describe([a,switched])['movement']=='SOURCE_SWITCH__INSUFFICIENT_OBSERVATIONS'


def test_same_source_history_and_switch_flags_are_separate():
    a=quote();b=deepcopy(a);b['observed_at']='2026-10-11T14:00:00Z';b['ah'].update(selected_side_line=-1,selected_side_price=1.90)
    r=describe([a,b]);assert r['line_change'] and r['price_change'] and not r['source_switch']
    b['favorite_side']='A';assert describe([a,b])['favorite_switch']


def test_chronological_evaluation_cannot_call_viewed_data_untouched():
    r=evaluate([])
    assert r['untouched_holdout'] is False and r['promotion_allowed'] is False
    assert r['unique_evaluated_fixtures']==0


def test_recovery_only_fetches_latest_elapsed_target(tmp_path,monkeypatch):
    from datetime import datetime
    from odds_scanner import research_v2_slot_recovery as recovery
    calls=[]
    monkeypatch.setattr(recovery,'primary',lambda root:calls.append(recovery.os.environ['RESEARCH_V2_FORCE_TARGET_AT']) or {})
    monkeypatch.setattr(recovery,'fallback',lambda *args,**kw:{})
    recovery.run(tmp_path,datetime.fromisoformat('2026-10-11T22:10:00+07:00'))
    assert calls==['2026-10-11T22:00:00+07:00']


def test_provider_429_stops_catalog_fanout(monkeypatch):
    from odds_scanner import master_scan_scope as scope
    monkeypatch.setattr(scope,'forward_mappings',lambda:{('propline','soccer_test'):'ENG-0001'})
    import urllib.error
    from odds_scanner import propline_provider as pp
    calls=[]
    def get(path,*args):
        calls.append(path)
        raise urllib.error.HTTPError('https://api.prop-line.com',429,'rate limit',{'Retry-After':'7200'},None)
    monkeypatch.setattr(pp,'_get',get)
    rows,errors=pp.fetch('test-key')
    assert rows==[] and len(errors)==1 and calls==['/sports']
    assert pp.LAST_FETCH_DIAGNOSTICS['failure_class']=='RATE_LIMITED'
    assert pp.retry_seconds(urllib.error.HTTPError('x',429,'rate limit',{'Retry-After':'7200'},None))==7200


def test_provider_time_budget_defers_without_request_storm(monkeypatch):
    from odds_scanner import propline_provider as pp
    ticks=iter([0,230])
    monkeypatch.setattr(pp.time,'monotonic',lambda:next(ticks))
    monkeypatch.setattr(pp,'active_soccer_sports',lambda key:('sport',))
    monkeypatch.setattr(pp,'_get',lambda *a:(_ for _ in ()).throw(AssertionError('request after budget')))
    rows,errors=pp.fetch('test')
    assert rows==[] and errors and pp.LAST_FETCH_DIAGNOSTICS['bounded_runtime_partial']
