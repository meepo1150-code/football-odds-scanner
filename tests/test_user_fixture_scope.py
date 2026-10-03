from odds_scanner.research_population import EXCLUDED_FIXTURE_IDS, exclusion_reason, in_scope

def test_reviewed_18_ids_only():
    assert len(EXCLUDED_FIXTURE_IDS)==18
    for fid in EXCLUDED_FIXTURE_IDS:
        assert exclusion_reason({'fixture_id':fid})=='USER_REVIEWED_FIXTURE_OUT_OF_SCOPE'
    assert in_scope({'fixture_id':'pinnwire:future','league':'International - Friendlies','home':'Japan','away':'Ecuador'})
