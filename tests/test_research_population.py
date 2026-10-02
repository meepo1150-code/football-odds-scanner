import pytest
from odds_scanner.research_population import in_scope, exclusion_reason


@pytest.mark.parametrize('league', ['Israel - Premier League Women', 'soccer_womens_super_league', 'Sweden - Damallsvenskan', 'FIFA - World Cup U20 Women', 'UEFA - U21 Euro Championship Qualifiers', 'Asian Games U23', 'China - U20 League', 'Under-19', 'Primavera'])
def test_excluded(league):
    assert not in_scope({'league': league})


@pytest.mark.parametrize('league', ['Premier League', 'Argentina - Reserve League', 'Mongolia - Premier League', 'League 2', 'UEFA Nations League'])
def test_preserved(league):
    assert in_scope({'league': league})


def test_team_age_suffix_and_reason():
    assert exclusion_reason({'home': 'Arsenal U21'}) == 'YOUTH_OUT_OF_SCOPE'
    assert exclusion_reason({'league': 'Women U19'}) == 'WOMEN_OUT_OF_SCOPE'


def test_scope_rebuild_preserves_raw_results_and_quarantine(tmp_path):
    import json
    from odds_scanner.research_v2_pattern_stats import build, SNAPSHOTS, RESULTS
    from odds_scanner.result_recovery_lifecycle import review
    from datetime import datetime, timezone
    snapshots=[]
    for fid,league in [('senior','Premier League'),('women','Women League'),('youth','U21 League')]:
        snapshots.append({'fixture_id':fid,'provider':'pinnwire','league':league,'home':'Home','away':'Away','kickoff':'2026-09-20T12:00:00Z','observed_at':'2026-09-20T10:00:00Z','favorite_side':'H','ah':{'selected_side_line':-.5,'selected_side_price':1.9}})
    (tmp_path/SNAPSHOTS).parent.mkdir(parents=True)
    (tmp_path/SNAPSHOTS).write_text(''.join(json.dumps(r)+'\n' for r in snapshots))
    (tmp_path/RESULTS).write_text(''.join(json.dumps({'fixture_id':s['fixture_id'],'ft_home_goals':1,'ft_away_goals':0})+'\n' for s in snapshots))
    raw=(tmp_path/SNAPSHOTS).read_bytes();results=(tmp_path/RESULTS).read_bytes()
    report=build(tmp_path)
    assert report['settled_fixtures']==1
    assert report['scope_excluded_snapshot_rows']==2
    assert report['quarantined_snapshot_rows']==0
    assert report['raw_snapshot_rows']==3
    assert (tmp_path/SNAPSHOTS).read_bytes()==raw and (tmp_path/RESULTS).read_bytes()==results
    (tmp_path/RESULTS).write_text('')
    assert review(tmp_path,datetime(2026,9,25,tzinfo=timezone.utc))['active_matured_unresolved']==1
