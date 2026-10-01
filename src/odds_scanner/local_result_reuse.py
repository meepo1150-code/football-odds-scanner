"""Reuse canonical results only through a unique full local identity bridge."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from .daily_fixture_result_backfill import _load_jsonl, _utc
from .oddspapi_result_cache import RESULTS_PATH, merge_normalized_results
SNAPSHOTS = Path('data/normalized/europe_pinnacle_research_v2_snapshots.jsonl')
REPORT = Path('reports/research_v2_local_result_reuse.json')


def identity(row):
    values = tuple(str(row.get(k) or '').strip().casefold() for k in ('home','away','league'))
    kickoff = _utc(row.get('kickoff'))
    return (*values,kickoff.isoformat()) if all(values) and kickoff else None


def run(root=Path('.')):
    snapshots = _load_jsonl(root/SNAPSHOTS)
    results = _load_jsonl(root/RESULTS_PATH)
    blocked = {str(r.get('fixture_id')) for r in _load_jsonl((root/RESULTS_PATH).with_suffix('.conflicts.jsonl'))}
    by_id = {}
    for r in results:
        if type(r.get('ft_home_goals')) is int and type(r.get('ft_away_goals')) is int and min(r['ft_home_goals'],r['ft_away_goals']) >= 0:
            by_id.setdefault(str(r.get('fixture_id')),[]).append(r)
    fixtures = {}; identities = {}
    for s in snapshots:
        fid = str(s.get('fixture_id') or '')
        if fid:
            fixtures[fid] = s
            identities.setdefault(fid,set()).add(identity(s))
    index = {}
    for fid, keys in identities.items():
        if fid in blocked or len(keys) != 1 or None in keys or fid not in by_id: continue
        rs = by_id[fid]
        if len({(r['ft_home_goals'],r['ft_away_goals']) for r in rs}) != 1: continue
        index.setdefault(next(iter(keys)),[]).append(rs[-1])
    missing = set(fixtures)-set(by_id); added=[]; reasons=[]; ambiguous=0
    for fid in sorted(missing):
        if fid in blocked:
            reasons.append({'fixture_id':fid,'reason':'RESULT_CONFLICT_REQUIRES_REVIEW'})
            continue
        keys=identities[fid]
        matches=index.get(next(iter(keys)),[]) if len(keys)==1 and None not in keys else []
        if len(matches) != 1:
            ambiguous += int(len(matches)>1)
            reasons.append({'fixture_id':fid,'reason':'AMBIGUOUS_IDENTITY' if len(matches)>1 else 'NO_VERIFIED_LOCAL_RESULT_WITH_FULL_IDENTITY'})
            continue
        source=matches[0]
        added.append({**source,'fixture_id':fid,'result_identity':'VERIFIED_LOCAL_EXACT_HOME_AWAY_LEAGUE_UTC_KICKOFF_UNIQUE','bridge_source_fixture_id':source['fixture_id'],'bridge_identity':list(next(iter(keys))),'reused_at':datetime.now(timezone.utc).isoformat()})
    count=merge_normalized_results(root/RESULTS_PATH,added)
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'status':'RESULTS_ADDED' if count else 'NO_NEW_VERIFIED_LOCAL_RESULTS','missing_before':len(missing),'results_added':count,'missing_after':len(missing)-count,'exact_matches':0,'verified_bridge_matches':count,'ambiguous':ambiguous,'not_found':len(missing)-count-ambiguous,'requests_used':0,'unresolved':reasons}
    path=root/REPORT;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    report=run();print(json.dumps({k:v for k,v in report.items() if k!='unresolved'}))
