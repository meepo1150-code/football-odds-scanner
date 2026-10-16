"""Four-round orchestration around the isolated, proven manual collector clone."""
import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from .automatic_scan_manifest import rows, cohort, freeze, annotate

BANGKOK = ZoneInfo('Asia/Bangkok')
LEDGER = Path('data/normalized/automatic_scan_slots.jsonl')
REPORT = Path('reports/automatic_scan_latest.json')


def slot_at(now):
    if now.tzinfo is None:
        raise ValueError('aware clock required')
    local = now.astimezone(BANGKOK)
    day = local.date()
    targets = [datetime.combine(day+timedelta(days=d), datetime.min.time(), BANGKOK).replace(hour=h)
               for d in (-1, 0) for h in (0, 15, 18, 21)]
    target = max(t for t in targets if t <= local)
    football_day = (target.date()-timedelta(days=1) if target.hour == 0 else target.date()).isoformat()
    return dict(slot_id=f'{football_day}/{target.hour:02d}00', football_day=football_day,
                target_at=target.isoformat(), lag_minutes=round((local-target).total_seconds()/60, 2))


def run(root=Path('.'), *, dry_run=False, now=None):
    now = now or datetime.now(timezone.utc)
    slot = slot_at(now)
    prior = [r for r in rows(root/LEDGER) if r['slot_id'] == slot['slot_id']]
    if any(r.get('complete') for r in prior):
        return dict(slot, status='ALREADY_COMPLETE', requests_used=0, dry_run=dry_run)
    if dry_run:
        return dict(slot, dry_run=True, requests_used=0, status='DRY_RUN',
                    manifest_available=cohort(root, slot['football_day']) is not None,
                    request_policy='AUTO_PROVIDER_QUOTA_ONLY')
    report = dict(slot, generated_at=now.isoformat(), requests_used=0, errors=[],
                  recovery_status='RECOVERY' if prior or slot['lag_minutes'] > 5 else 'PRIMARY',
                  run_url=f"https://github.com/{os.getenv('GITHUB_REPOSITORY', 'meepo1150-code/football-odds-scanner')}/actions/runs/{os.getenv('GITHUB_RUN_ID', '')}")
    if slot['lag_minutes'] > 30:
        report.update(status='DELAYED', errors=['Target SLA exceeded; no late current prices substituted'])
    elif len(prior) >= 3:
        report.update(status='FAIL', errors=['Recovery attempt ceiling reached'])
    elif slot['target_at'][11:13] != '15' and cohort(root, slot['football_day']) is None:
        report.update(status='FAIL', errors=['Validated immutable 15:00 manifest missing; no replacement fixture set'])
    else:
        os.environ['RESEARCH_V2_FORCE_RUN'] = 'true'
        os.environ['RESEARCH_V2_FORCE_TARGET_AT'] = slot['target_at']
        os.environ.pop('RESEARCH_V2_MANUAL_BREADTH', None)
        os.environ.pop('RESEARCH_V2_MANUAL_UNRESTRICTED', None)
        try:
            from .automatic_scan_collector import run as collect
            report.update(collect(root))
            if slot['target_at'][11:13] == '15':
                manifest = freeze(root, report)
            else:
                manifest = cohort(root, slot['football_day'])
            from .europe_pinnacle_discovery import AUDIT_PATH, SNAPSHOT_PATH
            target = slot['target_at']
            audits = [r for r in rows(root/AUDIT_PATH) if r.get('scheduled_target_at') == target]
            snapshots = [r for r in rows(root/SNAPSHOT_PATH) if r.get('scheduled_target_at') == target]
            annotate(report, manifest, datetime.now(timezone.utc), report.get('coverage_tournament_ids', []),
                     audits, snapshots, errors=bool(report.get('errors') or report.get('coverage_complete') is not True))
            report.update(manifest_id=manifest['manifest_id'])
        except Exception as exc:
            # Avoid exception messages: upstream errors may contain credential URLs.
            report.update(status='FAIL', errors=[type(exc).__name__])
    # Exact slot IDs override collector bookkeeping, never observed timestamps.
    report.update(slot)
    report['total_fixtures'] = report.get('daily_cohort_fixture_count', 0)
    report['priced_fixtures'] = sum(bool(r['quote_persisted']) for r in report.get('daily_cohort_fixtures', []))
    report['no_price_fixtures'] = report['total_fixtures']-report['priced_fixtures']
    report['api_errors'] = len(report.get('errors', []))
    report['actual_scan_time'] = report.get('actual_observed_at')
    report['complete'] = bool(report.get('manifest_id') and report.get('coverage_complete') is True
                              and report.get('daily_cohort_query_complete') is True and not report['api_errors'])
    report['scan_health'] = ('PASS' if not report['no_price_fixtures'] else 'WARNING') if report['complete'] else 'FAIL'
    observed = datetime.fromisoformat(report['actual_scan_time']) if report.get('actual_scan_time') else now
    report['delay_minutes'] = round((observed-datetime.fromisoformat(slot['target_at'])).total_seconds()/60, 2)
    if report['delay_minutes'] > 30:
        report.update(status='DELAYED', scan_health='FAIL', complete=False)
    report['notification'] = 'GITHUB_ACTIONS_SUMMARY_ONLY; CHATGPT_CONNECTION_NOT_VERIFIED'
    path = root/LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as out:
        out.write(json.dumps(report, ensure_ascii=False)+'\n')
    (root/REPORT).parent.mkdir(parents=True, exist_ok=True)
    (root/REPORT).write_text(json.dumps(report, ensure_ascii=False, indent=2))
    summary = os.getenv('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a') as out:
            out.write('### Automatic odds observation\n\n')
            for k in ('slot_id', 'target_at', 'actual_scan_time', 'delay_minutes', 'total_fixtures',
                      'priced_fixtures', 'no_price_fixtures', 'requests_used', 'api_errors',
                      'scan_health', 'recovery_status', 'status', 'run_url', 'notification'):
                out.write(f'- {k}: {report.get(k)}\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    result = run(dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False))
    if not args.dry_run and result.get('scan_health') == 'FAIL':
        raise SystemExit(1)
