"""Bounded workflow_dispatch historical reconstruction. Artifact output only."""
import argparse
import hashlib
import json
import os
import shutil
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .planner import BKK, build, stamp
from .normalizer import normalize
from .reconstruct import reconstruct_slot
from .representative import select
from .safety import HttpClient, StopPilot, digest, health_check, summarize_account

CACHE = Path('research/historical_backfill/data')
OUT = Path('research/manual_historical/output')
CATALOG = Path(__file__).parent/'reports/reviewed_catalog.json'
CATALOG_SHA = '2cb3c075c1888e354cfaed4a4b34ab7eeca2dcf24f5801b9e393c8fd0ed95e5d'


def write_json(path, value):
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
    for name in ('HISTORICAL_ODDSPAPI_KEY', 'ACCOUNT_PROBE_KEY'):
        secret = os.getenv(name)
        if secret and secret in text:
            raise StopPilot('SECRET_OUTPUT_BLOCKED')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def cache_read(root, candidate):
    index = root/'cache'/(digest(candidate['request'])+'.json')
    if not index.exists():
        return None
    if index.is_symlink() or index.resolve().parent != (root/'cache').resolve():
        raise StopPilot('CACHE_PATH_INVALID')
    receipt = json.loads(index.read_text())
    if receipt.get('request') != candidate['request']:
        raise StopPilot('CACHE_REQUEST_MISMATCH')
    # Only finalized matches may reuse immutable history indefinitely. Planner
    # additionally requires all targets to be past; live retrieval requires KO past.
    fetched = stamp(receipt['fetched_at'])
    if fetched < stamp(candidate['kickoff']):
        return None
    if receipt.get('origin') == 'LIVE_HTTP_404':
        return {'fixtureId': candidate['fixture_id'], 'bookmakers': {}}
    sha = receipt.get('raw_sha256', '')
    if receipt.get('origin') != 'LIVE_HTTP_200' or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
        raise StopPilot('CACHE_PROVENANCE_INVALID')
    path = root/'raw'/(sha+'.json')
    if path.is_symlink() or path.resolve().parent != (root/'raw').resolve():
        raise StopPilot('CACHE_PATH_INVALID')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise StopPilot('CACHE_HASH_MISMATCH')
    payload = json.loads(raw)
    if payload.get('fixtureId') != candidate['fixture_id']:
        raise StopPilot('CACHE_FIXTURE_MISMATCH')
    return payload


def cache_store(root, c, status, raw, now):
    root.mkdir(parents=True, exist_ok=True)
    receipt = dict(request=c['request'], fetched_at=now.isoformat(), http_status=status,
                   origin='LIVE_HTTP_'+str(status))
    if status == 200:
        payload = json.loads(raw)
        if payload.get('fixtureId') != c['fixture_id']:
            raise StopPilot('RESPONSE_FIXTURE_MISMATCH')
        for name in ('HISTORICAL_ODDSPAPI_KEY', 'ACCOUNT_PROBE_KEY'):
            key = os.getenv(name)
            if key and key.encode() in raw:
                raise StopPilot('SECRET_IN_RESPONSE')
        sha = hashlib.sha256(raw).hexdigest()
        dest = root/'raw'/(sha+'.json')
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_symlink():
            raise StopPilot('CACHE_PATH_INVALID')
        if dest.exists():
            if dest.read_bytes() != raw:
                raise StopPilot('CACHE_HASH_MISMATCH')
        else:
            with dest.open('xb') as f:
                f.write(raw)
        receipt['raw_sha256'] = sha
    # A growing prematch cache is not silently overwritten/refetched. Manual
    # operator must review invalidation; all finished valid receipts are reused.
    index = root/'cache'/(digest(c['request'])+'.json')
    index.parent.mkdir(parents=True, exist_ok=True)
    if index.exists():
        raise StopPilot('EXISTING_CACHE_REQUIRES_REVIEW')
    write_json(index, receipt)


def fresh_health(root):
    """Rebuild production health offline on private copies; never touch live files."""
    from odds_scanner.scan_health import refresh
    with tempfile.TemporaryDirectory(prefix='historical-health-') as folder:
        private = Path(folder)
        for name in ('data', 'reports', 'config'):
            if (root/name).exists():
                shutil.copytree(root/name, private/name)
        report = refresh(private)
        # refresh returns the complete monitor dictionary in current production.
        if not isinstance(report, dict):
            report = json.loads((private/'reports/scan_health_monitor.json').read_text())
        if report.get('api_requests_used') != 0 or report.get('raw_deleted') != 0:
            raise StopPilot('HEALTH_NOT_READ_ONLY')
        return report


