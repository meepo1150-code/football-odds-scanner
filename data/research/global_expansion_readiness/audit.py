"""Read-only audit of all 33 staged leagues against real collector receipts.

No provider transport, activation, history writes or production mapping imports.
A successful API response is not proof of complete fixture or odds coverage.
"""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from odds_scanner.master_schedule_plan import items, stamp, RAW_PATH, SCHEDULE_LIMIT
from odds_scanner.research_request_budget import allocation

IDENTITY=Path('data/research/global_expansion_readiness/identity_review.json')
OUT=Path('reports/global_expansion_readiness.json')
BANGKOK=ZoneInfo('Asia/Bangkok')


def load_rows(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()] if path.exists() else []


def memberships(root):
    rows=[]
    for directory in ('global_master_phase1','global_master_phase2','thailand_membership_completion'):
        with (root/'data/research'/directory/'verified_memberships.csv').open() as f:
            rows.extend(csv.DictReader(f))
    return rows


def select_schedule(responses, start, end, target, now):
    eligible=[]
    for row in responses:
        p=row.get('params',{});observed=stamp(row.get('observed_at'))
        if (row.get('provider')!='oddspapi' or row.get('endpoint')!='/fixtures'
            or p.get('sportId')!=10 or any(p.get(k) for k in ('participantId','tournamentId','tournamentIds'))
            or stamp(p.get('from'))!=start or stamp(p.get('to'))!=end
            or not observed or not target<=observed<=now):continue
        try:items(row.get('payload'))
        except ValueError:continue
        eligible.append(row)
    return max(eligible,key=lambda r:stamp(r['observed_at']),default=None)


