"""Freeze the 15:00 queried fixture population using retained ID-only evidence."""
import json
from .master_schedule_plan import RAW_PATH, stamp, items

POLICY = 'FIXED_1500_FIXTURE_COHORT_V1'
EFFECTIVE_DAY = '2026-10-14'


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def cohort(root, day):
    target = day+'T15:00:00+07:00'
    receipts = [r for r in rows(root/'data/normalized/research_v2_slot_ledger.jsonl')
                if r.get('provider', 'oddspapi') == 'oddspapi'
                and r.get('scheduled_target_at') == target
                and r.get('collection_succeeded') is True and r.get('coverage_tournament_ids')]
    if not receipts:
        return None
    first = min(receipts, key=lambda r: r['finalized_at'])
    observed = stamp(first.get('request_completed_at') or first.get('actual_observed_at'))
    ids = set(map(str, first['coverage_tournament_ids']))
    schedules = [r for r in rows(root/RAW_PATH) if r.get('endpoint') == '/fixtures'
                 and stamp(r.get('observed_at')) and observed and stamp(r['observed_at']) <= observed
                 and r.get('params', {}).get('from') == day+'T05:00:00+00:00'
                 and r.get('params', {}).get('to') == day+'T23:00:00+00:00']
    if not schedules:
        return None  # Never guess identities or reconstruct a schedule from names.
    schedule = max(schedules, key=lambda r: stamp(r['observed_at']))
    from .master_schedule_plan import registry
    from .research_population import exclusion_reason
    from .master_scan_scope import scan_scope_reason
    approved = {str(r['tournament_id']) for r in registry()}
    result = {}
    for f in items(schedule['payload']):
        tid = str(f.get('tournamentId')); ko = stamp(f.get('startTime')); fid = f.get('fixtureId')
        if (fid and tid in ids & approved and ko and observed < ko
                and f.get('statusId') == 0 and not exclusion_reason(f, provider='oddspapi')
                and not scan_scope_reason(f, provider='oddspapi')):
            result[str(fid)] = {'fixture_id': str(fid), 'tournament_id': int(tid),
                               'kickoff': ko.isoformat(), 'home': f.get('participant1Name'),
                               'away': f.get('participant2Name')}
    return {'policy': POLICY, 'setup_target_at': target, 'setup_observed_at': observed.isoformat(),
            'schedule_response_id': schedule['response_id'], 'fixtures': list(result.values())}


def annotate(report, setup, now, requested=(), audits=(), snapshots=(), errors=False):
    requested = set(map(str, requested)); audit = {str(r['fixture_id']): r for r in audits}
    valid = {}
    from .research_v2_slots import collection_snapshot
    for r in snapshots:
        valid[str(r['fixture_id'])] = collection_snapshot(r)
    details = []
    for f in setup['fixtures']:
        row = dict(f); past = stamp(f['kickoff']) <= now
        seen = audit.get(f['fixture_id'])
        if past and not seen:
            reason = 'KICKOFF_PASSED'
        elif str(f['tournament_id']) not in requested:
            reason = 'SKIPPED_QUOTA' if report.get('status') == 'SKIPPED_QUOTA' else 'UNQUERIED'
        elif not seen:
            reason = 'API_FAILURE' if errors else 'NO_FIXTURE_IN_PROVIDER_RESPONSE'
        elif valid.get(f['fixture_id']):
            reason = 'OBSERVED_CORE_ODDS'
        elif f['fixture_id'] in valid:
            reason = 'OBSERVED_OUTSIDE_CORE_PRICE'
        else:
            reason = seen.get('eligibility_reason') or 'NO_VERIFIED_PREMATCH_ODDS'
        row.update(reason=reason, observed_at=seen.get('observed_at') if seen else None,
                   queried=str(f['tournament_id']) in requested, quote_persisted=f['fixture_id'] in valid)
        details.append(row)
    pending = [f for f in details if stamp(f['kickoff']) > now]
    report.update(daily_cohort_policy=POLICY, daily_cohort_setup_target_at=setup['setup_target_at'],
                  daily_cohort_setup_response_id=setup['schedule_response_id'],
                  daily_cohort_fixture_count=len(details), daily_cohort_fixtures=details,
                  daily_cohort_remaining_prematch_count=len(pending),
                  daily_cohort_query_complete=not errors and all(f['queried'] for f in pending))
