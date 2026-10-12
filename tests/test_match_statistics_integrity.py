import json
from odds_scanner.research_v2_pattern_stats import build,SNAPSHOTS,RESULTS,OUTCOMES,_price_bucket


def snapshot(fid,when,price=1.9):
    return {'fixture_id':fid,'provider':'pinnwire','bookmaker':'pinnacle',
        'source_semantics':'PINNWIRE_MAINLINE','favorite_side':'H',
        'observed_at':when,'kickoff':'2026-10-17T23:00:00+07:00',
        'football_day':'2026-10-17','ah':{'home_line':-.25,'away_line':.25,
        'home_price':price,'away_price':2.0,'selected_side_line':-.25,'selected_side_price':price}}


def write(root,path,rows):
    p=root/path;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(''.join(json.dumps(r)+'\n' for r in rows))


def test_four_rounds_are_one_match_latest_valid_prematch_selected(tmp_path):
    rows=[snapshot('one',f'2026-10-17T{h}:00:00+07:00',p) for h,p in [(15,1.9),(18,1.95),(21,2.0),(22,2.1)]]
    rows += [snapshot('one','2026-10-17T23:00:00+07:00',1.8),snapshot('one','2026-10-18T00:00:00+07:00',1.85)]
    write(tmp_path,SNAPSHOTS,rows);write(tmp_path,RESULTS,[{'fixture_id':'one','ft_home_goals':0,'ft_away_goals':0}])
    report=build(tmp_path);out=json.loads((tmp_path/OUTCOMES).read_text())
    assert report['settled_fixtures']==1 and report['baseline_by_market_side_line'][0]['n']==1
    assert out['scan_count']==4 and out['ah_price']==2.1
    assert report['invalid_statistical_snapshot_rows']==2
    assert out['favorite_ah_settlement']=='HALF_LOSS' and out['favorite_profit_units']==-.5


def test_chronological_order_not_iso_string_order(tmp_path):
    write(tmp_path,SNAPSHOTS,[snapshot('one','2026-10-17T15:00:00+07:00',1.9),snapshot('one','2026-10-17T14:00:00Z',2.1)])
    write(tmp_path,RESULTS,[{'fixture_id':'one','ft_home_goals':1,'ft_away_goals':0}])
    build(tmp_path);assert json.loads((tmp_path/OUTCOMES).read_text())['ah_price']==2.1


def test_retired_and_conflict_remain_in_ft_denominator(tmp_path):
    write(tmp_path,SNAPSHOTS,[snapshot(fid,'2026-10-17T21:00:00+07:00') for fid in ['settled','retired','conflict']])
    write(tmp_path,RESULTS,[{'fixture_id':'settled','ft_home_goals':1,'ft_away_goals':0},
        {'fixture_id':'conflict','ft_home_goals':1,'ft_away_goals':0},
        {'fixture_id':'conflict','ft_home_goals':2,'ft_away_goals':0}])
    write(tmp_path,SNAPSHOTS.parent/'research_v2_retired_fixtures.jsonl',[{'fixture_id':'retired'}])
    report=build(tmp_path)
    assert report['settled_fixtures']==1 and report['ft_completeness_denominator']==3
    assert report['ft_completeness_pct']==33.33 and report['identity_conflict_ft_fixtures']==1
    assert report['raw_unresolved_ft_fixtures']==2 and report['retired_unresolved_ft_fixtures']==1


def test_every_requested_water_boundary():
    assert [_price_bucket(x) for x in [1.89,1.9,1.99,2,2.09,2.1,2.2]] == ['1.80-1.89','1.90-1.99','1.90-1.99','2.00-2.09','2.00-2.09','2.10-2.20','2.10-2.20']
