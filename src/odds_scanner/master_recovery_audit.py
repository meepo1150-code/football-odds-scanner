"""Network-free ID and stored-schedule replay; source records remain immutable."""
import hashlib
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from .master_mapping import load_mappings, enrich_fixture
from .master_schedule_plan import plan


def audit(root=Path('.')):
    mappings=load_mappings(root/'data/master/provider_mappings.csv')
    clubs={r['club_id']:r for r in csv.DictReader((root/'data/master/uefa_clubs_canonical.csv').open())}
    snapshot=json.loads((root/'reports/master_provider_snapshot.json').read_text())
    participants=snapshot['participants']; catalog={str(r['tournamentId']):r for r in snapshot['tournaments']}
    club_rows=[];competition_rows=[]
    for (provider,kind,pid),cid in sorted(mappings.items()):
        row={'provider':provider,'provider_id':pid,'canonical_id':cid}
        if kind=='club':
            row.update(canonical_name=clubs.get(cid,{}).get('canonical_name'),provider_name=participants.get(pid),canonical_exists=cid in clubs,provider_exists=pid in participants)
            club_rows.append(row)
        elif kind=='competition':
            row.update(provider_name=catalog.get(pid,{}).get('tournamentName'),provider_country=catalog.get(pid,{}).get('categoryName'),provider_exists=pid in catalog)
            competition_rows.append(row)
    from .europe_pinnacle_discovery import _football_day_bounds
    now=datetime.now(timezone.utc);ws,we,day=_football_day_bounds(now)
    _,scope=plan(snapshot['fixtures'],ws,we,now,complete=False)
    replay=Counter();details=[]
    source=root/'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl'
    for line in source.read_text().splitlines():
        row=json.loads(line)
        try:
            enriched=enrich_fixture(row,provider='oddspapi',mappings=mappings)
            status='EXACT_CANONICAL_IDS_AVAILABLE' if all(enriched.get(k) for k in ('canonical_competition_id','home_club_id','away_club_id')) else 'CANONICAL_UNMAPPED_PROVIDER_LOCAL_ONLY'
            if row.get('football_day')==day:details.append({'fixture_id':row['fixture_id'],'observed_at':row['observed_at'],'status':status,**{k:enriched.get(k) for k in ('tournament_id','canonical_competition_id','home_participant_id','home_club_id','away_participant_id','away_club_id')}})
        except ValueError:status='CANONICAL_ID_CONFLICT'
        replay[status]+=1
    report={'generated_at':now.isoformat(),'football_day':day,'http_requests':0,'club_mappings_checked':len(club_rows),'competition_mappings_checked':len(competition_rows),'evidence_files_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ('data/master/provider_mappings.csv','data/master/research/provider_mapping_audit_2026_10_09.json','reports/master_provider_snapshot.json')},'missing_club_canonical_ids':[r for r in club_rows if not r['canonical_exists']],'missing_provider_club_ids':[r for r in club_rows if not r['provider_exists']],'missing_provider_competition_ids':[r for r in competition_rows if not r['provider_exists']],'stored_snapshot_replay':dict(replay),'today_identity_replay':details,'saved_schedule_replay':scope,'raw_odds_response_replay_limitation':'Saved master fixtures are schedule/identity only; prior collector retained normalized quotes, not full bookmakerOdds responses. Missing historical prices cannot be reconstructed. New full responses are append-only and replayable.','fixture_id_policy':'Provider fixture IDs preserved; canonical club IDs never substituted for participant or fixture IDs.','production_ready':False}
    out=root/'reports/master_recovery_audit_2026_10_12.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report

if __name__=='__main__':
    r=audit();print(json.dumps({k:v for k,v in r.items() if k not in {'club_mapping_details','competition_mapping_details','today_identity_replay','saved_schedule_replay'}}))
