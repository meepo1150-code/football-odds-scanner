"""Multi-day manifest preparation from local pinned production evidence only."""
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from research.historical_backfill.candidates import select_candidates
from research.historical_backfill.reconstruct import parse_time

BKK = ZoneInfo('Asia/Bangkok')


def age_band(age):
    return '0_7' if age <= 7 else '8_14' if age <= 14 else '15_30' if age <= 30 else 'OUTSIDE_30'


def add_exact_football_days(rows, fixtures):
    """Fill missing football_day only from an unambiguous exact-ID cached record."""
    lookup = defaultdict(set)
    for r in fixtures:
        lookup[(r.get('fixture_id'), parse_time(r['kickoff']))].add(r['football_day'])
    out = []
    for r in rows:
        if r.get('football_day'):
            out.append(r); continue
        days = lookup[(r.get('fixture_id'), parse_time(r['kickoff']))]
        if len(days) == 1:
            out.append({**r, 'football_day': next(iter(days)),
                        'football_day_evidence': 'EXACT_ID_KICKOFF_DAILY_FIXTURE_CACHE'})
    return out


def build_manifest(snapshots, fixtures, results, mappings, competitions, excluded,
                   calibration, *, as_of, lookback_days=30, maximum=100):
    if not 14 <= lookback_days <= 30 or not 50 <= maximum <= 100:
        raise ValueError('lookback must be 14..30 and maximum 50..100')
    now = parse_time(as_of).astimezone(BKK)
    if len(calibration) != 10 or len({c['fixture_id'] for c in calibration}) != 10:
        raise ValueError('ten distinct calibration fixtures required')
    rows = add_exact_football_days(snapshots, fixtures)
    source_args = (fixtures, results, mappings, competitions, excluded)
    calibrated = []
    for old in calibration:
        matches = [r for r in rows if r['fixture_id'] == old['fixture_id']
                   and r['bookmaker'] == old['bookmaker']]
        current, _, _ = select_candidates(matches, *source_args, limit=1)
        if not current or any(current[0][k] != old[k] for k in
                              ('fixture_id', 'bookmaker', 'home', 'away', 'tournament_id')):
            raise ValueError('calibration mapping failed: ' + old['fixture_id'])
        if parse_time(current[0]['kickoff']) != parse_time(old['kickoff']):
            raise ValueError('calibration kickoff conflict')
        calibrated.append({**current[0], 'phase': 'CALIBRATION',
                           'original_manifest_preserved': True})
    eligible_rows = []
    for r in rows:
        age = (now.date() - datetime.fromisoformat(r['football_day']).date()).days
        if 1 <= age <= lookback_days and parse_time(r['kickoff']) < now:
            eligible_rows.append(r)
    expanded, rejected, groups = select_candidates(eligible_rows, *source_args, limit=maximum)
    seen = {c['fixture_id'] for c in calibrated}
    chosen = calibrated.copy()
    for c in expanded:
        if c['fixture_id'] not in seen and len(chosen) < maximum:
            chosen.append({**c, 'phase': 'EXPANSION_PENDING_CALIBRATION'})
            seen.add(c['fixture_id'])
    for c in chosen:
        age = (now.date() - datetime.fromisoformat(c['football_day']).date()).days
        c.update(age_days=age, age_band=age_band(age),
                 kickoff_hour_bangkok=parse_time(c['kickoff']).astimezone(BKK).hour)
    pending = [c for c in chosen if c['phase'] != 'CALIBRATION']
    return dict(schema_version='2.0', as_of=as_of, lookback_days=lookback_days,
        limit=maximum, status='PREPARED_NOT_EXECUTED', candidates=chosen,
        calibration_count=10, expansion_count=len(pending),
        unique_fixture_count=len(seen), eligible_fixture_bookmaker_groups=groups,
        rejections=rejected, age_bands=dict(Counter(c['age_band'] for c in chosen)),
        cumulative_windows={str(n): sum(1 <= c['age_days'] <= n for c in chosen) for n in (7,14,30)},
        days=sorted({c['football_day'] for c in chosen}),
        leagues=dict(Counter(c['league'] for c in chosen)),
        bookmakers=dict(Counter(c['bookmaker'] for c in chosen)),
        kickoff_hours_bangkok=dict(Counter(str(c['kickoff_hour_bangkok']) for c in chosen)),
        target_slots=sum(len(c['missing_rounds']) for c in chosen),
        requested_minimum_reached=len(chosen)>=50,
        original_calibration_outside_window=[c['fixture_id'] for c in calibrated if c['age_days']>lookback_days],
        data_gap_bands=[b for b in ('0_7','8_14','15_30') if not any(c['age_band']==b for c in chosen)])


def read_rows(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--fixtures', required=True)
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--maximum', type=int, default=100)
    parser.add_argument('--lookback-days', type=int, default=30)
    args=parser.parse_args(); root=Path(args.root).resolve()
    paths=[root/'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl',
           root/'data/normalized/v2_mainline_snapshots.jsonl',Path(args.fixtures).resolve(),
           root/'data/normalized/oddspapi_finished_results.jsonl',
           root/'data/master/provider_mappings.csv',root/'data/master/competitions.csv',
           root/'config/league_selection_v1.json']
    baseline=json.loads((root/'research/historical_backfill/reports/multiday_baseline.json').read_text())
    logical_paths=['data/normalized/europe_pinnacle_research_v2_snapshots.jsonl',
                   'data/normalized/v2_mainline_snapshots.jsonl',
                   'data/normalized/research_v2_daily_fixtures.jsonl',
                   'data/normalized/oddspapi_finished_results.jsonl',
                   'data/master/provider_mappings.csv','data/master/competitions.csv',
                   'config/league_selection_v1.json']
    for logical,path in zip(logical_paths,paths):
        data=path.read_bytes()
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if blob!=baseline['input_git_blobs'][logical]:
            raise ValueError('Input no longer matches pinned multi-day baseline: '+logical)
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    calibration=json.loads((root/'research/historical_backfill/reports/candidate_manifest.json').read_text())
    report=build_manifest(read_rows(paths[0])+read_rows(paths[1]),read_rows(paths[2]),read_rows(paths[3]),
        list(csv.DictReader(paths[4].open())),list(csv.DictReader(paths[5].open())),
        json.loads(paths[6].read_text())['user_excluded_competition_ids'],calibration,
        as_of=args.as_of,lookback_days=args.lookback_days,maximum=args.maximum)
    assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    report['input_sha256']={p.name:before[str(p)] for p in paths}
    report['baseline_sha']=baseline['baseline_sha']
    dest=root/'research/historical_backfill/reports/multiday_manifest.json'
    dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('candidates','input_sha256','rejections')},indent=2))


if __name__=='__main__':main()
