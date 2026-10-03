import json
from pathlib import Path

from odds_scanner.europe_pinnacle_discovery import BATCH_SIZE, _chunks, _merge_jsonl


def test_merge_snapshots_deduplicates_fixture_observation(tmp_path: Path):
    path = tmp_path / 'snapshots.jsonl'
    first = {'fixture_id':'1','observed_at':'2026-09-11T00:00:00+00:00','bookmaker':'pinnacle'}
    second = {'fixture_id':'2','observed_at':'2026-09-11T00:00:00+00:00','bookmaker':'pinnacle'}
    assert _merge_jsonl(path, [first, second], ('observed_at', 'fixture_id')) == 2
    assert _merge_jsonl(path, [first], ('observed_at', 'fixture_id')) == 2
    rows = [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines()]
    assert len(rows) == 2
    assert {x['fixture_id'] for x in rows} == {'1','2'}


def test_oddspapi_tournament_batches_never_exceed_provider_safe_limit():
    assert BATCH_SIZE == 5
    batches = list(_chunks(list(range(54)), BATCH_SIZE))
    assert len(batches) == 11
    assert max(map(len, batches)) <= 5
