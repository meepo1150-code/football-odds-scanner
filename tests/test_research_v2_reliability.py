import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from odds_scanner.europe_pinnacle_discovery import _record_slot, _slot_done
from odds_scanner.research_v2_movement import run as build_movement

def test_movement_reads_nested_canonical_market_fields(tmp_path: Path):
    p=tmp_path/'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl'
    p.parent.mkdir(parents=True)
    rows=[
        {'fixture_id':'f1','football_day':'2026-09-18','observed_at':'2026-09-18T12:00:00+00:00','ah':{'selected_side_line':-0.5,'selected_side_price':1.95},'ou':{'line':2.5,'over_price':1.90,'under_price':2.00},'one_x_two':{'home':1.80,'draw':3.5,'away':4.5}},
        {'fixture_id':'f1','football_day':'2026-09-18','observed_at':'2026-09-18T15:00:00+00:00','ah':{'selected_side_line':-0.75,'selected_side_price':1.90},'ou':{'line':2.75,'over_price':1.95,'under_price':1.95},'one_x_two':{'home':1.75,'draw':3.6,'away':4.7}},
    ]
    p.write_text(''.join(json.dumps(x)+'\n' for x in rows),encoding='utf-8')
    report=build_movement(tmp_path)
    feature=json.loads((tmp_path/'data/normalized/research_v2_movement_features.jsonl').read_text().strip())
    assert feature['delta_ah_line']==-0.25
    assert feature['delta_favorite_price']==-0.05
    assert feature['delta_ou_line']==0.25
    assert report['numeric_delta_fields_built']==8

def test_slot_ledger_marks_zero_fixture_complete_and_missed_incomplete(tmp_path: Path):
    ledger=tmp_path/'ledger.jsonl'
    target=datetime(2026,9,18,21,0,tzinfo=ZoneInfo('Asia/Bangkok'))
    base={'scheduled_target_at':target.isoformat(),'football_day':'2026-09-18','actual_observed_at':target.isoformat(),'generated_at':target.isoformat(),'schedule_lag_minutes':0,'observation_timing':'ON_TIME','requests_used':8,'football_day_fixtures':0,'strict_snapshots_this_run':0,'status':'RESEARCH_V2_OBSERVED'}
    _record_slot(ledger,base,'ZERO_FIXTURES')
    assert _slot_done(ledger,target)
    _record_slot(ledger,{**base,'status':'MISSED_SLOT'},'MISSED')
    assert not _slot_done(ledger,target)
