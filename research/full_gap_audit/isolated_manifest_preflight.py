"""Offline-only deterministic gate for the pinned 23-row historical manifest."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

EXPECTED = 23
REQUIRED = {'fixture_id', 'bookmaker', 'slot_utc', 'deduplication_key', 'recovery_eligible', 'status', 'mapping_evidence'}

def check(path):
    raw = Path(path).read_bytes()
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    errors = []
    if len(rows) != EXPECTED:
        errors.append(f'expected {EXPECTED} entries, got {len(rows)}')
    keys = set()
    for i, row in enumerate(rows, 1):
        missing = REQUIRED - row.keys()
        if missing: errors.append(f'row {i}: missing {sorted(missing)}')
        key = row.get('deduplication_key')
        if key in keys: errors.append(f'row {i}: duplicate deduplication_key')
        keys.add(key)
        if not row.get('mapping_evidence'): errors.append(f'row {i}: no identity evidence')
        if row.get('status') not in {'SCAN_FAILED', 'NO_PRICE'}: errors.append(f'row {i}: unsupported status')
        if row.get('recovery_eligible') is not True: errors.append(f'row {i}: not eligible')
        if row.get('bookmaker') != 'pinnacle': errors.append(f'row {i}: unexpected bookmaker')
    return {'gate': 'PASS_OFFLINE_MANIFEST_ONLY' if not errors else 'FAIL',
            'historical_api_requests': 0, 'credential_checked': False,
            'production_writes': 0, 'manifest_sha256': hashlib.sha256(raw).hexdigest(),
            'manifest_rows': len(rows), 'statuses': dict(Counter(x.get('status') for x in rows)),
            'errors': errors, 'live_recovery_authorized': False}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest')
    args = parser.parse_args()
    report = check(args.manifest)
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report['gate'].startswith('PASS') else 1)
