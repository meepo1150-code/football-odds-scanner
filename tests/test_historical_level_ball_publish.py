"""Historical AH zero uses the verified slot prices, with no provider calls."""
import copy
import json

import pytest

from scripts.publish_manual_historical import produce, publish, SNAPSHOTS, RUNTIME_STOP


def artifact(home=1.9, away=2.1):
    c = dict(fixture_id='verified-id', bookmaker='pinnacle', home='Home', away='Away',
             league='League', kickoff='2026-09-10T18:00:00Z', football_day='2026-09-10',
             evidence=[dict(mapping_source='ODDSPAPI_EXACT',
                            evidence_url='https://example.org/verified')],
             targets=[dict(target_utc='2026-09-10T08:00:00Z')])
    selected = dict(line_selection='BALANCED_LINE', market='AH',
                    official_mainline_verified=False, fixture_id=c['fixture_id'],
                    bookmaker=c['bookmaker'], slot_utc=c['targets'][0]['target_utc'],
                    market_id='ah-zero', home_line=0, away_line=0,
                    raw_record_hash='retained-raw-sha256',
                    quotes={side:dict(active=True, price=price,
                                     quote_at_utc='2026-09-10T07:59:00Z')
                            for side, price in [('home', home), ('away', away)]})
    result = {k:c[k] for k in ('fixture_id','bookmaker','home','away','kickoff','football_day')}
    result['slots'] = [dict(target_utc=c['targets'][0]['target_utc'],
                            status='BALANCED_LINE', selected=selected)]
    report = dict(status='COMPLETED', errors=[], production_writes=0, research_only=True,
                  run_url='https://github.com/example/repo/actions/runs/15', results=[result])
    manifest = dict(scope='VERIFIED_NATIVE_OR_EXTERNAL_ODDSPAPI_FIXTURES', candidates=[c])
    return report, manifest


@pytest.mark.parametrize('home,away,favorite', [(1.9,2.1,'H'), (2.1,1.9,'A')])
@pytest.mark.parametrize('has_original', [False, True])
def test_level_ball_uses_slot_price_even_with_opposite_cohort_favorite(home, away, favorite, has_original):
    report, manifest = artifact(home, away)
    original = [{**manifest['candidates'][0], 'favorite_side':'A' if favorite=='H' else 'H'}] if has_original else []
    before = copy.deepcopy((report, manifest, original))
    incoming, counts = produce(report, manifest, original)
    row, = incoming.values()
    assert row['favorite_side'] == favorite
    assert row['favorite_side_basis'] == 'HISTORICAL_LEVEL_BALL_LOWER_DECIMAL_PRICE'
    assert row['ah']['selected_side_price'] == min(home, away)
    assert row['ah']['selected_side_line'] == 0
    assert row['observed_at'] == '2026-09-10T07:59:00+00:00'
    assert row['mainline_verified'] is False and row['promotion_eligible'] is False
    assert counts['BALANCED_LINE'] == 1
    assert (report, manifest, original) == before


def test_equal_price_skips_only_that_slot():
    report, manifest = artifact(2, 2)
    valid = copy.deepcopy(report['results'][0]['slots'][0])
    valid['target_utc'] = valid['selected']['slot_utc'] = '2026-09-10T08:01:00Z'
    valid['selected']['quotes']['away']['price'] = 2.1
    manifest['candidates'][0]['targets'].append(dict(target_utc=valid['target_utc']))
    report['results'][0]['slots'].append(valid)
    incoming, counts = produce(report, manifest, [])
    assert len(incoming) == 1
    assert counts['LEVEL_BALL_EQUAL_PRICE_SKIPPED'] == 1


@pytest.mark.parametrize('field,value,error', [
    ('price',1.79,'INVALID_QUOTE'), ('active',False,'INVALID_QUOTE'),
    ('quote_at_utc','2026-09-10T08:01:00Z','QUOTE_TIMESTAMP_OUT_OF_RANGE')])
def test_lower_price_rule_does_not_bypass_quote_gates(field, value, error):
    report, manifest = artifact()
    report['results'][0]['slots'][0]['selected']['quotes']['home'][field] = value
    with pytest.raises(ValueError, match=error):
        produce(report, manifest, [])


def test_replaying_artifact_is_idempotent_and_preserves_live_rows(tmp_path):
    report, manifest = artifact()
    live = {**manifest['candidates'][0], 'favorite_side':'A', 'observed_at':'2026-09-10T07:00:00Z'}
    path = tmp_path/SNAPSHOTS
    path.parent.mkdir(parents=True)
    raw = json.dumps(live)+'\n'
    path.write_text(raw)
    assert publish(report, manifest, tmp_path)['added'] == 1
    first = path.read_bytes()
    assert first.startswith(raw.encode())
    replay = publish(report, manifest, tmp_path)
    assert replay['added'] == 0 and replay['unchanged'] == 1
    assert replay['api_requests'] == 0
    assert path.read_bytes() == first


