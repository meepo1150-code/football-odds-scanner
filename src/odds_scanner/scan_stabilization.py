"""Offline fixture diagnostics and future-slot capacity; never probe providers."""
import json
import math
from collections import Counter
from datetime import timedelta, timezone
from .master_schedule_plan import RAW_PATH, items, stamp, registry
from .daily_scan_cohort import cohort
from .research_request_budget import allocation, usage, RESERVATIONS
from .research_v2_slots import LEDGER, targets, target_football_day


def rows(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()] if path.exists() else []


def diagnostics(root, report):
    """Use the retained schedule, query receipt, and exact per-attempt evidence."""
    schedule = next((r for r in rows(root / RAW_PATH)
                     if r.get('response_id') == report.get('schedule_response_id')
                     and r.get('endpoint') == '/fixtures'), None)
    when = stamp(report.get('actual_observed_at'))
    if not schedule or not when:
        return {'status': 'INSUFFICIENT_EVIDENCE', 'fixtures': []}
    from .research_population import exclusion_reason
    from .master_scan_scope import scan_scope_reason
    approved = {str(r['tournament_id']) for r in registry()}
    audit = {str(r['fixture_id']): r for r in rows(root / 'data/normalized/europe_pinnacle_research_v2_audit.jsonl')
             if stamp(r.get('observed_at')) == when}
    from .research_v2_slots import collection_snapshot
    valid = {str(r['fixture_id']) for r in rows(root / 'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl')
             if stamp(r.get('observed_at')) == when and collection_snapshot(r)}
    requested = set(map(str, report.get('coverage_tournament_ids') or []))
    responses = [r for r in rows(root / RAW_PATH) if r.get('endpoint') == '/odds-by-tournaments'
                 and stamp(r.get('observed_at')) == when]
    returned = {str(f.get('fixtureId')) for r in responses for f in items(r['payload'])}
    frozen = cohort(root, report['football_day'])
    baseline = {f['fixture_id'] for f in frozen['fixtures']} if frozen else set()
    details = []
    for f in items(schedule['payload']):
        fid, tid, ko = str(f.get('fixtureId')), str(f.get('tournamentId')), stamp(f.get('startTime'))
        if tid not in approved or not ko or exclusion_reason(f, provider='oddspapi') or scan_scope_reason(f, provider='oddspapi'):
            continue
        if not stamp(report['football_day_window_start']) <= ko < stamp(report['football_day_window_end']):
            continue
        seen = audit.get(fid)
        if ko <= when:
            cause = 'ALREADY_KICKOFF'
        elif fid in valid:
            cause = 'VALID_ODDS'
        elif tid not in requested:
            cause = 'QUOTA_SKIPPED'
        elif not seen:
            cause = ('PROVIDER_FAILURE' if report.get('errors') else 'COLLECTOR_FAILURE' if fid in returned
                     else 'MARKET_UNAVAILABLE' if responses else 'INSUFFICIENT_EVIDENCE')
        elif any(word in str(seen.get('eligibility_reason', '')) for word in ('MAPPING', 'UNMAPPED', 'ID_CONFLICT')):
            cause = 'MAPPING_FAILURE'
        elif seen.get('eligibility_reason') == 'OK':
            cause = 'VALIDATION_REJECTED'
        else:
            cause = 'MARKET_UNAVAILABLE'
        details.append({'fixture_id': fid, 'home': f.get('participant1Name'), 'away': f.get('participant2Name'),
                        'kickoff': ko.isoformat(), 'tournament_id': tid, 'in_1500_cohort': fid in baseline,
                        'reason': cause, 'provider_reason': seen.get('eligibility_reason') if seen else None,
                        'query_scope_includes_tournament': tid in requested})
    return {'status': 'RETAINED_RESPONSE_DIAGNOSIS', 'observed_at': when.isoformat(),
            'schedule_response_id': schedule['response_id'], 'fixtures': details,
            'reason_counts': dict(Counter(f['reason'] for f in details)),
            'no_price_or_result_inferred': True}


def readiness(root, now):
    local_day = target_football_day(now)
    future = [t for offset in range(2) for t in targets((stamp(local_day+'T12:00:00+07:00') + timedelta(days=offset)).date())
              if t > now]
    target = min(future)
    day = target_football_day(target)
    fixed = cohort(root, day)
    pending = [f for f in fixed['fixtures'] if stamp(f['kickoff']) > target] if fixed else []
    ids = sorted({f['tournament_id'] for f in pending})
    chosen, budget = allocation(root / LEDGER, ids, target.astimezone(timezone.utc), prioritized=True)
    report_path = root / 'reports/europe_pinnacle_research_v2_status.json'
    last = json.loads(report_path.read_text()) if report_path.exists() else {}
    # The last account response predates that run's transport. Count every
    # durable grant after it, including unfinished grants, conservatively.
    account_at = stamp(last.get('collection_started_at'))
    account_before = last.get('quota_remaining_before')
    consumed = sum(r['requests_used'] for r in rows(root / RESERVATIONS)
                   if account_at and stamp(r['finalized_at']) >= account_at)
    estimated = max(0, account_before-consumed) if type(account_before) is int else None
    required = math.ceil(len(ids)/5)
    reserve = last.get('account_safety_reserve', 10) + budget['future_utc_requests_reserved']
    ready = fixed is not None and chosen == ids and estimated is not None and estimated-required >= reserve
    return {'target_at': target.isoformat(), 'football_day': day,
            'status': 'READY_FROM_RETAINED_EVIDENCE' if ready else 'UNVERIFIED_OR_CAPACITY_BLOCKED',
            'fixture_set_size': len(fixed['fixtures']) if fixed else None,
            'remaining_prematch_at_target': len(pending), 'pending_fixture_ids': [f['fixture_id'] for f in pending],
            'required_market_requests': required, 'allocated_tournament_ids': chosen,
            'quota_utc_day': budget['quota_utc_day'], 'research_usage': dict(zip(('day', 'month'), usage(root/LEDGER, now))),
            'account_remaining_estimate': estimated, 'account_observed_before': account_at.isoformat() if account_at else None,
            'account_estimate_limitation': 'OTHER_ACCOUNT_CONSUMERS_AFTER_OBSERVATION_NOT_MEASURED; RECHECK_UNMETERED_ACCOUNT_AT_COLLECTION',
            'fixture_set_policy': fixed['policy'] if fixed else None,
            'schedule_response_id': fixed['schedule_response_id'] if fixed else None,
            'budget': budget, 'network_requests': 0, 'runtime_verified': False}
