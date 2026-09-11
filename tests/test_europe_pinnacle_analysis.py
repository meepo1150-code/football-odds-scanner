from odds_scanner.europe_pinnacle_summary import summarize as summarize_accum
from odds_scanner.europe_pinnacle_movement import summarize as summarize_move
from odds_scanner.europe_pinnacle_movement_research import summarize as summarize_research


def _row(t,line=-0.5,ou=2.5):
    return {'fixture_id':'f1','observed_at':t,'country':'England','league':'Championship','home':'A','away':'B','favorite_side':'H','ah':{'selected_side_line':line,'selected_side_price':1.9},'ou':{'line':ou,'over_price':1.91,'under_price':1.99},'candidate_matching_allowed':False}


def test_summary_is_separate_pinnacle_universe():
    r=summarize_accum([_row('2026-09-11T00:00:00+00:00')],[{'country':'England','tournament_name':'Championship'}])
    assert r['classification']=='EUROPE_PINNACLE_DISCOVERY_ONLY'
    assert r['candidate_matching_allowed'] is False
    assert r['strict_observations']==1


def test_movement_uses_first_vs_latest_not_open_close_claim():
    r=summarize_move([_row('2026-09-11T00:00:00+00:00'),_row('2026-09-12T00:00:00+00:00',-0.75,2.75)])
    assert r['fixtures_with_repeated_observations']==1
    m=r['movement_rows'][0]
    assert m['ah']['first_observed_line']==-0.5
    assert m['ah']['latest_observed_line']==-0.75
    assert m['ah']['line_bucket']=='DOWN_.25'
    assert 'not guaranteed bookmaker opening price' in r['interpretation']
    assert 'CLV' in r['interpretation']


def test_research_has_no_outcomes_or_roi():
    movement=summarize_move([_row('2026-09-11T00:00:00+00:00'),_row('2026-09-12T00:00:00+00:00',-0.75)])
    r=summarize_research(movement)
    assert r['outcomes_joined'] is False
    assert r['roi_calculated'] is False
    assert r['production_promotion_allowed'] is False
    assert r['validation_gate_effect']=='NONE'