def partial_artifact():
    report, manifest = artifact()
    report.update(status='STOPPED', errors=[RUNTIME_STOP])
    pending = copy.deepcopy(manifest['candidates'][0])
    pending['fixture_id'] = 'not-yet-processed'
    manifest['candidates'].append(pending)
    return report, manifest


def test_runtime_partial_requires_explicit_opt_in():
    report, manifest = partial_artifact()
    with pytest.raises(ValueError, match='SCAN_NOT_COMPLETED'):
        produce(report, manifest, [])
    incoming, _ = produce(report, manifest, [], allow_runtime_partial=True)
    assert len(incoming) == 1
    assert report['status'] == 'STOPPED' and report['errors'] == [RUNTIME_STOP]


@pytest.mark.parametrize('errors', [[], ['HISTORY_HTTP_429_STOP_NO_RETRY'],
    ['RESEARCH_QUOTA_OR_SUBSCRIPTION_CHANGED'], [RUNTIME_STOP, 'PRODUCTION_POSTCHECK_FAILED']])
def test_partial_rejects_other_failure_reasons(errors):
    report, manifest = partial_artifact()
    report['errors'] = errors
    with pytest.raises(ValueError, match='SCAN_NOT_COMPLETED'):
        produce(report, manifest, [], allow_runtime_partial=True)


def test_partial_rejects_duplicate_results():
    report, manifest = partial_artifact()
    report['results'] *= 2
    with pytest.raises(ValueError, match='DUPLICATE_RESULT'):
        produce(report, manifest, [], allow_runtime_partial=True)


def test_partial_still_requires_every_target_for_processed_fixture():
    report, manifest = partial_artifact()
    manifest['candidates'][0]['targets'].append(dict(target_utc='2026-09-10T09:00:00Z'))
    with pytest.raises(ValueError, match='SLOT_MANIFEST_MISMATCH'):
        produce(report, manifest, [], allow_runtime_partial=True)


def test_partial_receipt_is_honest_and_replay_is_idempotent(tmp_path):
    report, manifest = partial_artifact()
    p = tmp_path/SNAPSHOTS
    p.parent.mkdir(parents=True)
    p.touch()
    receipt = publish(report, manifest, tmp_path, allow_runtime_partial=True)
    assert receipt['status'] == 'PARTIAL_PROMOTED'
    assert receipt['source_scan_status'] == 'STOPPED'
    assert receipt['processed_candidate_pairs'] == 1
    assert receipt['unprocessed_candidate_pairs'] == 1
    assert receipt['api_requests'] == 0
    first = p.read_bytes()
    replay = publish(report, manifest, tmp_path, allow_runtime_partial=True)
    assert replay['status'] == 'PARTIAL_NO_NEW_ROWS'
    assert replay['unchanged'] == 1 and p.read_bytes() == first


def test_partial_cli_requires_source_run_binding(tmp_path, monkeypatch):
    from scripts.publish_manual_historical import main
    report, manifest = partial_artifact()
    (tmp_path/'report.json').write_text(json.dumps(report))
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    monkeypatch.setattr('sys.argv', ['publish', '--artifact-dir', str(tmp_path), '--allow-runtime-partial'])
    with pytest.raises(ValueError, match='PARTIAL_PUBLICATION_REQUIRES_SOURCE_RUN'):
        main()
    monkeypatch.setattr('sys.argv', ['publish', '--artifact-dir', str(tmp_path), '--allow-runtime-partial',
                                    '--expected-run-url', 'https://github.com/wrong/repo/actions/runs/16'])
    with pytest.raises(ValueError, match='HISTORICAL_ARTIFACT_RUN_MISMATCH'):
        main()


def test_replay_workflow_has_no_collector_and_requires_main():
    from pathlib import Path
    import yaml
    w = yaml.safe_load(Path('.github/workflows/publish-retained-historical.yml').read_text())
    job = w['jobs']['publish']
    assert job['if'] == "github.ref == 'refs/heads/main'"
    commands = '\n'.join(s.get('run','') for s in job['steps'])
    assert 'manual-historical-scan.yml' in commands
    assert '--expected-run-url' in commands and '--allow-runtime-partial' in commands
    assert 'historical_manual.runner' not in commands
    assert 'secrets.' not in str(w)
    assert 'git reset --hard origin/main' in commands
    assert 'gh workflow run pages.yml --ref main' in commands