def reconstruct(c, payload, catalog):
    markets = normalize(payload, c, catalog, active_semantics_verified=True)
    slots, all_lines = [], []
    for t in c['targets']:
        if t['status'] == 'NOT_PREMATCH_SLOT':
            slots.append({**t, 'selected': None})
            continue
        rows = []
        for m in markets:
            r = reconstruct_slot(fixture_id=c['fixture_id'], kickoff=c['kickoff'],
                slot=t['target_utc'], source='oddspapi', bookmaker=c['bookmaker'], market='AH',
                line=m['line'], selections=m['selections'])
            r['market_id'] = m['market_id']
            rows.append(r)
        pick = select(rows, fixture_id=c['fixture_id'], bookmaker=c['bookmaker'],
                      kickoff=c['kickoff'], slot=t['target_utc'], catalog=catalog)
        if not markets:
            pick.update(status='NO_HISTORICAL_DATA', reason='NO_REVIEWED_AH_MARKET_IN_RESPONSE')
        slots.append({**t, **pick, 'timestamp_basis': 'PROVIDER_HISTORY_ENTRY_CREATED_AT_NOT_LIVE_COLLECTION'})
        all_lines.extend(rows)
    # Compare original live observations at their actual capture times, not at
    # requested target times. A different price at another instant is not an error.
    comparisons = []
    for o in c['observations']:
        if stamp(o['observed_at']) >= stamp(c['kickoff']):
            continue
        for m in markets:
            if m['line'] != o.get('ah', {}).get('home_line'):
                continue
            r = reconstruct_slot(fixture_id=c['fixture_id'], kickoff=c['kickoff'],
                slot=o['observed_at'], source='oddspapi', bookmaker=c['bookmaker'], market='AH',
                line=m['line'], selections=m['selections'])
            comparisons.append(dict(observed_at=o['observed_at'], status=r['status'], line=m['line'],
                original_prices={s: o['ah'].get(s+'_price') for s in ('home', 'away')},
                historical_quotes=r.get('quotes'), difference_is_not_automatically_error=True))
    hard = {'INVALID_TIMESTAMP', 'INVALID_PRICE', 'AMBIGUOUS_LATEST_STATE', 'IDENTITY_MISMATCH',
            'CATALOG_LINE_MISMATCH', 'FUTURE_OR_INPLAY_QUOTE', 'CONFLICTING_DUPLICATE_LINE'}
    if any(r['status'] in hard for r in all_lines) or any(
            set(s.get('rejection_counts', {})) & hard or s.get('reason') in hard for s in slots):
        raise StopPilot('QUOTE_QUALITY_ANOMALY')
    return dict(fixture_id=c['fixture_id'], bookmaker=c['bookmaker'], football_day=c['football_day'],
        home=c['home'], away=c['away'], kickoff=c['kickoff'], slots=slots,
        exact_lines=all_lines, original_comparisons=comparisons,
        official_mainline_verified=False, promotion_eligible=False, data_origin='BACKFILLED')


