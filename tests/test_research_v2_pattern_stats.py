from odds_scanner.asian_settlement import settle_asian_handicap
from odds_scanner.research_v2_pattern_stats import _price_result, _price_bucket, _core, _movement

def price_result(line,home,away,odds=1.90):return _price_result(settle_asian_handicap(home,away,line,odds,'H').settlement.value)
def test_home_minus_1_5_wins_match_1_0_but_loses_price():assert price_result(-1.5,1,0)=='LOSS'
def test_home_minus_1_0_one_goal_win_is_push():assert price_result(-1.0,1,0)=='PUSH'
def test_home_minus_0_75_one_goal_win_is_half_win():assert price_result(-0.75,1,0)=='HALF_WIN'
def test_home_minus_0_5_one_goal_win_is_full_price_win():assert price_result(-0.5,1,0)=='WIN'
def test_home_minus_1_5_two_goal_win_is_full_price_win():assert price_result(-1.5,2,0)=='WIN'
def test_decimal_price_buckets():
    assert _price_bucket(1.80)=='1.80-1.89';assert _price_bucket(1.90)=='1.90-1.99';assert _price_bucket(2.00)=='2.00-2.09';assert _price_bucket(2.10)=='2.10-2.20';assert _price_bucket(2.20)=='2.10-2.20';assert _core(1.80) and _core(2.20);assert not _core(1.79) and not _core(2.21)
def test_favorite_switch_is_separate_movement_state():
    first={'favorite_side':'H','ah':{'selected_side_line':-0.5,'selected_side_price':1.90}};last={'favorite_side':'A','ah':{'selected_side_line':-0.25,'selected_side_price':1.95}};assert _movement(first,last)=='FAVORITE_SWITCH'

from odds_scanner.research_v2_pattern_stats import _ou25
from odds_scanner.research_v2_integrity import trusted_snapshot


def quote():
    return {'provider':'propline','bookmaker':'pinnacle',
            'mainline_verified':True,'source_semantics':'PROPLINE_PINNACLE_TWO_SIDED_CORE_MAINLINE',
            'observed_at':'2026-09-29T10:00:00Z','kickoff':'2026-09-29T12:00:00Z',
            'favorite_side':'H','ah':{'home_line':-.5,'away_line':.5,'home_price':1.9,
                                    'away_price':2,'selected_side_line':-.5,'selected_side_price':1.9},
            'ou':{'line':2.5,'over_price':1.9,'under_price':2}}


def test_ou25_prices_require_exact_line_and_preserve_goal_frequency():
    s=quote()
    assert _ou25(s,2,1)['ou25_over_price']==1.9
    for line in [None,2.25,2.75,3.5]:
        s['ou']['line']=line
        result=_ou25(s,2,1)
        assert result['ou25_result']=='OVER'
        assert result['ou25_over_price'] is None
        assert result['ou25_under_price'] is None


def test_ou25_rejects_missing_invalid_or_postmatch_prices():
    for bad in [None,0,1,float('nan'),float('inf')]:
        s=quote();s['ou']['under_price']=bad
        assert _ou25(s,0,0)['ou25_over_price'] is None
    for field,value in [('observed_at','2026-09-29T12:00:00Z'),('observed_at','bad'),
                        ('observed_at','2026-09-29T10:00:00'),('source_semantics',None),('bookmaker',None)]:
        s=quote();s[field]=value
        assert _ou25(s,0,0)['ou25_over_price'] is None


def test_propline_labels_do_not_override_pair_or_bookmaker_integrity():
    assert trusted_snapshot(quote())
    for field,value in [('bookmaker','other'),('mainline_verified',False),('kickoff','bad')]:
        s=quote();s[field]=value;assert not trusted_snapshot(s)
    for field,value in [('away_line',.75),('away_price',None),('home_price',float('nan')),
                        ('selected_side_price',4),('selected_side_line',-.75)]:
        s=quote();s['ah'][field]=value;assert not trusted_snapshot(s)


def test_ou25_roi_denominator_excludes_alternate_lines_end_to_end(tmp_path):
    import json
    from odds_scanner.research_v2_pattern_stats import build,SNAPSHOTS,RESULTS,OUTCOMES
    snapshots=[];results=[]
    for fid,line in [('exact',2.5),('alternate',3.5)]:
        s=quote();s.update(fixture_id=fid,football_day='2026-09-29');s['ou']['line']=line
        snapshots.append(s)
        results.append({'fixture_id':fid,'ft_home_goals':2,'ft_away_goals':1})
    for path,rows in [(SNAPSHOTS,snapshots),(RESULTS,results)]:
        p=tmp_path/path;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(''.join(json.dumps(x)+'\n' for x in rows))
    report=build(tmp_path)
    group=report['over_under_2_5_by_ah_line_price'][0]
    assert group['n']==2
    assert group['over_2_5_n']==2
    assert group['ou25_priced_n']==1
    assert group['over_2_5_roi_pct']==90.0
    assert group['under_2_5_roi_pct']==-100.0
    rows=[json.loads(x) for x in (tmp_path/OUTCOMES).read_text().splitlines()]
    exact=next(x for x in rows if x['fixture_id']=='exact')
    assert exact['ou25_observed_at']=='2026-09-29T10:00:00Z'
    assert exact['ou25_bookmaker']=='pinnacle'
    assert report['quarantined_snapshot_rows']==0


def test_conflict_ledger_blocks_result_reintroduced_by_another_writer(tmp_path):
    import json
    from odds_scanner.research_v2_pattern_stats import build,SNAPSHOTS,RESULTS
    s=quote();s.update(fixture_id='blocked',football_day='2026-09-29')
    for path,rows in [(SNAPSHOTS,[s]),(RESULTS,[{'fixture_id':'blocked','ft_home_goals':2,'ft_away_goals':1}]),(RESULTS.with_suffix('.conflicts.jsonl'),[{'fixture_id':'blocked','reason':'FOTMOB_NOT_NORMAL_TIME_FT'}])]:
        p=tmp_path/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(''.join(json.dumps(x)+'\n' for x in rows))
    report=build(tmp_path)
    assert report['settled_fixtures']==0 and report['raw_unresolved_ft_fixtures']==1
