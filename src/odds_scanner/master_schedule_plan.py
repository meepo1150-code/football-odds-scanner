"""ID-only whole-Master schedule planning and immutable response receipts."""
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from .master_scan_scope import approved_competitions, forward_mappings, scan_scope_reason
from .research_population import exclusion_reason

RAW_PATH = Path('data/normalized/research_v2_provider_responses.jsonl')
SCHEDULE_LIMIT = 1000


def stamp(value):
    try:
        result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (ValueError, TypeError):
        return None


def items(payload):
    rows = payload if isinstance(payload, list) else next((payload.get(k) for k in ('data','fixtures','results') if isinstance(payload.get(k), list)), None) if isinstance(payload, dict) else None
    if rows is None or any(not isinstance(r, dict) for r in rows):
        raise ValueError('Invalid provider fixture list')
    return rows


def retain(root, endpoint, params, payload, observed_at):
    """Append original JSON response; never replace a prior response or timestamp."""
    record = {'provider':'oddspapi', 'endpoint':endpoint, 'params':params,
              'observed_at':observed_at.isoformat(), 'payload':payload}
    record['response_id'] = hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    path = root/RAW_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(',', ':'))+'\n')
    return record


def cached_schedule(root, start, end, now):
    path=root/RAW_PATH
    if not path.exists(): return None
    for line in reversed(path.read_text().splitlines()):
        row=json.loads(line); p=row.get('params',{})
        observed=stamp(row.get('observed_at'))
        if (row.get('endpoint')=='/fixtures' and p.get('from')==start.isoformat()
                and p.get('to')==end.isoformat() and observed and observed<=now
                and (now-observed).total_seconds()<=18*3600):
            try: items(row['payload'])
            except ValueError: continue
            return row
    return None


def registry():
    active=approved_competitions()
    mappings=forward_mappings()
    return [{'canonical_competition_id':cid,'tournament_id':int(pid),
             'tournament_name':active[cid]['competition_name'],
             'country':active[cid]['country_name']}
            for (provider,pid),cid in sorted(mappings.items()) if provider=='oddspapi']


def plan(rows, start, end, now, *, complete=False):
    targets=registry(); by_id={str(t['tournament_id']):t for t in targets}; counts=Counter(); future=Counter(); rejected=Counter()
    seen=set()
    for f in rows:
        tid=str(f.get('tournamentId')); ko=stamp(f.get('startTime')); fid=f.get('fixtureId')
        if tid not in by_id or not ko or not start<=ko<end or not fid: continue
        reason=exclusion_reason(f,provider='oddspapi') or scan_scope_reason(f,provider='oddspapi')
        if reason: rejected[reason]+=1;continue
        if str(fid) in seen: continue
        seen.add(str(fid)); counts[tid]+=1
        if ko>now and f.get('statusId')==0: future[tid]+=1
    coverage=[]
    for t in targets:
        tid=str(t['tournament_id']); n=counts[tid]; remaining=future[tid]
        reason='AWAITING_ODDS' if remaining else 'KICKOFF_PASSED_OR_NOT_PREMATCH' if n else 'NO_MATCHES' if complete else 'NO_SCHEDULE_EVIDENCE'
        coverage.append({**t,'scheduled_fixtures':n,'remaining_prematch_fixtures':remaining,'reason':reason})
    # Fixture volume is observed, not a league-strength assumption. Stable ID tiebreak.
    candidates=sorted([t for t in coverage if t['remaining_prematch_fixtures']],key=lambda t:(-t['remaining_prematch_fixtures'],t['tournament_id']))
    return candidates, {'master_competitions_considered':len(targets),
        'schedule_response_complete':complete,'scheduled_approved_fixtures':sum(counts.values()),
        'scheduled_approved_competitions':len(counts),'remaining_prematch_competitions':len(future),
        'schedule_scope_rejections':dict(rejected),'competition_coverage':coverage}


def finish_coverage(report, requested, audits, errors=False):
    requested=set(map(str,requested)); by_id={}
    for row in audits: by_id.setdefault(str(row.get('tournament_id')),[]).append(row)
    for row in report.get('competition_coverage',[]):
        tid=str(row['tournament_id'])
        if row['reason']!='AWAITING_ODDS':continue
        if tid not in requested:row['reason']='QUOTA_SKIPPED';continue
        evidence=by_id.get(tid,[])
        row['odds_fixture_rows']=len(evidence)
        row['strict_snapshots']=sum(x.get('eligibility_status')=='MATCH' for x in evidence)
        row['market_reason_counts']=dict(Counter(x.get('eligibility_reason') for x in evidence))
        row['reason']='OBSERVED' if row['strict_snapshots'] else 'PROVIDER_ERROR' if errors else 'UNMAPPED' if any('UNMAPPED' in str(x.get('eligibility_reason')) or 'CONFLICT' in str(x.get('eligibility_reason')) for x in evidence) else 'NO_MARKET' if evidence else 'NO_MARKET_RESPONSE'
    report['competition_reason_counts']=dict(Counter(x['reason'] for x in report.get('competition_coverage',[])))
