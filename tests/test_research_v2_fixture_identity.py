import copy
import json
import hashlib
from odds_scanner.research_v2_fixture_identity import build_bridge, project
from odds_scanner.research_v2_pattern_stats import build, SNAPSHOTS, RESULTS
from odds_scanner.research_v2_movement import run


def pair():
    base=dict(home='Germany',away='Serbia',kickoff='2026-10-01T18:45:00+00:00',football_day='2026-10-01',
              bookmaker='pinnacle',favorite_side='H',observed_at='2026-10-01T09:00:00+00:00',
              ah=dict(home_line=-1.5,away_line=1.5,home_price=1.9,away_price=2.0,selected_side_line=-1.5,selected_side_price=1.9),
              ou=dict(line=2.5,over_price=1.9,under_price=2.0))
    a=dict(base,fixture_id='pinnwire:1',provider='pinnwire',league='UEFA - Nations League A',source_semantics='PINNWIRE_PREMATCH_FULL_SNAPSHOT')
    b=dict(copy.deepcopy(base),fixture_id='propline:2',provider='propline',league='soccer_uefa_nations_league',observed_at='2026-10-01T11:00:00+00:00',mainline_verified=True,source_semantics='PROPLINE_PINNACLE_TWO_SIDED_CORE_MAINLINE')
    b['ah'].update(home_line=-.75,away_line=.75,selected_side_line=-.75)
    return [a,b]


def write(root,rows,results,conflicts=()):
    for path,data in [(SNAPSHOTS,rows),(RESULTS,results),(RESULTS.with_suffix('.conflicts.jsonl'),conflicts)]:
        p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(''.join(json.dumps(r)+'\n' for r in data))


def test_bridge_is_derived_preserves_source_and_raw():
    rows=pair();original=copy.deepcopy(rows);mapping,evidence=build_bridge(rows)
    assert evidence['bridged_matches']==1
    assert mapping=={'pinnwire:1':'pinnwire:1','propline:2':'pinnwire:1'}
    assert project(rows,mapping)[1]['source_fixture_id']=='propline:2'
    assert rows==original


def test_identity_requires_exact_teams_time_competition_and_unique_id():
    for key,val in [('away','Serbia U21'),('home','Germany Women'),('kickoff','2026-10-01T18:46:00+00:00'),('league','UEFA - U21 Championship'),('bookmaker','other')]:
        rows=pair();rows[1][key]=val;assert build_bridge(rows)[0]=={}
    rows=pair();duplicate=dict(rows[0],fixture_id='pinnwire:3');assert not build_bridge(rows+[duplicate])[0]
    rows=pair();changed=dict(rows[0],away='Other');assert not build_bridge(rows+[changed])[0]
    rows=pair();rows[1]['mainline_verified']=False;assert not build_bridge(rows)[0]


def test_unique_settlement_and_cross_feed_movement(tmp_path):
    rows=pair();result=[dict(fixture_id=r['fixture_id'],ft_home_goals=1,ft_away_goals=0) for r in rows]
    write(tmp_path,rows,result);before=(tmp_path/SNAPSHOTS).read_bytes()
    stats=build(tmp_path);movement=run(tmp_path)
    assert stats['settled_fixtures']==1
    assert stats['core_price_settled_fixtures']==1
    assert stats['market_state_by_side_line_price'][0]['half_win']==1
    assert stats['over_under_2_5_by_ah_line_price'][0]['n']==1
    assert stats['provider_fixture_ids']==2
    assert movement['fixtures_with_two_plus_snapshots']==0
    assert movement['classification_counts']=={'SOURCE_SWITCH__INSUFFICIENT_OBSERVATIONS':1}
    assert (tmp_path/SNAPSHOTS).read_bytes()==before


