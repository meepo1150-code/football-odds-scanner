import json
from pathlib import Path

from odds_scanner.europe_pinnacle_discovery import merge_snapshots


def test_merge_snapshots_deduplicates_fixture_observation(tmp_path: Path):
    path = tmp_path / 'snapshots.jsonl'
    first = {'fixture_id':'1','observed_at':'2026-09-11T00:00:00+00:00','bookmaker':'pinnacle'}
    second = {'fixture_id':'2','observed_at':'2026-09-11T00:00:00+00:00','bookmaker':'pinnacle'}
    assert merge_snapshots(path, [first, second]) == 2
    assert merge_snapshots(path, [first]) == 2
    rows = [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines()]
    assert len(rows) == 2
    assert {x['fixture_id'] for x in rows} == {'1','2'}
