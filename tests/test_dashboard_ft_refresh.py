import json
from odds_scanner.dashboard_ft_refresh import refresh
from odds_scanner.research_v2_pattern_stats import SNAPSHOTS, RESULTS, OUTCOMES, REPORT, MISSING_LEDGER


def write_rows(root, path, rows):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(''.join(json.dumps(r) + '\n' for r in rows))


def snapshot(fid, day='2026-10-20'):
    return {'provider': 'propline', 'bookmaker': 'pinnacle', 'fixture_id': fid,
            'home': 'Home ' + fid, 'away': 'Away ' + fid,
            'mainline_verified': True, 'source_semantics': 'PROPLINE_PINNACLE_TWO_SIDED_CORE_MAINLINE',
            'observed_at': day + 'T08:00:00Z', 'kickoff': day + 'T20:00:00Z',
            'favorite_side': 'H', 'football_day': day,
            'ah': {'home_line': -.5, 'away_line': .5, 'home_price': 1.9, 'away_price': 2,
                   'selected_side_line': -.5, 'selected_side_price': 1.9}}


def test_new_scan_updates_denominator_without_losing_retained_ft(tmp_path):
    write_rows(tmp_path, SNAPSHOTS, [snapshot('settled')])
    write_rows(tmp_path, RESULTS, [{'fixture_id': 'settled', 'ft_home_goals': 1, 'ft_away_goals': 0}])
    refresh(tmp_path)
    old = (tmp_path / OUTCOMES).read_bytes()
    # Reproduce a partial result cache plus new-day snapshots: retain prior FT.
    write_rows(tmp_path, RESULTS, [])
    write_rows(tmp_path, SNAPSHOTS, [snapshot('settled'), snapshot('new')])
    raw = (tmp_path / SNAPSHOTS).read_bytes()
    stats = refresh(tmp_path)
    assert stats['settled_fixtures'] == 1
    assert stats['ft_completeness_denominator'] == 2
    assert stats['ft_completeness_pct'] == 50
    assert (tmp_path / OUTCOMES).read_bytes() == old
    assert (tmp_path / SNAPSHOTS).read_bytes() == raw
    ledger = json.loads((tmp_path / MISSING_LEDGER).read_text())
    assert ledger['missing_ft_count'] == 1
    assert ledger['fixtures'][0]['fixture_id'] == 'new'
    assert refresh(tmp_path)['ft_completeness_denominator'] == 2


def test_empty_snapshot_cache_does_not_replace_retained_statistics(tmp_path):
    write_rows(tmp_path, SNAPSHOTS, [snapshot('settled')])
    write_rows(tmp_path, RESULTS, [{'fixture_id': 'settled', 'ft_home_goals': 1, 'ft_away_goals': 0}])
    refresh(tmp_path)
    old = (tmp_path / REPORT).read_bytes()
    write_rows(tmp_path, SNAPSHOTS, [])
    assert refresh(tmp_path)['settled_fixtures'] == 1
    assert (tmp_path / REPORT).read_bytes() == old


def test_score_change_blocks_publication(tmp_path):
    import pytest
    write_rows(tmp_path, SNAPSHOTS, [snapshot('settled')])
    write_rows(tmp_path, RESULTS, [{'fixture_id': 'settled', 'ft_home_goals': 1, 'ft_away_goals': 0}])
    refresh(tmp_path)
    write_rows(tmp_path, RESULTS, [{'fixture_id': 'settled', 'ft_home_goals': 2, 'ft_away_goals': 0}])
    with pytest.raises(ValueError, match='score changed'):
        refresh(tmp_path)
