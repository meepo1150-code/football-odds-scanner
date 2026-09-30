"""Data-level operational status, independent from successful workflow execution."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from .europe_pinnacle_discovery import _football_day_bounds
from .research_v2_integrity import trusted_snapshot
from .research_v2_pattern_stats import _result_index, _rows


def load(root, name):
    p=root/'reports'/f'{name}.json'
    return json.loads(p.read_text()) if p.exists() else {}


def utc(value):
    try:
        d=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (ValueError, TypeError): return None


def build(root=Path('.'), now=None):
    now=now or datetime.now(timezone.utc)
    stats=load(root,'research_v2_pattern_statistics')
    move=load(root,'research_v2_movement_status')
    quota=load(root,'oddspapi_quota_health')
    legacy=load(root,'legacy_propline_recovery')
    forward=load(root,'v2_forward_readiness')
    sync=load(root,'research_v2_daily_sync_status')
    path=root/'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl'
    raw=[json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []
    valid=[x for x in raw if trusted_snapshot(x)]
    today=_football_day_bounds(now)[2]
    day_scans=[x for x in valid if x.get('football_day')==today]
    providers={}
    for name in ('pinnwire','propline'):
        p=load(root,f'{name}_research_v2_status')
        when=utc(p.get('generated_at'))
        fresh=when is not None and 0<=(now-when).total_seconds()<=18*3600
        usable=p.get('status')=='RESEARCH_V2_OBSERVED' and not p.get('errors') and fresh
        providers[name]={'status':p.get('data_source_health') or p.get('status','UNKNOWN'), 'capability':'FALLBACK' if name=='propline' else 'RESEARCH_ONLY', 'usable_recent_output':usable,'generated_at':p.get('generated_at'),'errors':p.get('errors',[]),'execution_ready':False}
    providers['oddspapi']={'status':quota.get('status','UNKNOWN'),'request_limit':quota.get('request_limit'),'request_count':quota.get('request_count'),'request_remaining':quota.get('request_remaining'),'generated_at':quota.get('generated_at'),'capability':'WAITING_EXTERNAL_DATA' if quota.get('quota_exhausted') else 'REQUIRES_CURRENT_VALIDATION'}
    counts={'raw_snapshots':len(raw),'verified_snapshots':len(valid),'quarantined_snapshots':len(raw)-len(valid),'recovered_legacy_snapshots':legacy.get('recovered',0),'unresolved_ft_fixtures':stats.get('raw_unresolved_ft_fixtures'),'settled_statistical_fixtures':stats.get('settled_fixtures'),'core_price_settled_fixtures':stats.get('core_price_settled_fixtures'),'movement_fixtures':move.get('fixtures_with_two_plus_snapshots'),'numeric_movement_deltas':move.get('numeric_delta_fields_built'),'current_day_valid_scans':len(day_scans),'current_day_distinct_scan_times':len({x.get('observed_at') for x in day_scans})}
    results, _ = _result_index(_rows(root/'data/normalized/oddspapi_finished_results.jsonl'))
    for row in _rows(root/'data/normalized/oddspapi_finished_results.conflicts.jsonl'):
        results.pop(str(row.get('fixture_id')),None)
    missing = {str(s.get('fixture_id')):s for s in valid if str(s.get('fixture_id')) not in results}
    counts['unresolved_matured_3h_fixtures'] = sum(1 for s in missing.values() if utc(s.get('kickoff')) and (now-utc(s['kickoff'])).total_seconds() >= 10800)
    counts['unresolved_future_or_recent_fixtures'] = len(missing)-counts['unresolved_matured_3h_fixtures']
    failures=[]
    if stats.get('raw_snapshot_rows') != len(raw):failures.append('STATISTICS_RAW_COUNT_STALE')
    if stats.get('snapshot_rows') != len(valid):failures.append('STATISTICS_VERIFIED_COUNT_STALE')
    if stats.get('quarantined_snapshot_rows') != len(raw)-len(valid):failures.append('QUARANTINE_COUNT_MISMATCH')
    if move.get('source_snapshot_rows') != len(valid):failures.append('MOVEMENT_INPUT_STALE')
    ready=[{'candidate_id':c.get('candidate_id'),'settled':c.get('settled_entries'),'minimum':150,'status':c.get('status'),'production_promotion_allowed':c.get('production_promotion_allowed',False)} for c in forward.get('candidates',[])]
    result={'schema_version':'1.1','football_day':today,'generated_at':now.isoformat(),'workflow_success_is_not_data_source_health':True,'status':'BROKEN_DATA_ASSERTIONS' if failures else ('COLLECTING_WITH_EXTERNAL_BLOCKERS' if any(p.get('usable_recent_output') for p in providers.values()) else 'WAITING_EXTERNAL_DATA'),'data_assertions_passed':not failures,'assertion_failures':failures,'counts':counts,'providers':providers,'daily_sync_status':sync.get('status','UNKNOWN'),'forward_candidates':ready,'paper_label':'PAPER_RESEARCH_ONLY','production_promotion_allowed':False,'legacy_recovery_status':legacy.get('status','UNKNOWN'),'dashboard_browser_verified':False}
    p=root/'reports/research_v2_operational_audit.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    r=build(); print(json.dumps(r))
    if not r['data_assertions_passed']:raise SystemExit(1)
