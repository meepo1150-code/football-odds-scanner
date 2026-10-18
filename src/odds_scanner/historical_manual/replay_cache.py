"""Reconstruct every usable saved response without any provider transport."""
import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

from scripts.publish_manual_historical import RUNTIME_STOP, _identity, _validate
from .runner import CATALOG, CATALOG_SHA, cache_read, reconstruct, write_json


def replay(report, manifest, cache, *, expected_run_url):
    if report.get('run_url') != expected_run_url:
        raise ValueError('HISTORICAL_ARTIFACT_RUN_MISMATCH')
    if report.get('status') != 'STOPPED' or report.get('errors') != [RUNTIME_STOP]:
        raise ValueError('CACHE_REPLAY_REQUIRES_RUNTIME_STOP')
    _validate(report, manifest, allow_runtime_partial=True)
    catalog_raw = CATALOG.read_bytes()
    if hashlib.sha256(catalog_raw).hexdigest() != CATALOG_SHA:
        raise ValueError('REVIEWED_CATALOG_HASH_MISMATCH')
    catalog = json.loads(catalog_raw)
    results = {_identity(r):copy.deepcopy(r) for r in report['results']}
    available = additional = 0
    for candidate in manifest['candidates']:
        # cache_read verifies request, fixture, SHA and complete-through-target
        # provenance. Missing data remains missing; there is no HTTP fallback.
        payload = cache_read(cache, candidate, allow_growing=True)
        if payload is None:
            continue
        available += 1
        key = _identity(candidate)
        if key not in results:
            results[key] = reconstruct(candidate, payload, catalog)
            additional += 1
    derived = copy.deepcopy(report)
    derived['results'] = [results[_identity(c)] for c in manifest['candidates']
                          if _identity(c) in results]
    derived['slot_status_counts'] = dict(Counter(
        s['status'] for r in derived['results'] for s in r['slots']))
    derived['all_requested_slots_complete_fixture_bookmaker_pairs'] = sum(
        bool(r['slots']) and all(s['status'] == 'BALANCED_LINE' for s in r['slots'])
        for r in derived['results'])
    derived['offline_cache_replay'] = dict(
        source_report_sha256=hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest(),
        original_processed_pairs=len(report['results']), available_cached_pairs=available,
        additional_processed_pairs=additional, processed_pairs=len(results),
        unprocessed_pairs=len(manifest['candidates'])-len(results), provider_requests=0)
    _validate(derived, manifest, allow_runtime_partial=True)
    return derived


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--artifact-dir', type=Path, required=True)
    p.add_argument('--cache-root', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--expected-run-url', required=True)
    args = p.parse_args()
    if args.output_dir.resolve() == args.artifact_dir.resolve():
        raise ValueError('SOURCE_ARTIFACT_MUST_REMAIN_IMMUTABLE')
    report = json.loads((args.artifact_dir/'report.json').read_text())
    manifest = json.loads((args.artifact_dir/'manifest.json').read_text())
    derived = replay(report, manifest, args.cache_root, expected_run_url=args.expected_run_url)
    write_json(args.output_dir/'report.json', derived)
    write_json(args.output_dir/'manifest.json', manifest)
    print(json.dumps(derived['offline_cache_replay'], indent=2))
    print(json.dumps(derived['slot_status_counts'], indent=2))


if __name__ == '__main__':
    main()
