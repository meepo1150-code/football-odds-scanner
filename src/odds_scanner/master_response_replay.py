"""Replay retained odds without HTTP, preserving original response observation times."""
import json
from pathlib import Path
from .master_schedule_plan import RAW_PATH, items, stamp, registry
from .v2_mainline_observer import extract_mainline_snapshot, CATALOG_PATH
from .europe_pinnacle_discovery import SNAPSHOT_PATH,_football_day_bounds
from .master_scan_scope import scan_scope_reason
from .research_population import in_scope


def run(root=Path('.')):
    catalog=json.loads((root/CATALOG_PATH).read_text())
    meta={str(t['tournament_id']):t for t in registry()}
    rows=[json.loads(x) for x in (root/RAW_PATH).read_text().splitlines()] if (root/RAW_PATH).exists() else []
    existing=[json.loads(x) for x in (root/SNAPSHOT_PATH).read_text().splitlines()] if (root/SNAPSHOT_PATH).exists() else []
    keys={(r.get('fixture_id'),stamp(r.get('observed_at'))) for r in existing}
    snapshots=[];quarantine=[]
    for response in rows:
        if response.get('endpoint')!='/odds-by-tournaments':continue
        observed=stamp(response.get('observed_at'))
        if observed is None:continue
        ws,we,day=_football_day_bounds(observed)
        requested=set(str(response.get('params',{}).get('tournamentIds','')).split(','))
        try:fixtures=items(response.get('payload'))
        except ValueError:continue
        for f in fixtures:
            tid=str(f.get('tournamentId'));ko=stamp(f.get('startTime'));fid=f.get('fixtureId')
            if tid not in requested or tid not in meta or scan_scope_reason(f,provider='oddspapi') or not ko or not ws<=ko<we:continue
            if (fid,observed) in keys:continue
            try:snap,reason=extract_mainline_snapshot(f,catalog,observed_at=observed,tournament_meta=meta[tid],bookmaker='pinnacle')
            except ValueError:snap=None;reason='MASTER_CANONICAL_ID_CONFLICT'
            if snap and not all(snap.get(k) for k in ('canonical_competition_id','home_club_id','away_club_id')):snap=None;reason='MASTER_CLUB_UNMAPPED'
            if not snap or not in_scope(snap):
                quarantine.append({'provider_fixture_id':fid,'observed_at':observed.isoformat(),'response_id':response.get('response_id'),'reason':reason});continue
            snap.update(football_day=day,research_only=True,replayed_from_response_id=response.get('response_id'))
            snapshots.append(snap);keys.add((fid,observed))
    if snapshots:
        path=root/SNAPSHOT_PATH;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('a') as handle:
            for snap in snapshots:handle.write(json.dumps(snap,ensure_ascii=False,separators=(',',':'))+'\n')
    report={'http_requests':0,'results_added':len(snapshots),'raw_responses_checked':len(rows),'quarantined':quarantine,'observation_timestamp_policy':'ORIGINAL_RESPONSE_RECEIPT_TIME_ONLY','source_history_rewritten':False}
    p=root/'reports/master_response_replay.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False))
