import copy
import json
from pathlib import Path

import pytest
import yaml

from odds_scanner.historical_manual import planner, runner
from odds_scanner.historical_manual.replay_cache import replay
from odds_scanner.historical_manual.safety import StopPilot
from scripts.publish_manual_historical import RUNTIME_STOP, produce
from test_manual_historical import NOW, native, source, payload

URL = 'https://github.com/meepo1150-code/football-odds-scanner/actions/runs/39094936689'


def setup(root):
    source(root, [native('id123'), native('id124'), native('id125')])
    manifest = planner.build(root, '2026-09-14', '2026-09-14',
                             '15:00,18:00,21:00,00:00', 'pinnacle', NOW)
    cache = root/runner.CACHE
    for c in manifest['candidates'][:2]:
        runner.cache_store(cache, c, 200, json.dumps(payload(c['fixture_id'])).encode(), NOW)
    first = manifest['candidates'][0]
    report = dict(status='STOPPED', errors=[RUNTIME_STOP], run_url=URL,
                  production_writes=0, research_only=True, historical_requests=1,
                  results=[runner.reconstruct(first, payload(first['fixture_id']),
                           json.loads(runner.CATALOG.read_text()))])
    return report, manifest, cache


def test_replays_preexisting_cache_even_when_fetch_loop_stopped(tmp_path, monkeypatch):
    report, manifest, cache = setup(tmp_path)
    before = copy.deepcopy((report, manifest))
    originals = {p:p.read_bytes() for p in cache.rglob('*.json')}
    monkeypatch.setattr('urllib.request.urlopen', lambda *a, **kw: pytest.fail('NO HTTP ALLOWED'))
    result = replay(report, manifest, cache, expected_run_url=URL)
    assert result['status'] == 'STOPPED' and result['errors'] == [RUNTIME_STOP]
    assert result['historical_requests'] == 1  # Preserve the original accounting.
    assert result['offline_cache_replay']['provider_requests'] == 0
    assert result['offline_cache_replay']['additional_processed_pairs'] == 1
    assert result['offline_cache_replay']['available_cached_pairs'] == 2
    assert result['offline_cache_replay']['unprocessed_pairs'] == 1
    assert result['slot_status_counts'] == {'BALANCED_LINE':8}
    incoming, _ = produce(result, manifest, [], allow_runtime_partial=True)
    assert len(incoming) == 8
    assert (report, manifest) == before
    assert all(p.read_bytes() == raw for p,raw in originals.items())
    assert replay(result, manifest, cache, expected_run_url=URL)['results'] == result['results']


def test_corrupt_saved_raw_is_blocked_not_silently_published(tmp_path):
    report, manifest, cache = setup(tmp_path)
    c = manifest['candidates'][1]
    index = cache/'cache'/(runner.digest(c['request'])+'.json')
    raw_path = cache/'raw'/(json.loads(index.read_text())['raw_sha256']+'.json')
    raw_path.write_bytes(b'{}')
    with pytest.raises(StopPilot, match='CACHE_HASH_MISMATCH'):
        replay(report, manifest, cache, expected_run_url=URL)


def test_cache_before_requested_target_is_not_reused(tmp_path):
    report, manifest, cache = setup(tmp_path)
    c = manifest['candidates'][1]
    index = cache/'cache'/(runner.digest(c['request'])+'.json')
    receipt = json.loads(index.read_text())
    receipt['fetched_at'] = '2026-09-14T08:00:00Z'
    index.write_text(json.dumps(receipt))
    result = replay(report, manifest, cache, expected_run_url=URL)
    assert len(result['results']) == 1
    assert result['offline_cache_replay']['additional_processed_pairs'] == 0


@pytest.mark.parametrize('errors', [['PRODUCTION_POSTCHECK_FAILED'],
    [RUNTIME_STOP,'RESEARCH_QUOTA_OR_SUBSCRIPTION_CHANGED']])
def test_other_stop_reasons_are_blocked(tmp_path, errors):
    report, manifest, cache = setup(tmp_path)
    report['errors'] = errors
    with pytest.raises(ValueError, match='CACHE_REPLAY_REQUIRES_RUNTIME_STOP'):
        replay(report, manifest, cache, expected_run_url=URL)


def test_replay_rejects_wrong_source_run(tmp_path):
    report, manifest, cache = setup(tmp_path)
    with pytest.raises(ValueError, match='HISTORICAL_ARTIFACT_RUN_MISMATCH'):
        replay(report, manifest, cache, expected_run_url=URL+'0')


def test_workflow_restores_only_exact_source_cache_before_reconstruction():
    w = yaml.safe_load(Path('.github/workflows/publish-retained-historical.yml').read_text())
    steps = w['jobs']['publish']['steps']
    restore = next(s for s in steps if s.get('id') == 'saved_cache')
    assert restore['with']['key'] == '${{ steps.source.outputs.cache_key }}'
    assert 'restore-keys' not in restore['with']
    replay_step = next(s for s in steps if 'replay_cache' in s.get('run',''))
    assert 'test "$MATCHED_CACHE_KEY" = "$SOURCE_CACHE_KEY"' in replay_step['run']
    assert steps.index(restore) < steps.index(replay_step)
    commands = '\n'.join(s.get('run','') for s in steps)
    assert 'historical_manual.runner' not in commands
    assert 'secrets.' not in str(w)
    assert commands.count('--artifact-dir "$ARTIFACT_DIR"') == 2
