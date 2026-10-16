"""No-network calibration replay from immutable live cache; fail-closed expansion gate."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from research.historical_backfill import storage
from research.historical_backfill.isolated_runner import load_cache, evaluate, digest
from research.historical_backfill.normalizer import normalize
from research.historical_backfill.reconstruct import parse_time
from research.historical_backfill.representative import select, POLICY

BASE = Path('research/historical_backfill')
OUT = BASE/'data/quality'
SOURCE_CATALOG_SHA256 = 'e058dab57f1270ad1bd3b8917bd6a882df28a5a614f915e0a51a06995a8b747e'
HARD_REJECTIONS = {'IDENTITY_MISMATCH','MARKET_SCOPE_MISMATCH','INVALID_QUARTER_LINE',
    'CATALOG_LINE_MISMATCH','INVALID_SLOT','INVALID_TIMESTAMP','INVALID_PRICE',
    'AMBIGUOUS_LATEST_STATE','FUTURE_OR_INPLAY_QUOTE'}


def read(path):
    return json.loads(path.read_text())


def immutable_hashes(root):
    result = {}
    for folder in ('raw', 'cache'):
        for p in sorted((root/folder).glob('*.json')):
            if p.is_symlink():
                raise ValueError('CACHE_SYMLINK')
            result[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def validate_catalog(catalog, source):
    encoded = json.dumps(source, sort_keys=True, separators=(',', ':')).encode()
    if hashlib.sha256(encoded).hexdigest() != SOURCE_CATALOG_SHA256:
        raise ValueError('SOURCE_CATALOG_CHANGED')
    for m in catalog:
        matches = [x for x in source if str(x['marketId']) == str(m['market_id'])]
        if len(matches) != 1:
            raise ValueError('CATALOG_MARKET_ID_AMBIGUOUS')
        x = matches[0]
        if (x['sportId'], x['marketName'], x['marketType'], x['period'], x['playerProp']) != (10, 'Asian Handicap', 'spreads', 'fulltime', False):
            raise ValueError('CATALOG_SCOPE_INVALID')
        sides = {str(o['outcomeName']): o['outcomeId'] for o in x['outcomes']}
        if (m['home_line'], m['home_outcome_id'], m['away_outcome_id']) != (x['handicap'], sides['1'], sides['2']):
            raise ValueError('CATALOG_SIGN_OR_SIDE_INVALID')
    if len({str(m['market_id']) for m in catalog}) != len(catalog):
        raise ValueError('CATALOG_DUPLICATE_MARKET')


def observations():
    rows = []
    for name in ('europe_pinnacle_research_v2_snapshots.jsonl', 'v2_mainline_snapshots.jsonl'):
        p = Path('data/normalized')/name
        if p.exists():
            rows.extend(json.loads(s) for s in p.read_text().splitlines() if s.strip())
    return rows


def replay(manifest, catalog, observed, root, baseline):
    before = immutable_hashes(root)
    source = read(Path('data/normalized/oddspapi_market_catalog.json'))
    validate_catalog(catalog, source)
    results, slots, comparisons, raw_audit, errors = [], [], [], [], []
    for c in manifest['candidates'][:10]:
        payload = load_cache(root, c)
        if payload is None or payload.get('cached_http_status') == 404:
            raise ValueError('CALIBRATION_LIVE_200_CACHE_REQUIRED')
        normalized = normalize(payload, c, catalog, active_semantics_verified=True)
        ticks = [t for m in normalized for side in m['selections'].values() for t in side]
        raw_audit.append(dict(fixture_id=c['fixture_id'], reviewed_ah_markets=len(normalized),
            raw_sha256=json.loads((root/'cache'/(digest(c['request'])+'.json')).read_text())['raw_sha256'],
            tick_count=len(ticks), active_states=dict(Counter(str(t['active']) for t in ticks)),
            earliest_quote=min((t['created_at'] for t in ticks), default=None),
            latest_quote=max((t['created_at'] for t in ticks), default=None)))
        item = evaluate(c, payload, catalog, observed)
        results.append(item)
        for slot in c['missing_rounds']:
            at = parse_time(slot)
            rows = [r for r in item['reconstructed'] if parse_time(r['slot_utc']) == at]
            slots.append(select(rows, fixture_id=c['fixture_id'], bookmaker=c['bookmaker'],
                                kickoff=c['kickoff'], slot=slot, catalog=catalog))
        for o in observed:
            if o.get('fixture_id') != c['fixture_id'] or o.get('bookmaker') != c['bookmaker']:
                continue
            if parse_time(o['observed_at']) >= parse_time(c['kickoff']):
                continue
            # Reconstruct ALL reviewed lines at the actual observation time, independently
            # of which missing target slots happen to be in the recovery manifest.
            observed_candidate = {**c, 'missing_rounds': [o['observed_at']]}
            from research.historical_backfill.comparison import reconstruct_candidate
            rs = reconstruct_candidate(observed_candidate, normalized, state_semantics_verified=True)
            chosen = select(rs, fixture_id=c['fixture_id'], bookmaker=c['bookmaker'],
                kickoff=c['kickoff'], slot=o['observed_at'], catalog=catalog)
            same = [r for r in rs if r['status']=='COMPLETE' and r['line']==o['ah']['home_line']]
            comparisons.append(dict(fixture_id=c['fixture_id'], observed_at=o['observed_at'],
                observed_home_line=o['ah']['home_line'], observed_home_price=o['ah']['home_price'],
                observed_away_price=o['ah']['away_price'], balanced=chosen,
                same_observed_line_quotes=same[0]['quotes'] if len(same)==1 else None,
                difference_is_not_automatically_error=True))
    recovered = [r for x in results for r in x['reconstructed'] if r['status']=='COMPLETE']
    # Compare all 163 record contents, not just totals. Original evidence is unchanged.
    if sorted(digest(r) for r in recovered) != sorted(digest(r) for r in baseline['recovered_snapshots']):
        errors.append('ORIGINAL_RECONSTRUCTION_CHANGED')
    selected = [s for s in slots if s['status']=='BALANCED_LINE']
    rejected = Counter()
    for s in slots:
        rejected.update(s['rejection_counts'])
        if s['reason']=='CONFLICTING_DUPLICATE_LINE':
            errors.append('CONFLICTING_DUPLICATE_LINE')
    errors.extend(sorted(set(rejected)&HARD_REJECTIONS))
    if before != immutable_hashes(root):
        errors.append('RAW_OR_CACHE_MUTATED')
    sporting = [s for s in slots if s['fixture_id']=='id1000023872530942'
                and parse_time(s['slot_utc'])==parse_time('2026-09-19T15:00:00+07:00')]
    sporting_ok = len(sporting)==1 and sporting[0]['status']=='BALANCED_LINE' and (
        sporting[0]['selected']['line'], sporting[0]['selected']['quotes']['home']['price'],
        sporting[0]['selected']['quotes']['away']['price']) == (-2.0,1.892,1.990)
    if not sporting_ok:
        errors.append('SPORTING_EXPECTED_BALANCED_LINE_NOT_REPRODUCED')
    fixture_n = len({s['fixture_id'] for s in selected})
    paired_n = len({c['fixture_id'] for c in comparisons if c['same_observed_line_quotes']})
    # Freeze before looking at live replay. Coverage need not be perfect: never invent
    # a line to fill an unresolved slot. Retain original 8-fixture / 5-paired thresholds.
    passed = not errors and fixture_n>=8 and paired_n>=5 and len(results)==10 and len(recovered)==163
    return dict(status='PASS' if passed else 'FAIL', policy=POLICY, api_requests=0,
        expansion_allowed=passed, manifest_sha256=digest(manifest), catalog_sha256=digest(catalog),
        gate_policy=dict(min_balanced_fixtures=8,min_paired_fixtures=5,invalid_selections=0,
                         original_163_unchanged=True,sporting_regression_required=True),
        errors=errors, fixtures_replayed=len(results), recovered_line_snapshots=len(recovered),
        balanced_fixtures=fixture_n, paired_fixtures=paired_n, target_slots=len(slots),
        selected_slots=len(selected), unresolved_slots=len(slots)-len(selected),
        eligible_lines=sum(s['eligible_lines'] for s in slots),
        rejected_lines=sum(s['rejected_lines'] for s in slots), rejection_counts=dict(rejected),
        sporting_expected_verified=sporting_ok, raw_cache_unchanged=before==immutable_hashes(root),
        immutable_cache_hashes=before, raw_audit=raw_audit, slots=slots, observed_comparisons=comparisons)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    try:
        result = replay(read(BASE/'reports/multiday_manifest.json'),read(BASE/'reports/reviewed_catalog.json'),
            observations(),storage.ROOT,read(BASE/'reports/LIVE_PILOT_20261016.json'))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        result = dict(status='FAIL',expansion_allowed=False,api_requests=0,errors=[type(exc).__name__])
    (OUT/'calibration.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('slots','observed_comparisons','immutable_cache_hashes','raw_audit')},indent=2))
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':
    raise SystemExit(main())


def authorize_expansion(report, manifest, catalog, root):
    """Bind passing calibration to exact inputs and unchanged raw bytes, before HTTP."""
    if (report.get('status')!='PASS' or report.get('expansion_allowed') is not True
        or report.get('policy')!=POLICY or report.get('errors')
        or report.get('manifest_sha256')!=digest(manifest)
        or report.get('catalog_sha256')!=digest(catalog)
        or report.get('sporting_expected_verified') is not True
        or report.get('raw_cache_unchanged') is not True
        or report.get('recovered_line_snapshots')!=163
        or report.get('balanced_fixtures',0)<8 or report.get('paired_fixtures',0)<5):
        raise ValueError('PRICE_QUALITY_GATE_REQUIRED')
    now=immutable_hashes(root)
    expected=report.get('immutable_cache_hashes',{})
    if not expected or any(now.get(k)!=v for k,v in expected.items()):
        raise ValueError('CALIBRATION_CACHE_CHANGED')
    for c in manifest['candidates'][:10]:
        payload=load_cache(root,c)
        if payload is None or payload.get('cached_http_status')==404:
            raise ValueError('CALIBRATION_CACHE_REQUIRED_NO_REFETCH')


def require_cached_prefix(manifest, count, root):
    """Resume only if every previously completed candidate is still in verified cache."""
    if type(count) is not int or not 10 <= count <= len(manifest['candidates']):
        raise ValueError('INVALID_RESUME_PREFIX')
    for c in manifest['candidates'][:count]:
        if load_cache(root,c) is None:
            raise ValueError('RESUME_CACHE_INCOMPLETE_NO_REFETCH')
    return count