def audit(root=Path('.'), *, now=None, football_day=None, identity=None, responses=None, snapshots=None, member_rows=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError('Aware clock required')
    day=football_day or now.astimezone(BANGKOK).date().isoformat()
    from odds_scanner.europe_pinnacle_discovery import _football_day_bounds
    # The canonical research football day is noon to next-day 06:00 Bangkok.
    reference=datetime.fromisoformat(day+'T15:00:00+07:00')
    start,end,_=_football_day_bounds(reference)
    target=reference.astimezone(timezone.utc)
    identity=identity if identity is not None else json.loads((root/IDENTITY).read_text())
    member_rows=member_rows if member_rows is not None else memberships(root)
    responses=responses if responses is not None else load_rows(root/RAW_PATH)
    snapshots=snapshots if snapshots is not None else load_rows(root/'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl')
    members=defaultdict(set);names={}
    for m in member_rows:members[m['competition_id']].add(m['club_id']);names[m['club_id']]=m['source_name']
    competitions=identity['competitions'];clubs={c['club_id']:c for c in identity['clubs']}
    if len(competitions)!=33 or len(clubs)!=588 or set(members)!={c['competition_id'] for c in competitions}:
        raise ValueError('Expansion scope must account for exactly 33 leagues and 588 club identities')
    if len(member_rows)!=588 or sum(len(ms) for ms in members.values())!=588:
        raise ValueError('Expansion memberships must be complete and unique')
    if any(c not in clubs for ms in members.values() for c in ms):raise ValueError('Membership lacks canonical club ID')
    verified={cid for cid,c in clubs.items() if c['status']=='VERIFIED_CACHED_PARTICIPANT_IDENTITY' and c.get('provider_id')}
    owners=defaultdict(set)
    for cid in verified:owners[str(clubs[cid]['provider_id'])].add(cid)
    if any(len(cs)!=1 for cs in owners.values()):raise ValueError('Conflicting provider participant ownership')
    pid_to_club={pid:next(iter(cs)) for pid,cs in owners.items() if len(cs)==1}
    schedule=select_schedule(responses,start,end,target,now)
    fixtures=items(schedule['payload']) if schedule else []
    params=schedule.get('params',{}) if schedule else {}
    limit=params.get('limit',SCHEDULE_LIMIT)
    complete=(schedule is not None and isinstance(schedule['payload'],list) and
              type(limit) is int and 0<len(fixtures)<limit)
    # An empty list cannot distinguish no scheduled matches from provider coverage gaps.
    if schedule is not None and isinstance(schedule['payload'],list) and not fixtures:
        complete=True
    versions=defaultdict(set)
    for f in fixtures:
        versions[str(f.get('fixtureId'))].add(json.dumps(f,sort_keys=True))
    conflicts={fid for fid,vs in versions.items() if len(vs)>1}
    rows=[]
    for comp in competitions:
        cid=comp['competition_id'];ms=members[cid]
        comp_ok=comp['status']=='VERIFIED_CACHED_COMPETITION_IDENTITY' and comp.get('provider_id') is not None
        candidate_ids={str(a['provider_id']) for a in comp['alternatives']}
        eligible={str(comp['provider_id'])} if comp_ok else set()
        observations=[];seen=set()
        for f in fixtures:
            tid=str(f.get('tournamentId'));ko=stamp(f.get('startTime'));fid=str(f.get('fixtureId') or '')
            if tid not in candidate_ids or not ko or not start<=ko<end or fid in seen:continue
            seen.add(fid);failures=[];sides=[]
            if not fid:failures.append('MISSING_FIXTURE_ID')
            if fid in conflicts:failures.append('CONFLICTING_FIXTURE_VERSIONS')
            if tid not in eligible:failures.append('COMPETITION_ID_UNVERIFIED')
            expected_names={a['provider_name'] for a in comp['alternatives'] if str(a['provider_id'])==tid}
            if f.get('tournamentName') not in expected_names:failures.append('PROVIDER_COMPETITION_NAME_CHANGED')
            for side in (1,2):
                pid=str(f.get(f'participant{side}Id',''));club=pid_to_club.get(pid)
                if not club:failures.append('UNVERIFIED_PARTICIPANT_'+str(side))
                elif club not in ms:failures.append('PARTICIPANT_OUTSIDE_CURRENT_ROSTER_'+str(side))
                else:
                    known={o['provider_name'] for o in clubs[club]['observations']}
                    if f.get(f'participant{side}Name') not in known:failures.append('PROVIDER_NAME_CHANGED_'+str(side))
                sides.append(dict(provider_id=pid,club_id=club,provider_name=f.get(f'participant{side}Name')))
            if sides[0]['provider_id']==sides[1]['provider_id'] or sides[0]['club_id'] and sides[0]['club_id']==sides[1]['club_id']:
                failures.append('DUPLICATE_SIDE_IDENTITY')
            observations.append(dict(fixture_id=fid,tournament_id=tid,kickoff=ko.isoformat(),
                provider_status_id=f.get('statusId'),
                sides=sides,mapping_status='PASS' if not failures else 'BLOCKED',reasons=failures))
        requested=[]
        for receipt in responses:
            t=stamp(receipt.get('observed_at'))
            if receipt.get('provider')=='oddspapi' and receipt.get('endpoint')=='/odds-by-tournaments' and t and target<=t<=now:
                ids={x.strip() for x in str(receipt.get('params',{}).get('tournamentIds','')).split(',')}
                if ids & eligible:requested.append(receipt.get('response_id'))
        fixture_ids={o['fixture_id'] for o in observations if o['mapping_status']=='PASS'}
        price_rows=[s for s in snapshots if str(s.get('fixture_id')) in fixture_ids and
            str(s.get('tournament_id')) in eligible and s.get('source_semantics')=='CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED'
            and s.get('mainline_verified') is True and stamp(s.get('observed_at')) and target<=stamp(s['observed_at'])<=now]
        missing=sorted(ms-verified)
        if not schedule:status='WAITING_1500_FIXTURE_RESPONSE'
        elif any(o['mapping_status']!='PASS' for o in observations):status='FIXTURE_MAPPING_BLOCKED'
        elif not complete:status='PARTIAL_FIXTURE_RESPONSE'
        elif not observations:status='NO_FIXTURES_RETURNED_NOT_PROOF_OF_NO_MATCHES'
        else:status='RETURNED_FIXTURE_IDENTITIES_MATCHED'
        rows.append(dict(competition_id=cid,competition_name=comp['competition_name'],
            canonical_clubs=len(ms),canonical_club_ids=sorted(ms),provider_mapped_clubs=len(ms & verified),
            provider_unresolved_clubs=[dict(club_id=c,canonical_name=names[c],reason=clubs[c]['reason']) for c in missing],
            competition_identity_verified=bool(comp_ok),candidate_tournament_ids=sorted(candidate_ids),
            verified_tournament_id=comp.get('provider_id'),full_roster_identity_verified=bool(comp_ok and not missing),
            schedule_status=status,returned_fixtures=len(observations),matched_fixtures=sum(o['mapping_status']=='PASS' for o in observations),
            fixture_details=observations,odds_request_receipts=requested,valid_odds_fixtures=len({s['fixture_id'] for s in price_rows}),
            price_status='VALID_ODDS_OBSERVED' if price_rows else 'REQUESTED_NO_VALID_ODDS_OBSERVED' if requested else 'NOT_REQUESTED_FOR_EXPANSION',
            provider_season_stage_verified=False,activation_allowed=False))
    unresolved=sum(len(r['provider_unresolved_clubs']) for r in rows)
    proposed=[c['provider_id'] for c in competitions if c.get('provider_id')]
    _,budget=allocation(root/'data/normalized/research_v2_slot_ledger.jsonl',proposed,now,prioritized=True,manual=True)
    available=math.ceil(len(budget['coverage_tournament_ids'])/5)
    required=math.ceil(len(competitions)/5)
    gate_reasons=[]
    if unresolved or any(not r['competition_identity_verified'] for r in rows):gate_reasons.append('INCOMPLETE_PROVIDER_IDENTITIES')
    if available<required:gate_reasons.append('FULL_SCOPE_PRICE_PROBE_EXCEEDS_PROTECTED_QUOTA')
    if not schedule:gate_reasons.append('NO_1500_FIXTURE_RESPONSE_YET')
    if schedule and not complete:gate_reasons.append('FIXTURE_RESPONSE_NOT_COMPLETE')
    if any(r['matched_fixtures']<r['returned_fixtures'] for r in rows):gate_reasons.append('UNMATCHED_RETURNED_FIXTURES')
    return dict(schema_version='1.0',generated_at=now.isoformat(),football_day=day,
        expected_scan_target=reference.isoformat(),provider='oddspapi',provider_requests_used=0,
        transport_policy='REUSE_CANONICAL_SCAN_RESPONSES_ONLY_NO_EXTRA_API_CALLS',
        phase3_expansion_allowed=False,activation_allowed=False,
        counts=dict(leagues=len(rows),clubs=len(clubs),provider_verified_competitions=sum(r['competition_identity_verified'] for r in rows),
            provider_mapped_clubs=len(verified),provider_unresolved_clubs=unresolved,
            complete_roster_leagues=sum(r['full_roster_identity_verified'] for r in rows),
            returned_fixtures=sum(r['returned_fixtures'] for r in rows),matched_fixtures=sum(r['matched_fixtures'] for r in rows)),
        schedule_response_id=schedule.get('response_id') if schedule else None,
        schedule_observed_at=schedule.get('observed_at') if schedule else None,
        schedule_response_complete=complete,
        full_scope_live_test_gate=dict(allowed=not gate_reasons,reasons=gate_reasons,
            minimum_odds_requests=required,available_optional_odds_requests=available,
            protected_future_requests=budget['future_utc_requests_reserved']),
        leagues=rows,limitations=['No fixtures returned does not prove a league has no matches or no provider coverage.',
            'Fixture identity is separate from current odds coverage and provider season/stage.',
            'Only staged clubs with corroborated participant IDs can match; no fuzzy names, ID inference or activation.'])


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--football-day');p.add_argument('--output',default=str(OUT));a=p.parse_args()
    result=audit(football_day=a.football_day);path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('counts','full_scope_live_test_gate','schedule_observed_at')},indent=2))


if __name__=='__main__':main()
