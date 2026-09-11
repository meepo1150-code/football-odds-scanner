from odds_scanner.europe_discovery_movement import summarize


def row(ts, *, fixture='1', ah_line=-0.5, ah_price=1.90, ou_line=2.5, over=1.95, under=1.85, candidates=None, favorite='H'):
    return {
        'fixture_id': fixture,
        'observed_at': ts,
        'country': 'England',
        'league': 'Championship',
        'home': 'A',
        'away': 'B',
        'kickoff': '2026-09-13T14:00:00+00:00',
        'favorite_side': favorite,
        'ah': {'selected_side_line': ah_line, 'selected_side_price': ah_price},
        'ou': {'line': ou_line, 'over_price': over, 'under_price': under},
        'candidate_like_matches': candidates or [],
    }


def test_requires_repeated_fixture_observations_for_movement():
    report = summarize([row('2026-09-11T04:47:00+00:00')])
    assert report['fixtures_seen'] == 1
    assert report['fixtures_with_repeated_observations'] == 0
    assert report['movement_rows'] == []
    assert report['production_promotion_allowed'] is False
    assert report['validation_gate_effect'] == 'NONE'


def test_first_vs_latest_tracks_exact_quarter_line_and_price_movement():
    report = summarize([
        row('2026-09-11T04:47:00+00:00', ah_line=-0.5, ah_price=1.96, ou_line=2.5, over=1.92, under=1.88, candidates=['P1']),
        row('2026-09-12T04:47:00+00:00', ah_line=-0.75, ah_price=1.87, ou_line=2.75, over=2.01, under=1.80, candidates=['P1','P2']),
    ])
    x = report['movement_rows'][0]
    assert x['ah']['opening_line'] == -0.5
    assert x['ah']['latest_line'] == -0.75
    assert x['ah']['line_delta'] == -0.25
    assert x['ah']['line_bucket'] == 'DOWN_.25'
    assert x['ah']['price_delta'] == -0.09
    assert x['ou']['line_delta'] == 0.25
    assert x['ou']['line_bucket'] == 'UP_.25'
    assert x['candidate_like_persisted'] == ['P1']
    assert x['candidate_like_appeared'] == ['P2']
    assert x['candidate_like_disappeared'] == []


def test_favorite_side_change_is_explicit_and_not_hidden():
    report = summarize([
        row('2026-09-11T04:47:00+00:00', favorite='H'),
        row('2026-09-12T04:47:00+00:00', favorite='A'),
    ])
    x = report['movement_rows'][0]
    assert x['favorite_side_changed'] is True
    assert x['favorite_side_open'] == 'H'
    assert x['favorite_side_latest'] == 'A'


def test_report_does_not_claim_true_opening_or_closing_semantics():
    report = summarize([
        row('2026-09-11T04:47:00+00:00'),
        row('2026-09-12T04:47:00+00:00'),
    ])
    assert report['source_semantics'] == 'FIRST_VS_LATEST_STRICT_DAILY_DISCOVERY_OBSERVATION'
    text = report['interpretation'].lower()
    assert 'not guaranteed to be bookmaker opening price' in text
    assert 'not guaranteed to be closing price' in text
    assert 'do not treat this report as clv' in text
