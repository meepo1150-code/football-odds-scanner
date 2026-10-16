"""Immutable ID-evidenced fixture set for the isolated automatic scanner."""
import hashlib
import json
from pathlib import Path
from .daily_scan_cohort import annotate
from .master_schedule_plan import RAW_PATH, stamp, items, registry
from .master_scan_scope import scan_scope_reason
from .research_population import exclusion_reason

MANIFESTS = Path('data/normalized/automatic_scan_manifests.jsonl')
POLICY = 'AUTO_IMMUTABLE_1500_V1'


def rows(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()] if path.exists() else []


def cohort(root, day):
    found = [r for r in rows(root/MANIFESTS) if r['football_day'] == day]
    if not found:
        return None
    if any(r != found[0] for r in found):
        raise ValueError('Conflicting immutable daily manifests')
    return found[0]


def retained_schedule(root, day):
    manifest = cohort(root, day)
    if manifest:
        return next((r for r in rows(root/RAW_PATH) if r['response_id'] == manifest['schedule_response_id']), None)


def freeze(root, report):
    day = report['football_day']
    existing = cohort(root, day)
    if existing:
        return existing
    if report.get('coverage_complete') is not True or report.get('errors') or report.get('status') not in {'RESEARCH_V2_OBSERVED', 'ZERO_USABLE_FIXTURES'}:
        raise ValueError('Preparation is not validated; manifest forbidden')
    raw = next((r for r in rows(root/RAW_PATH) if r['response_id'] == report.get('schedule_response_id')), None)
    if raw is None or not isinstance(raw['payload'], list) or len(raw['payload']) >= 1000:
        raise ValueError('Complete retained schedule evidence required')
    approved = {str(r['tournament_id']) for r in registry()}
    requested = set(map(str, report.get('coverage_tournament_ids', [])))
    observed = stamp(report.get('collection_started_at') or report['generated_at'])
    start, end = stamp(report['football_day_window_start']), stamp(report['football_day_window_end'])
    fixtures = {}
    for f in items(raw['payload']):
        ko, fid, tid = stamp(f.get('startTime')), f.get('fixtureId'), str(f.get('tournamentId'))
        if (fid and tid in approved and ko and start <= ko < end and ko > observed
            and f.get('statusId') == 0 and not exclusion_reason(f, provider='oddspapi')
            and not scan_scope_reason(f, provider='oddspapi')):
            if tid not in requested:
                raise ValueError('Eligible tournament omitted from preparation')
            record = dict(fixture_id=str(fid), tournament_id=int(tid), kickoff=ko.isoformat(),
                          home=f.get('participant1Name'), away=f.get('participant2Name'))
            if str(fid) in fixtures and fixtures[str(fid)] != record:
                raise ValueError('Conflicting fixture identities')
            fixtures[str(fid)] = record
    result = dict(policy=POLICY, football_day=day, setup_target_at=report['scheduled_target_at'],
        setup_observed_at=report['actual_observed_at'], schedule_response_id=raw['response_id'],
        fixtures=sorted(fixtures.values(), key=lambda r:r['fixture_id']))
    result['manifest_id'] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    path = root/MANIFESTS
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as out:
        out.write(json.dumps(result, sort_keys=True)+'\n')
    return result


def cached_response(root, endpoint, params, target, now):
    # Reconcile successful batches of this slot only. Preserve original observed_at.
    for row in reversed(rows(root/RAW_PATH)):
        observed = stamp(row.get('observed_at'))
        if (row.get('endpoint') == endpoint and row.get('params') == params and observed
            and target <= observed <= now):
            return row
    return None


def request_batches(root, ids, target, now, size=5):
    """Keep successful same-slot batches intact even when priority/kickoff changes."""
    remaining = set(map(str, ids))
    result = []
    for row in reversed(rows(root/RAW_PATH)):
        observed = stamp(row.get('observed_at'))
        if row.get('endpoint') != '/odds-by-tournaments' or not observed or not target <= observed <= now:
            continue
        params = row.get('params', {})
        batch = str(params.get('tournamentIds', '')).split(',')
        if remaining.intersection(batch):
            result.append([int(x) for x in batch])
            remaining.difference_update(batch)
    pending = sorted(int(x) for x in remaining)
    result.extend(pending[i:i+size] for i in range(0, len(pending), size))
    return result
