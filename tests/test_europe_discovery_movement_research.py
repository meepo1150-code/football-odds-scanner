from odds_scanner.europe_discovery_movement_research import summarize


def movement(*, fixture='1', first=None, latest=None, persisted=None, appeared=None, disappeared=None, ah='FLAT', ou='FLAT', changed=False, league='Championship'):
    return {
        'fixture_id': fixture,
        'country': 'England',
        'league': league,
        'candidate_like_open': first or [],
        'candidate_like_latest': latest or [],
        'candidate_like_persisted': persisted or [],
        'candidate_like_appeared': appeared or [],
        'candidate_like_disappeared': disappeared or [],
        'favorite_side_changed': changed,
        'ah': {'line_bucket': ah},
        'ou': {'line_bucket': ou},
    }


def test_empty_research_is_non_promotional():
    report = summarize({'movement_rows': []})
    assert report['repeated_fixtures'] == 0
    assert report['candidate_patterns_observed'] == 0
    assert report['candidate_pattern_movement'] == []
    assert report['production_promotion_allowed'] is False
    assert report['validation_gate_effect'] == 'NONE'
    assert report['outcome_or_roi_used'] is False


def test_candidate_persistence_appearance_disappearance_and_buckets():
    report = summarize({
        'source_semantics': 'FIRST_VS_LATEST_STRICT_DAILY_DISCOVERY_OBSERVATION',
        'movement_rows': [
            movement(fixture='1', first=['P1'], latest=['P1'], persisted=['P1'], ah='DOWN_.25', ou='FLAT'),
            movement(fixture='2', first=['P1'], latest=[], disappeared=['P1'], ah='FLAT', ou='UP_.25', changed=True),
            movement(fixture='3', first=[], latest=['P1', 'P2'], appeared=['P1', 'P2'], ah='UP_.25', ou='DOWN_.25', league='Serie B'),
        ],
    })
    assert report['repeated_fixtures'] == 3
    assert report['candidate_patterns_observed'] == 2
    p1 = next(x for x in report['candidate_pattern_movement'] if x['candidate_id'] == 'P1')
    assert p1['repeated_fixtures_touched'] == 3
    assert p1['first_observed_hits'] == 2
    assert p1['latest_observed_hits'] == 2
    assert p1['persisted'] == 1
    assert p1['appeared'] == 1
    assert p1['disappeared'] == 1
    assert p1['persistence_rate_among_first_observed_hits'] == 0.5
    assert p1['favorite_side_changed'] == 1
    assert p1['ah_line_buckets'] == {'DOWN_.25': 1, 'FLAT': 1, 'UP_.25': 1}
    assert p1['ou_line_buckets'] == {'DOWN_.25': 1, 'FLAT': 1, 'UP_.25': 1}
    assert p1['league_counts']['England · Championship'] == 2
    assert p1['league_counts']['England · Serie B'] == 1
    p2 = next(x for x in report['candidate_pattern_movement'] if x['candidate_id'] == 'P2')
    assert p2['appeared'] == 1
    assert p2['persistence_rate_among_first_observed_hits'] is None


def test_overall_buckets_include_non_candidate_repeated_fixtures():
    report = summarize({'movement_rows': [
        movement(fixture='1', ah='FLAT', ou='UP_.25'),
        movement(fixture='2', first=['P1'], latest=['P1'], persisted=['P1'], ah='DOWN_.25', ou='FLAT'),
    ]})
    assert report['overall_ah_line_buckets'] == {'DOWN_.25': 1, 'FLAT': 1}
    assert report['overall_ou_line_buckets'] == {'FLAT': 1, 'UP_.25': 1}