def execute(args, *, root=Path('.'), clock=lambda: datetime.now(timezone.utc), sleeper=time.sleep,
            client_factory=HttpClient, health_reader=None, environ=None):
    env = os.environ if environ is None else environ
    out, cache = root/OUT, root/CACHE
    report = dict(status='BLOCKED', historical_requests=0, account_requests=0, cache_hits=0,
        errors=[], results=[], requests=[], production_writes=0, research_only=True,
        run_url=f"https://github.com/{env.get('GITHUB_REPOSITORY', '')}/actions/runs/{env.get('GITHUB_RUN_ID', '')}")
    production = None
    def save():
        report.update(generated_at=clock().isoformat(), total_http_requests=report['historical_requests']+report['account_requests'])
        write_json(out/'report.json', report)
    def account(key, books):
        if not key:
            raise StopPilot('CREDENTIAL_MISSING')
        sleeper(1.2)
        report['account_requests'] += 1
        save()
        status, _, raw = client_factory(key)('/account', {})
        if status != 200:
            raise StopPilot('ACCOUNT_HTTP_'+str(status))
        payload = json.loads(raw)
        if not payload.get('current_subscription_id'):
            raise StopPilot('SUBSCRIPTION_ID_MISSING')
        return summarize_account(payload, books, clock())
    try:
        if args.mode not in {'plan', 'cache-only', 'recover'}:
            raise StopPilot('INVALID_MODE')
        raw_catalog = CATALOG.read_bytes()
        if hashlib.sha256(raw_catalog).hexdigest() != CATALOG_SHA:
            raise StopPilot('REVIEWED_CATALOG_CHANGED')
        catalog = json.loads(raw_catalog)
        manifest = build(root, args.start_day, args.end_day, args.times, args.bookmakers, clock())
        # No new requests for a growing/prematch fixture history.
        if any(stamp(c['kickoff']) >= clock() for c in manifest['candidates']):
            raise StopPilot('FIXTURE_HAS_NOT_KICKED_OFF')
        payloads, uncached = {}, []
        for c in manifest['candidates']:
            if not any(t['status'] == 'PENDING' for t in c['targets']):
                continue
            key = c['fixture_id'], c['bookmaker']
            payload = cache_read(cache, c)
            if payload is None:
                uncached.append(c)
            else:
                payloads[key] = payload
        manifest.update(planned_historical_requests=len(uncached), cached_pairs=len(payloads),
            request_count_policy='ALL_VERIFIED_CANDIDATES_NO_INTERNAL_COUNT_CAP',
            request_deduplication='FIXTURE_BOOKMAKER_NOT_TARGET_TIME',
            estimated_account_checks_if_recover=2*len(uncached)+3 if uncached else 0,
            requested_target_slots=sum(len(c['targets']) for c in manifest['candidates']))
        write_json(out/'manifest.json', manifest)
        report['plan'] = {k:v for k,v in manifest.items() if k != 'candidates'}
        if not manifest['candidates']:
            report['status'] = 'NO_VERIFIED_FIXTURES'
        elif args.mode == 'plan':
            report['status'] = 'PLANNED'
        else:
            if args.mode == 'recover' and uncached:
                if not args.confirm_live_requests:
                    raise StopPilot('LIVE_REQUEST_CONFIRMATION_REQUIRED')
                if (env.get('GITHUB_EVENT_NAME') != 'workflow_dispatch'
                        or env.get('GITHUB_REF') != 'refs/heads/main'
                        or env.get('PILOT_ENVIRONMENT') != 'historical-research'):
                    raise StopPilot('MAIN_MANUAL_HISTORICAL_ENVIRONMENT_REQUIRED')
                reader = health_reader or (lambda: fresh_health(root))
                baseline = reader()
                books = {c['bookmaker'] for c in uncached}
                production = account(env.get('ACCOUNT_PROBE_KEY'), set())
                research = account(env.get('HISTORICAL_ODDSPAPI_KEY'), books)
                if production['subscription_fingerprint'] == research['subscription_fingerprint']:
                    raise StopPilot('SHARED_PRODUCTION_SUBSCRIPTION')
                isolation = dict(research=research['subscription_fingerprint'],
                                 production=production['subscription_fingerprint'])
                health_check(baseline, baseline, clock(), account_isolation=isolation)
                report.update(production_before=production, research_before=research,
                    credential_isolation='DISTINCT_ACTIVE_SUBSCRIPTIONS_VERIFIED',
                    time_policy='ISOLATED_MANUAL_NO_PRODUCTION_CLOCK_BLACKOUT',
                    production_health_baseline={k: baseline[k] for k in ('generated_at', 'status', 'issues')})
                client = client_factory(env['HISTORICAL_ODDSPAPI_KEY'])
                for c in uncached:
                    health_check(reader(), baseline, clock(), account_isolation=isolation)
                    before = account(env['HISTORICAL_ODDSPAPI_KEY'], books)
                    sleeper(5.2)
                    receipt = dict(fixture_id=c['fixture_id'], bookmaker=c['bookmaker'], attempted_at=clock().isoformat())
                    report['requests'].append(receipt)
                    report['historical_requests'] += 1
                    save()
                    status, _, raw = client('/historical-odds', c['request']['params'])
                    receipt['http_status'] = status
                    if status not in (200, 404):
                        raise StopPilot('HISTORY_HTTP_'+str(status)+'_STOP_NO_RETRY')
                    cache_store(cache, c, status, raw, clock())
                    # Artifacts retain only newly fetched bytes, not another full
                    # copy of the 1GB reviewed seed on every cache-only replay.
                    index = cache/'cache'/(digest(c['request'])+'.json')
                    archive = out/'new_cache'
                    (archive/'cache').mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(index, archive/'cache'/index.name)
                    entry = json.loads(index.read_text())
                    if entry.get('raw_sha256'):
                        (archive/'raw').mkdir(parents=True, exist_ok=True)
                        name = entry['raw_sha256']+'.json'
                        shutil.copyfile(cache/'raw'/name, archive/'raw'/name)
                    after = account(env['HISTORICAL_ODDSPAPI_KEY'], books)
                    if before != after:
                        raise StopPilot('RESEARCH_QUOTA_OR_SUBSCRIPTION_CHANGED')
                    payloads[c['fixture_id'], c['bookmaker']] = cache_read(cache, c)
                    report['results'].append(reconstruct(c, payloads[c['fixture_id'], c['bookmaker']], catalog))
                    save()
            for c in manifest['candidates']:
                if any(r['fixture_id'] == c['fixture_id'] and r['bookmaker'] == c['bookmaker']
                       for r in report['results']):
                    continue
                payload = payloads.get((c['fixture_id'], c['bookmaker']))
                if payload is not None:
                    report['cache_hits'] += int(c not in uncached)
                    report['results'].append(reconstruct(c, payload, catalog))
                else:
                    report['results'].append(dict(fixture_id=c['fixture_id'], bookmaker=c['bookmaker'],
                        football_day=c['football_day'], slots=[{**t, 'status': t['status'] if t['status'] != 'PENDING'
                        else 'CACHE_MISS_NO_REQUEST', 'selected': None} for t in c['targets']]))
                save()
            report['status'] = 'PARTIAL_CACHE_MISS' if args.mode == 'cache-only' and uncached else 'COMPLETED'
    except (StopPilot, ValueError, KeyError, TypeError, OSError) as exc:
        report['errors'].append(str(exc) if isinstance(exc, StopPilot) else type(exc).__name__)
        report['status'] = 'STOPPED' if report['historical_requests'] else 'BLOCKED'
    finally:
        if production is not None:
            try:
                after = account(env.get('ACCOUNT_PROBE_KEY'), set())
                report['production_after'] = after
                delta = after['request_count'] - production['request_count']
                report['production_quota_delta'] = delta
                report['production_usage_attribution'] = 'OBSERVED_ACCOUNT_USAGE_NOT_ATTRIBUTED_TO_HISTORICAL'
                # Concurrent live collectors may legitimately consume their own
                # distinct subscription. Never relabel that as historical usage.
                stable = all(after[k] == production[k] for k in production if k != 'request_count')
                if not stable or delta < 0:
                    raise StopPilot('PRODUCTION_ACCOUNT_CHANGED')
            except (StopPilot, ValueError, KeyError, TypeError, OSError):
                report['status'] = 'STOPPED'
                report['errors'].append('PRODUCTION_POSTCHECK_FAILED')
        report['slot_status_counts'] = dict(Counter(s['status'] for r in report['results'] for s in r['slots']))
        report['all_requested_slots_complete_fixture_bookmaker_pairs'] = sum(
            bool(r['slots']) and all(s['status'] == 'BALANCED_LINE' for s in r['slots']) for r in report['results'])
        save()
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--start-day', required=True)
    p.add_argument('--end-day', required=True)
    p.add_argument('--times', default='15:00,18:00,21:00,00:00')
    p.add_argument('--bookmakers', default='pinnacle')
    p.add_argument('--mode', choices=['plan', 'cache-only', 'recover'], default='plan')
    p.add_argument('--confirm-live-requests', action='store_true')
    args = p.parse_args()
    report = execute(args)
    summary = {k:v for k,v in report.items() if k not in ('results', 'requests')}
    text = '# Manual Historical Scan\n\n```json\n'+json.dumps(summary, ensure_ascii=False, indent=2)+'\n```\n'
    text += '\nHistory-entry times are not live scan times or guaranteed bookmaker-change times. BALANCED_LINE is not Official Mainline.\n\n'
    text += '| Football day | Fixture / book | Target BKK | Status | Home AH | Home / away odds | Home / away history-entry BKK |\n|---|---|---|---|---|---|---|\n'
    for item in report['results']:
        for slot in item['slots']:
            selected = slot.get('selected') or {}
            quotes = selected.get('quotes', {})
            prices = ' / '.join(str(quotes.get(s, {}).get('price', '—')) for s in ('home', 'away'))
            timestamps = ' / '.join(stamp(quotes[s]['quote_at_utc']).astimezone(BKK).isoformat()
                if s in quotes else '—' for s in ('home', 'away'))
            label = f"{item.get('home', item['fixture_id'])} – {item.get('away', '')} / {item['bookmaker']}".replace('|', '/')
            text += f"| {item['football_day']} | {label} | {slot['target_thai']} | {slot['status']} | {selected.get('home_line', '—')} | {prices} | {timestamps} |\n"
    (OUT/'RESULT.md').write_text(text)
    if os.getenv('GITHUB_STEP_SUMMARY'):
        Path(os.environ['GITHUB_STEP_SUMMARY']).write_text(text)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if report['status'] in {'PLANNED', 'COMPLETED', 'NO_VERIFIED_FIXTURES'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
