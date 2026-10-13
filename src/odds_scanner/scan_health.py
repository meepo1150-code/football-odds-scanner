"""Quota-free immutable scan receipts and a current actionable health monitor."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

HISTORY = Path('data/normalized/scan_health_history.jsonl')
LATEST = Path('reports/scan_health_latest.json')
MONITOR = Path('reports/scan_health_monitor.json')
SOURCES = ('europe_pinnacle', 'propline', 'pinnwire')


def rows(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()] if path.exists() else []


def load(root, name):
    p = root / 'reports' / (name + '.json')
    return json.loads(p.read_text()) if p.exists() else {}


def stamp(value):
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (ValueError, TypeError):
        return None


def number(value):
    return value if type(value) is int and value >= 0 else None


def record(root, report, provider='oddspapi', provenance='LIVE_REPORT'):
    """Capture only public health fields; never archive exception text or credentials."""
    from .research_v2_slots import collection_snapshot
    status = str(report.get('status', 'UNKNOWN'))
    when = report.get('checked_at') or report.get('generated_at')
    if stamp(when) is None:
        raise ValueError('Scan health needs an explicit observation timestamp')
    observed = stamp(report.get('actual_observed_at') or when)
    started = stamp(report.get('collection_started_at') or report.get('fetch_started_at')) or observed
    finished = stamp(report.get('request_completed_at')) or observed
    # Count exact fixture IDs from this attempt's persisted valid core quotes.
    valid = {str(s['fixture_id']) for s in rows(root / 'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl')
             if collection_snapshot(s) and stamp(s.get('observed_at')) is not None and started <= stamp(s.get('observed_at')) <= finished
             and (s.get('provider') == provider or provider == 'oddspapi' and str(s.get('source_semantics', '')).startswith('CURRENT_ODDSPAPI_'))}
    found = number(report.get('scheduled_approved_fixtures'))
    if found is None:
        found = number(report.get('football_day_fixtures', report.get('source_rows_in_football_day')))
    returned = number(report.get('football_day_fixtures'))
    errors = len(report.get('errors') or [])
    attempted = (number(report.get('requests_used')) or 0) + (number(report.get('http_requests_attempted')) or 0) + (number(report.get('account_requests_attempted')) or 0)
    api_errors = errors if attempted else 0
    if status.startswith('SKIPPED_') or status in {'MISSED_SLOT','PROVIDER_COOLDOWN'}:
        valid = set()
    incomplete = report.get('coverage_complete') is not True
    coverage = report.get('competition_coverage') or []
    unqueried = sum(number(c.get('remaining_prematch_fixtures')) or 0 for c in coverage if c.get('reason') in {'QUOTA_SKIPPED', 'AWAITING_ODDS', 'NO_SCHEDULE_EVIDENCE'})
    issues = []
    if errors or 'FAILED' in status or 'INVALID' in status or status == 'API_KEY_NOT_CONFIGURED': issues.append('API_OR_CONFIGURATION_FAILURE')
    if incomplete: issues.append('COVERAGE_INCOMPLETE')
    if unqueried: issues.append('QUOTA_OR_UNQUERIED_FIXTURES')
    if report.get('observation_timing') in {'LATE', 'OUTSIDE_WINDOW'}: issues.append('SCAN_LATE')
    if found is None: issues.append('FIXTURE_COUNT_UNKNOWN')
    if status not in {'RESEARCH_V2_OBSERVED', 'ZERO_USABLE_FIXTURES'}: issues.append('COLLECTION_NOT_CONFIRMED')
    if found and len(valid) < found: issues.append('FIXTURES_WITHOUT_VALID_CORE_ODDS')
    health = 'FAIL' if 'API_OR_CONFIGURATION_FAILURE' in issues else 'WARNING' if issues else 'PASS'
    receipt = {'schema_version': '1.0', 'provider': provider, 'generated_at': when,
               'actual_observed_at': report.get('actual_observed_at'), 'football_day': report.get('football_day'),
               'scheduled_target_at': report.get('scheduled_target_at'), 'scan_status': status,
               'provenance': provenance, 'status': health, 'issues': issues,
               'fixtures_found': found, 'fixtures_with_valid_odds': len(valid),
               'fixtures_without_valid_odds': max(0, found-len(valid)) if found is not None else None,
               'fixtures_unqueried': unqueried, 'fixtures_returned_in_market_response': returned,
               'api_error_count': api_errors, 'source_or_configuration_error_count': errors, 'requests_used': number(report.get('requests_used')),
               'coverage_complete': not incomplete, 'schedule_response_id': report.get('schedule_response_id'),
               'data_source_health': report.get('data_source_health'),
               'account_requests_attempted': number(report.get('account_requests_attempted')),
               'account_transient_failures': report.get('account_transient_failures', []),
               'competition_coverage': coverage,
               'count_semantics': 'DISTINCT_FIXTURES; STRICT_PREMATCH_CORE_AH_1.80_TO_2.20; UNQUERIED_IS_NOT_CONFIRMED_NO_MARKET',
               'record_type': 'CONTROL_CHECK' if status.startswith('SKIPPED_') or status in {'MISSED_SLOT','PROVIDER_COOLDOWN'} else 'SCAN_ATTEMPT'}
    # Imported prior reports are explicitly marked and carry no current Actions identity.
    if provenance == 'LIVE_REPORT' and os.getenv('GITHUB_RUN_ID'):
        receipt['workflow_run_url'] = 'https://github.com/' + os.environ.get('GITHUB_REPOSITORY', 'meepo1150-code/football-odds-scanner') + '/actions/runs/' + os.environ['GITHUB_RUN_ID']
        receipt['workflow_run_attempt'] = os.getenv('GITHUB_RUN_ATTEMPT', '1')
    receipt['report_id'] = hashlib.sha256(json.dumps(receipt, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    path = root / HISTORY
    if not any(r.get('report_id') == receipt['report_id'] for r in rows(path)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(receipt, ensure_ascii=False, sort_keys=True)+'\n')
    write_latest(root)
    summary = os.getenv('GITHUB_STEP_SUMMARY')
    if summary and provenance == 'LIVE_REPORT':
        with open(summary, 'a', encoding='utf-8') as handle:
            handle.write('\n### Scan Health: '+provider+' — '+health+'\n\n')
            handle.write('Workflow conclusion is separate from data health.\n\n')
            handle.write('Scan status: `'+status+'` · valid odds: '+str(len(valid))+
                         ' · fixtures: '+str(found if found is not None else 'UNKNOWN')+
                         ' · API errors: '+str(api_errors)+' · billable requests: '+
                         str(number(report.get('requests_used')) or 0)+'\n\n')
            handle.write('Issues: '+(', '.join(issues) or 'none')+'\n')
    return receipt


def write_latest(root):
    history = rows(root / HISTORY)
    order = lambda r: (stamp(r['generated_at']), r['report_id'])
    attempts = [r for r in history if r.get('record_type') == 'SCAN_ATTEMPT']
    latest = max(attempts, key=order) if attempts else None
    checks = sorted(history, key=order, reverse=True)[:30]
    value = {'schema_version': '1.0', 'latest_scan': latest, 'recent_reports': checks,
             'report_count': len(history), 'history_path': str(HISTORY)}
    p = root / LATEST
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    return value


def refresh(root=Path('.'), now=None):
    """Read canonical slots and FT/identity evidence; no calls or queue deletions."""
    from .research_v2_slots import coverage, read_ledger, read_snapshots
    from .europe_pinnacle_discovery import _football_day_bounds
    now = now or datetime.now(timezone.utc)
    latest = write_latest(root)
    col = coverage(now, _football_day_bounds(now)[2], read_ledger(root), read_snapshots(root))
    ft = load(root, 'research_v2_missing_ft_ledger').get('fixtures', [])
    # Include retained approved unresolved fixtures, even if previously retired.
    overdue = [r for r in ft if r.get('status') not in {'POSTPONED', 'CANCELLED', 'ABANDONED'} and stamp(r.get('kickoff')) and (now-stamp(r['kickoff'])).total_seconds() >= 10800]
    stats = load(root, 'research_v2_pattern_statistics')
    identity = load(root, 'research_v2_fixture_identity')
    unmatched = identity.get('rejected', [])
    issues = []
    missing = [r for r in col['canonical_slots'] if r['state'] in {'MISSING','MISSED'}]
    if missing: issues.append('SCAN_MISSING')
    if overdue: issues.append('FT_DELAY')
    if stats.get('identity_conflict_ft_fixtures'): issues.append('FT_IDENTITY_CONFLICT')
    if unmatched: issues.append('UNMATCHED_IDENTITY_CANDIDATES')
    scan = latest['latest_scan']
    if scan and scan['status'] != 'PASS': issues.append('LATEST_SCAN_' + scan['status'])
    if not scan: issues.append('NO_SCAN_HEALTH_RECEIPT')
    value = {'schema_version':'1.0', 'generated_at': now.isoformat(), 'football_day': _football_day_bounds(now)[2],
             'status': 'FAIL' if 'SCAN_MISSING' in issues or scan and scan['status']=='FAIL' else 'WARNING' if issues else 'PASS',
             'issues': issues, 'scan_missing_count': len(missing), 'scan_missing': missing,
             'ft_delay_count': len(overdue), 'ft_delay': overdue,
             'verified_non_ft_lifecycle_count': sum(r.get('status') in {'POSTPONED','CANCELLED','ABANDONED'} for r in ft),
             'unmatched_count': len(unmatched), 'unmatched': unmatched,
             'unmatched_semantics': 'REJECTED_CROSS_PROVIDER_BRIDGE_CANDIDATES; NOT_AUTOMATICALLY_MISSING_FT',
             'latest_scan_report_id': scan['report_id'] if scan else None,
             'latest_scan_day': scan.get('football_day') if scan else None,
             'history_report_count': latest['report_count'], 'canonical_slots': col['canonical_slots'],
             'api_requests_used':0, 'raw_deleted':0, 'approved_unresolved_fixtures_retained':True}
    p = root / MONITOR
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    return value


if __name__ == '__main__':
    print(json.dumps(refresh(), ensure_ascii=False))
