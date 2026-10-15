"""Offline regression: all four slots execute the same real collector path."""
import json
from datetime import datetime, timezone
from odds_scanner import europe_pinnacle_discovery as collector
from odds_scanner import research_v2_slot_recovery as recovery
from odds_scanner.research_v2_slots import targets, collection_snapshot
from test_collector_observation_contract import setup


def test_four_slots_collect_append_only_and_duplicate_wakeups_are_free(tmp_path, monkeypatch):
    clock, fixture = setup(tmp_path, monkeypatch, now='2026-10-14T08:03:00+00:00')
    fixture['startTime'] = '2026-10-14T20:00:00Z'
    target_path = tmp_path/collector.TARGET_PATH
    target_path.write_text(json.dumps({'tournaments': [
        {'tournament_id': 17, 'country': 'England', 'tournament_name': 'Premier League'}]}))
    monkeypatch.delenv('RESEARCH_QUOTA_DURABLE', raising=False)
    monkeypatch.setattr(recovery, 'primary', collector.run)
    monkeypatch.setattr(recovery, 'fallback', lambda *a, **kw: (_ for _ in ()).throw(AssertionError('primary must complete')))
    calls = []
    def get(endpoint, *args):
        calls.append(endpoint)
        return {} if endpoint == '/account' else [fixture]
    monkeypatch.setattr(collector, '_get', get)
    preserved = b''
    for target in targets('2026-10-14'):
        clock.current = target.astimezone(timezone.utc).replace(minute=3)
        reports = recovery.run(tmp_path, clock.current)
        assert reports[0]['status'] == 'RESEARCH_V2_OBSERVED'
        data = (tmp_path/collector.SNAPSHOT_PATH).read_bytes()
        assert data.startswith(preserved)
        preserved = data
        rows = [json.loads(line) for line in data.splitlines()]
        assert collection_snapshot(rows[-1])
        assert datetime.fromisoformat(rows[-1]['scheduled_target_at']) == target
        assert rows[-1]['observed_at'] == clock.current.isoformat()
        assert rows[-1]['football_day'] == '2026-10-14'
        before = len(calls)
        assert recovery.run(tmp_path, clock.current) == []
        assert len(calls) == before
    assert len(rows) == 4
    assert calls.count('/odds-by-tournaments') == 4
