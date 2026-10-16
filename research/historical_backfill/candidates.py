"""Exact-ID candidate selection from pinned local evidence. No provider calls."""
import csv
from collections import defaultdict
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from research.historical_backfill.reconstruct import parse_time, finite

BKK = ZoneInfo('Asia/Bangkok')


def planned_slots(day, kickoff):
    day = datetime.fromisoformat(day).date()
    slots = [datetime.combine(day, time(h), BKK) for h in (15, 18, 21)]
    slots.append(datetime.combine(day + timedelta(days=1), time(0), BKK))
    return [s.isoformat() for s in slots if s < parse_time(kickoff)]


def select_candidates(snapshots, fixtures, results, mappings, competitions, excluded, limit=10):
    if not 1 <= limit <= 100:
        raise ValueError('pilot limit must be 1..100; acquisition is separately staged')
    by_id, ft, groups = defaultdict(list), defaultdict(list), defaultdict(list)
    for r in fixtures:
        by_id[str(r.get('fixture_id'))].append(r)
    for r in results:
        ft[str(r.get('fixture_id'))].append(r)
    approved = {r['competition_id'] for r in competitions if r['status'] == 'VERIFIED_OFFICIAL'} - set(excluded)
    ids = defaultdict(set)
    for r in mappings:
        if r['provider'] == 'oddspapi' and r['entity_type'] == 'competition' and r['internal_id'] in approved and r['verification_status'].startswith('VERIFIED'):
            ids[str(r['provider_id'])].add(r['internal_id'])
    rejects = defaultdict(int)
    for r in snapshots:
        fid = str(r.get('fixture_id', ''))
        if not fid.startswith('id') or r.get('source_semantics') != 'CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED' or r.get('mainline_verified') is not True:
            rejects['NOT_EXACT_OBSERVED_ODDSPAPI'] += 1; continue
        tid = str(r.get('tournament_id'))
        if len(ids[tid]) != 1:
            rejects['NOT_APPROVED_EXACT_COMPETITION'] += 1; continue
        if r.get('canonical_competition_id') not in (None,next(iter(ids[tid]))):
            rejects['CANONICAL_COMPETITION_CONFLICT'] += 1; continue
        exact = [f for f in by_id[fid] if str(f.get('tournament_id')) == tid
                 and f.get('home') == r.get('home') and f.get('away') == r.get('away')
                 and parse_time(f['kickoff']) == parse_time(r['kickoff'])]
        identities = {(str(f.get('tournament_id')), f.get('home'), f.get('away'), parse_time(f['kickoff'])) for f in by_id[fid]}
        if not exact or len(identities) != 1:
            rejects['MAPPING_MISSING_OR_CONFLICT'] += 1; continue
        ah = r.get('ah', {})
        nums = [ah.get(k) for k in ('home_line', 'away_line', 'home_price', 'away_price')]
        if not all(finite(v) for v in nums) or abs(nums[0]*4-round(nums[0]*4))>1e-8 or abs(nums[0]+nums[1])>1e-8 or min(nums[2:])<=1:
            rejects['INVALID_AH'] += 1; continue
        if parse_time(r['observed_at']) >= parse_time(r['kickoff']):
            rejects['POST_KICKOFF'] += 1; continue
        groups[(fid, r['bookmaker'])].append(r)
    eligible = []
    for (fid, book), obs in groups.items():
        r = obs[0]
        identity = {(v['home'], v['away'], parse_time(v['kickoff']), str(v['tournament_id']), v['football_day']) for v in obs}
        if len(identity) != 1:
            rejects['OBSERVED_IDENTITY_CONFLICT'] += 1; continue
        slots = planned_slots(r['football_day'], r['kickoff'])
        # No clock-hour guess: only explicit target evidence counts as an observed round.
        existing = sorted({parse_time(v['scheduled_target_at']).isoformat() for v in obs if v.get('scheduled_target_at')
                           and 0 <= (parse_time(v['observed_at']) - parse_time(v['scheduled_target_at'])).total_seconds() <= 9000})
        all_existing = existing
        requested = {parse_time(s).isoformat() for s in slots}
        existing = [s for s in all_existing if s in requested]
        missing = [s for s in slots if parse_time(s).isoformat() not in existing]
        if not missing: continue
        scores = {(v.get('ft_home_goals'), v.get('ft_away_goals')) for v in ft[fid]
                  if type(v.get('ft_home_goals')) is int and type(v.get('ft_away_goals')) is int
                  and min(v['ft_home_goals'],v['ft_away_goals'])>=0 and v.get('result_source')}
        ft_status = 'VERIFIED_EXACT_ID' if len(scores)==1 else 'FT_CONFLICT' if scores else 'FT_MISSING'
        eligible.append(dict(fixture_id=fid, tournament_id=r['tournament_id'],
            canonical_competition_id=next(iter(ids[str(r['tournament_id'])])), league=r['league'], home=r['home'],away=r['away'],
            kickoff=r['kickoff'],football_day=r['football_day'],bookmaker=book,
            existing_rounds=existing, other_observed_rounds=[s for s in all_existing if s not in requested], missing_rounds=missing, observed_snapshot_count=len({v['observed_at'] for v in obs}),
            unassigned_observations=sorted({v['observed_at'] for v in obs if not v.get('scheduled_target_at')}),
            ft_status=ft_status,ft_score=list(next(iter(scores))) if len(scores)==1 else None,
            ft_sources=sorted({str(v.get('result_source')) for v in ft[fid]}),
            mapping_confidence='EXACT_ID_TEAMS_KICKOFF_TOURNAMENT',
            request=dict(endpoint='/v4/historical-odds',params=dict(fixtureId=fid,bookmakers=book)),
            slot_interpretation='RECOVERY_TARGET' if r['football_day']>='2026-10-13' else 'COUNTERFACTUAL_FOUR_SLOT_RESEARCH'))
    # Greedy diversity: dates, leagues, missing shapes, then singleton snapshots.
    # A fixture can enter once across bookmakers. Newer evidence breaks ties.
    selected=[]; seen=set(); days=set(); leagues=set(); patterns=set()
    while len(selected)<limit:
        pool=[r for r in eligible if r['fixture_id'] not in seen]
        if not pool:break
        r=max(pool,key=lambda r:(r['football_day'] not in days,
            r['canonical_competition_id'] not in leagues,
            len(r['missing_rounds']) not in patterns,
            r['observed_snapshot_count']==1,r['football_day'],r['fixture_id']))
        selected.append(r);seen.add(r['fixture_id']);days.add(r['football_day'])
        leagues.add(r['canonical_competition_id']);patterns.add(len(r['missing_rounds']))
    return selected,dict(rejects),len(eligible)
