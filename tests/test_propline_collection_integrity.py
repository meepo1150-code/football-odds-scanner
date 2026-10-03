from datetime import datetime, timedelta, timezone
import pytest
from odds_scanner import propline_research_v2 as collector


@pytest.mark.parametrize('offset,away_line,accepted', [(-1, .5, False), (1, .5, True), (1, .25, False)])
def test_collector_counts_only_integrity_accepted_snapshots(tmp_path, monkeypatch, offset, away_line, accepted):
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(collector, '_football_day', lambda _: (now-timedelta(days=1), now+timedelta(days=1), now.date().isoformat()))
    row = dict(sport='league', event_id='123', home='Home', away='Away', bookmaker='pinnacle', kickoff=(now+timedelta(hours=offset)).isoformat(), ah_home_line=-.5, ah_away_line=away_line, ah_home_odds=1.95, ah_away_odds=1.95)
    monkeypatch.setattr(collector, 'fetch', lambda: ([row], []))
    report = collector.run(tmp_path)
    assert report['strict_snapshots_this_run'] == int(accepted)
    assert report['quarantined_observations_this_run'] == int(not accepted)
    assert (tmp_path/collector.SNAPSHOT_PATH).exists() == accepted