def test_result_on_either_id_and_conflicts_fail_closed(tmp_path):
    rows=pair()
    for fid in ('pinnwire:1','propline:2'):
        write(tmp_path,rows,[dict(fixture_id=fid,ft_home_goals=1,ft_away_goals=0)])
        assert build(tmp_path)['settled_fixtures']==1
    write(tmp_path,rows,[dict(fixture_id='pinnwire:1',ft_home_goals=1,ft_away_goals=0),dict(fixture_id='propline:2',ft_home_goals=2,ft_away_goals=0)])
    diagnostics=build(tmp_path)
    from odds_scanner.research_v2_pattern_stats import _rows, _result_index
    m,_=build_bridge(_rows(tmp_path/SNAPSHOTS))
    direct,ambiguous=_result_index(project(_rows(tmp_path/RESULTS),m))
    assert diagnostics['settled_fixtures']==0, (
        len(_rows(tmp_path/SNAPSHOTS)), len(_rows(tmp_path/RESULTS)),
        len(m),len(direct),len(ambiguous))

    write(tmp_path,rows,[dict(fixture_id='pinnwire:1',ft_home_goals=1,ft_away_goals=0)],[dict(fixture_id='propline:2')])
    diagnostics=build(tmp_path)
    from odds_scanner.research_v2_pattern_stats import _rows, _result_index
    m,_=build_bridge(_rows(tmp_path/SNAPSHOTS))
    direct,ambiguous=_result_index(project(_rows(tmp_path/RESULTS),m))
    assert diagnostics['settled_fixtures']==0, (
        len(_rows(tmp_path/SNAPSHOTS)), len(_rows(tmp_path/RESULTS)),
        len(m),len(direct),len(ambiguous))


def native_and_fallback():
    r=pair()[0]
    r.update(fixture_id='pinnwire:123',provider_fixture_id='123')
    digest=hashlib.sha1(f"{r['home']}|{r['away']}|{r['kickoff']}".encode()).hexdigest()[:16]
    return [r,dict(copy.deepcopy(r),fixture_id='pinnwire:'+digest,provider_fixture_id=digest)]


def test_reproduced_fallback_alias_is_derived_and_settles_once(tmp_path):
    rows=native_and_fallback();original=copy.deepcopy(rows)
    mapping,evidence=build_bridge(rows)
    assert mapping[rows[1]['fixture_id']]=='pinnwire:123'
    assert evidence['bridges'][0]['policy']=='REPRODUCED_PINNWIRE_FALLBACK_HASH_AND_UNIQUE_NATIVE_ID'
    write(tmp_path,rows,[dict(fixture_id=rows[1]['fixture_id'],ft_home_goals=1,ft_away_goals=0)])
    stats=build(tmp_path)
    assert stats['settled_fixtures']==1
    assert stats['verified_cross_provider_canonical_fixtures']==0
    assert stats['verified_same_provider_duplicate_fixtures']==1
    outcome=json.loads((tmp_path/'data/normalized/research_v2_pattern_outcomes.jsonl').read_text())
    assert outcome['result_join']=='VERIFIED_PROVIDER_FALLBACK_ALIAS'
    assert rows==original
    write(tmp_path,rows,[dict(fixture_id=r['fixture_id'],ft_home_goals=i,ft_away_goals=0) for i,r in enumerate(rows)])
    diagnostics=build(tmp_path)
    from odds_scanner.research_v2_pattern_stats import _rows, _result_index
    m,_=build_bridge(_rows(tmp_path/SNAPSHOTS))
    direct,ambiguous=_result_index(project(_rows(tmp_path/RESULTS),m))
    assert diagnostics['settled_fixtures']==0, (
        len(_rows(tmp_path/SNAPSHOTS)), len(_rows(tmp_path/RESULTS)),
        len(m),len(direct),len(ambiguous))


def test_same_teams_different_date_reschedule_and_unproven_ids_remain_unmatched():
    for key,value in [('kickoff','2026-10-02T18:45:00+00:00'),('away','Other'),
                      ('provider_fixture_id','unverified'),('fixture_id','pinnwire:456')]:
        rows=native_and_fallback();rows[1][key]=value
        assert not build_bridge(rows)[0]
    rows=native_and_fallback();changed=dict(rows[0],kickoff='2026-10-02T18:45:00+00:00')
    mapping,evidence=build_bridge(rows+[changed])
    assert not mapping and any(r['reason']=='INCONSISTENT_IDENTITY' for r in evidence['rejected'])


def test_ft_cannot_settle_reused_provider_id_across_two_match_dates(tmp_path):
    rows=native_and_fallback()[:1]
    rows.append(dict(rows[0],kickoff='2026-10-02T18:45:00+00:00'))
    write(tmp_path,rows,[dict(fixture_id='pinnwire:123',ft_home_goals=0,ft_away_goals=0)])
    stats=build(tmp_path)
    assert stats['settled_fixtures']==0 and stats['identity_conflict_ft_fixtures']==1
