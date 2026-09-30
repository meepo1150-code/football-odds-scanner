from copy import deepcopy
import json
from odds_scanner.legacy_propline_recovery import recover, build, SNAPSHOTS, RECOVERED, REPORT


def quote():
    return {'provider': 'propline', 'fixture_id': 'propline:test:1', 'home': 'A', 'away': 'B', 'league': 'test', 'kickoff': '2026-09-29T18:00:00Z', 'observed_at': '2026-09-29T16:59:00Z', 'bookmaker': 'pinnacle', 'mainline_verified': True, 'source_semantics': 'PROPLINE_PINNACLE_TWO_SIDED_CORE_MAINLINE', 'favorite_side': 'H', 'ah': {'home_line': -.5, 'away_line': .5, 'home_price': 1.9, 'away_price': 2.0, 'selected_side_line': -.5, 'selected_side_price': 1.9}}


def legacy():
    row = quote()
    row.pop('mainline_verified')
    row.pop('source_semantics')
    row['observed_at'] = '2026-09-29T17:00:00Z'
    row['ah']['home_price'] = row['ah']['selected_side_price'] = 4.0
    return row


def test_recovery_preserves_original_and_actual_quote_time():
    old = legacy()
    before = deepcopy(old)
    audit, staged = recover(old, [(quote(), 'archive')])
    assert old == before
    assert audit['status'] == 'RECOVERED_STAGED'
    assert staged['replacement_snapshot']['observed_at'] == '2026-09-29T16:59:00Z'
    assert staged['provenance']['age_seconds'] == 60
    assert staged['replacement_snapshot']['ah']['home_price'] == 1.9


def test_no_later_price_reconstruction():
    row = quote(); row['observed_at'] = '2026-09-29T17:01:00Z'
    audit, staged = recover(legacy(), [(row, 'archive')])
    assert staged is None
    assert audit['rejection_counts']['LATER_QUOTE_CANNOT_RECONSTRUCT_PAST'] == 1


def test_stale_history_is_rejected():
    row = quote(); row['observed_at'] = '2026-09-29T16:00:00Z'
    assert recover(legacy(), [(row, 'archive')])[1] is None


def test_ambiguous_quotes_remain_quarantined():
    a, b = quote(), quote()
    b['ah']['home_price'] = b['ah']['selected_side_price'] = 1.95
    audit, staged = recover(legacy(), [(a, 'a'), (b, 'b')])
    assert audit['status'] == 'AMBIGUOUS' and staged is None


def test_exact_id_cannot_override_conflicting_metadata():
    for key in ('home', 'away', 'league', 'kickoff'):
        row = quote(); row[key] = 'conflict'
        assert recover(legacy(), [(row, 'archive')])[1] is None


def test_exact_identity_bridge_requires_all_fields():
    row = quote(); row['fixture_id'] = 'other:1'
    assert recover(legacy(), [(row, 'archive')])[1]['provenance']['identity_method'] == 'EXACT_TEAMS_LEAGUE_KICKOFF_BRIDGE'
    row['league'] = None
    assert recover(legacy(), [(row, 'archive')])[1] is None


def test_invalid_semantics_bookmaker_pair_and_prices_rejected():
    for key, value in [('bookmaker', 'bet365'), ('mainline_verified', False), ('source_semantics', 'PINNWIRE_PREMATCH_FULL_SNAPSHOT')]:
        row = quote(); row[key] = value
        assert recover(legacy(), [(row, 'archive')])[1] is None
    for key, value in [('away_price', None), ('home_price', float('nan')), ('away_line', -.5), ('selected_side_price', 4.0), ('home_line', -.3)]:
        row = quote(); row['ah'][key] = value
        assert recover(legacy(), [(row, 'archive')])[1] is None


def test_build_is_deterministic_and_never_edits_canonical(tmp_path):
    path = tmp_path / SNAPSHOTS; path.parent.mkdir(parents=True)
    raw = json.dumps(legacy()) + '\n'
    path.write_text(raw)
    report = build(tmp_path)
    first = (tmp_path / REPORT).read_bytes()
    assert report['total_legacy_observations'] == report['still_quarantined'] == report['unavailable'] == 1
    assert report['recovered'] == report['promoted'] == 0
    assert (tmp_path / RECOVERED).read_text() == ''
    build(tmp_path)
    assert (tmp_path / REPORT).read_bytes() == first
    assert path.read_text() == raw
