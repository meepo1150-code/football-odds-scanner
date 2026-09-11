from odds_scanner.europe_discovery_summary import summarize


def test_summary_is_descriptive_and_never_promotion_eligible():
    targets=[
        {'country':'England','tournament_name':'Championship'},
        {'country':'Germany','tournament_name':'2. Bundesliga'},
    ]
    rows=[
        {'fixture_id':'1','observed_at':'2026-09-11T04:00:00+00:00','country':'England','league':'Championship','candidate_like_matches':['P1']},
        {'fixture_id':'1','observed_at':'2026-09-12T04:00:00+00:00','country':'England','league':'Championship','candidate_like_matches':[]},
        {'fixture_id':'2','observed_at':'2026-09-12T04:00:00+00:00','country':'England','league':'Championship','candidate_like_matches':['P1','P2']},
    ]
    report=summarize(rows,targets)
    assert report['classification']=='EUROPE_DISCOVERY_ONLY'
    assert report['production_promotion_allowed'] is False
    assert report['validation_gate_effect']=='NONE'
    assert report['observation_days']==2
    assert report['strict_observations']==3
    assert report['unique_fixtures']==2
    assert report['target_leagues']==2
    assert report['leagues_with_strict_observations']==1
    assert report['candidate_like_observations']==2
    assert report['candidate_like_hits']==3
    assert report['pattern_hits']=={'P1':2,'P2':1}
    coverage={(x['country'],x['league']):x for x in report['league_coverage']}
    assert coverage[('England','Championship')]['observations']==3
    assert coverage[('England','Championship')]['unique_fixtures']==2
    assert coverage[('Germany','2. Bundesliga')]['coverage_status']=='NO_STRICT_OBSERVATION_YET'


def test_summary_handles_empty_evidence_without_inventing_results():
    report=summarize([], [{'country':'Spain','tournament_name':'LaLiga 2'}])
    assert report['strict_observations']==0
    assert report['candidate_like_hits']==0
    assert report['leagues_with_strict_observations']==0
    assert report['league_coverage'][0]['coverage_status']=='NO_STRICT_OBSERVATION_YET'
