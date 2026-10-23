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


def test_retirement_changes_queue_counts_not_settled_statistics(tmp_path):
    import json
    from odds_scanner.research_v2_pattern_stats import build,SNAPSHOTS,RESULTS
    path=tmp_path/SNAPSHOTS;path.parent.mkdir(parents=True)
    good={**quote(),'fixture_id':'settled'};missing={**quote(),'fixture_id':'missing'}
    path.write_text(json.dumps(good)+'\n'+json.dumps(missing)+'\n')
    (tmp_path/RESULTS).write_text(json.dumps({'fixture_id':'settled','ft_home_goals':1,'ft_away_goals':0})+'\n')
    before=build(tmp_path)
    (path.parent/'research_v2_retired_fixtures.jsonl').write_text(json.dumps({'fixture_id':'missing'})+'\n')
    after=build(tmp_path)
    for field in ['settled_fixtures','core_price_settled_fixtures','market_state_by_side_line_price','over_under_2_5_by_ah_line_price']:
        assert before[field]==after[field]
    assert after['raw_unresolved_ft_fixtures']==1
    assert after['retired_unresolved_ft_fixtures']==1 and after['active_unresolved_ft_fixtures']==0


def test_equivalent_line_representations_share_wr_and_ou_populations(tmp_path):
    import json
    from odds_scanner.research_v2_pattern_stats import build,SNAPSHOTS,RESULTS
    snapshots=[];results=[]
    for i,line in enumerate([-1,-1.0,'-1.00',0,0.0,-0.0]):
        s=quote();s.update(provider='oddspapi',fixture_id=str(i),home='Home',away='Away')
        s['ah'].update(home_line=line,away_line=-float(line),selected_side_line=line)
        snapshots.append(s);results.append({'fixture_id':str(i),'ft_home_goals':2 if i==0 else 1,'ft_away_goals':0 if i<3 else 1})
    for path,rows in [(SNAPSHOTS,snapshots),(RESULTS,results)]:
        p=tmp_path/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(''.join(json.dumps(x)+'\n' for x in rows))
    raw=(tmp_path/SNAPSHOTS).read_bytes()
    r=build(tmp_path)
    groups={x['ah_line']:x for x in r['baseline_by_market_side_line']}
    assert set(groups)=={'-1','0'}
    assert groups['-1']['n']==3 and groups['-1']['full_win']==1 and groups['-1']['push']==2
    assert groups['-1']['favorite_price_win_pct']==33.33
    assert groups['0']['n']==3 and groups['0']['push']==3
    assert len(r['over_under_2_5_by_ah_line_price'])==2
    assert (tmp_path/SNAPSHOTS).read_bytes()==raw




def test_avg_total_goals_by_ah_price_bucket_uses_verified_ft_once(tmp_path):
    """A late prematch quote supersedes early quotes; missing/ambiguous FT never enters means."""
    import json
    from odds_scanner.research_v2_pattern_stats import build, SNAPSHOTS, RESULTS

    snapshots = []
    results = []
    for fid, price, goals in [
        ('three_goals', 1.90, (2, 1)),
        ('one_goal', 1.91, (1, 0)),
        ('five_goals', 1.95, (3, 2)),
        ('other_bucket', 2.05, (0, 0)),
        ('conflicted', 1.93, (4, 0)),
    ]:
        row = quote()
        row.update(fixture_id=fid, football_day='2026-09-29')
        row['ah']['home_price'] = price
        row['ah']['selected_side_price'] = price
        snapshots.append(row)
        results.append({'fixture_id': fid, 'ft_home_goals': goals[0], 'ft_away_goals': goals[1]})
    old = quote()
    old.update(fixture_id='three_goals', football_day='2026-09-29', observed_at='2026-09-29T09:00:00Z')
    old['ah']['home_price'] = 2.05
    old['ah']['selected_side_price'] = 2.05
    snapshots.append(old)
    missing = quote()
    missing.update(fixture_id='missing', football_day='2026-09-29')
    snapshots.append(missing)
    results.append({'fixture_id': 'conflicted', 'ft_home_goals': 0, 'ft_away_goals': 0})

    for path, rows in ((SNAPSHOTS, snapshots), (RESULTS, results)):
        file = tmp_path / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(''.join(json.dumps(item) + '\\n' for item in rows))
    report = build(tmp_path)
    by_price = {item['ah_price_bucket']: item for item in report['over_under_2_5_by_ah_line_price']}
    mid = by_price['1.90-1.99']
    assert report['settled_fixtures'] == 4
    assert mid['n'] == mid['goals_n'] == 3
    assert mid['total_goals'] == 9
    assert mid['avg_total_goals'] == 3.0
    assert mid['over_3_5_n'] == 1
    assert mid['over_3_5_pct'] == 33.33
    outer = by_price['2.00-2.09']
    assert outer['n'] == outer['goals_n'] == 1
    assert outer['avg_total_goals'] == 0
    assert outer['over_3_5_pct'] == 0


def test_goal_metrics_exclude_missing_invalid_ft_rows(tmp_path):
    import json
    from odds_scanner.research_v2_pattern_stats import build, SNAPSHOTS, RESULTS
    good = quote()
    good.update(fixture_id='valid', football_day='2026-09-29')
    missing = quote()
    missing.update(fixture_id='no_ft', football_day='2026-09-29')
    for path, rows in ((SNAPSHOTS, [good, missing]),
                       (RESULTS, [{'fixture_id': 'valid', 'ft_home_goals': 2, 'ft_away_goals': 2},
                                  {'fixture_id': 'no_ft', 'ft_home_goals': True, 'ft_away_goals': 1}])):
        file = tmp_path / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(''.join(json.dumps(item) + '\\n' for item in rows))
    report = build(tmp_path)
    assert report['settled_fixtures'] == 1
    row = report['over_under_2_5_by_ah_line_price'][0]
    assert row['goals_n'] == 1 and row['avg_total_goals'] == 4
    assert row['over_3_5_n'] == 1 and row['over_3_5_pct'] == 100
