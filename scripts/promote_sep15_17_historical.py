"""Offline, reversible promotion of the exact reviewed Sep15–17 football-day run.

Only validated fixture/bookmaker/date cohorts with usable history are replaced.
Every removed original line is retained verbatim in a production archive.
"""
import argparse
import hashlib
import json
import math
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def dt(value):
    parsed=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timezone required')
    return parsed

def football_day(kickoff):
    local=dt(kickoff).astimezone(ZoneInfo('Asia/Bangkok'))
    return (local-timedelta(days=1) if local.hour<6 else local).date().isoformat()

SOURCE = Path('data/normalized/europe_pinnacle_research_v2_snapshots.jsonl')
NATIVE = Path('data/normalized/v2_mainline_snapshots.jsonl')
ARCHIVE = Path('data/research/pre_sep15_17_historical_originals.jsonl')
RECEIPT = Path('reports/sep15_17_historical_promotion.json')
PROVENANCE = 'ODDSPAPI_RECONSTRUCTED_FROM_RUN_38867737713'
DAYS = {'2026-09-15', '2026-09-16', '2026-09-17'}
EXPECTED_CANDIDATES = 58
EXPECTED_ROWS = 169
EXPECTED_BY_DAY = {'2026-09-15':70,'2026-09-16':51,'2026-09-17':48}
REPORT_SHA256 = '5e26b19cbadf699184e2031aade034402dc670bb841c9a0f23a7f90ed65bab53'
MANIFEST_SHA256 = 'e142e20915ba3d6044d0c4b8f677db3c0b6dd1b508dcdf27e3cd21d9614f2994'

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def read_rows(raw):
    return [json.loads(line) for line in raw.decode().splitlines() if line.strip()]

def key(row):
    return str(row['fixture_id']), row['bookmaker']

def plan(report, manifest, canonical, native):
    if (report.get('status') != 'COMPLETED' or report.get('errors')
            or report.get('production_writes') != 0 or report.get('production_quota_delta') != 0):
        raise ValueError('Unclean research report')
    candidates = manifest['candidates']
    if len(candidates) != EXPECTED_CANDIDATES or len(report['results']) != EXPECTED_CANDIDATES:
        raise ValueError('Unexpected candidate count')
    candidates = {key(c): c for c in candidates}
    results = {key(r): r for r in report['results']}
    if len(candidates) != EXPECTED_CANDIDATES or set(candidates) != set(results):
        raise ValueError('Duplicate or mismatched fixture/bookmaker identities')
    templates = defaultdict(list)
    for row in canonical + native:
        if 'bookmaker' in row:
            templates[key(row)].append(row)
    generated = []
    skipped = Counter()
    for identity, c in sorted(candidates.items()):
        day = c['football_day']
        if day not in DAYS or football_day(c['kickoff']) != day:
            raise ValueError('Football-day mismatch')
        expected = (c['home'], c['away'], dt(c['kickoff']), c['league'])
        original = templates.get(identity, [])
        if not original or any((r.get('home'), r.get('away'), dt(r['kickoff']), r.get('league')) != expected for r in original):
            raise ValueError('Missing or conflicting original identity: '+repr(identity))
        base = original[-1]
        slots = results[identity]['slots']
        midnight = dt(day+'T00:00:00+07:00')
        allowed = {midnight+timedelta(hours=h) for h in (15,18,21,24)}
        if (len(slots) != 4 or {dt(s['slot_utc']) for s in slots} != allowed
                or {s['slot_utc'] for s in slots} != set(c['all_requested_rounds'])):
            raise ValueError('Slot manifest mismatch')
        for slot in slots:
            if slot['status'] != 'BALANCED_LINE':
                skipped[slot['status']] += 1
                continue
            selected = slot['selected']
            home, away = (selected['quotes'][s] for s in ('home', 'away'))
            line, hp, ap = selected['line'], home['price'], away['price']
            if any(type(v) not in (int, float) or not math.isfinite(v) for v in (line, hp, ap)):
                raise ValueError('Non-finite or non-numeric quote')
            target, kickoff = dt(slot['slot_utc']), dt(c['kickoff'])
            ht, at = dt(home['quote_at_utc']), dt(away['quote_at_utc'])
            if (selected.get('status') != 'COMPLETE' or key(selected) != identity
                    or selected.get('line_selection') != 'BALANCED_LINE'
                    or selected.get('market') != 'AH' or not selected.get('catalog_evidence')
                    or slot.get('official_mainline_verified') is not False
                    or any(q.get('active') is not True for q in (home, away))
                    or abs(line*4-round(line*4)) > 1e-8
                    or not (1.8 <= hp <= 2.2 and 1.8 <= ap <= 2.2)
                    or not (ht <= target < kickoff and at <= target)
                    or max((target-ht).total_seconds(), (target-at).total_seconds()) > 3600):
                raise ValueError('Untrusted historical quote')
            # Signed home AH explicitly identifies the giving side for nonzero lines.
            # A level AH retains the original verified cohort side, not invented 1X2.
            fav = 'H' if line < 0 else 'A' if line > 0 else base.get('favorite_side')
            if fav not in ('H', 'A'):
                raise ValueError('Unresolved level-AH side')
            row = dict(base)
            row.update(provider='oddspapi', football_day=day,
                observed_at=max(ht, at).isoformat(), scheduled_target_at=slot['slot_utc'],
                historical_target_slot_at=slot['slot_utc'], historical_quote_home_at=ht.isoformat(),
                historical_quote_away_at=at.isoformat(), historical_provenance=PROVENANCE,
                historical_market_id=selected['market_id'], historical_raw_record_hash=selected['raw_record_hash'],
                historical_timestamp_basis='PROVIDER_HISTORY_ENTRY_CREATED_AT_NOT_LIVE_COLLECTION',
                source_semantics='HISTORICAL_BALANCED_LINE_AS_OF_SLOT', data_origin='BACKFILLED',
                mainline_verified=False, promotion_eligible=False, research_only=True,
                one_x_two={}, ou={}, favorite_fair_probability=None, favorite_side=fav,
                favorite_side_basis='SIGNED_AH_GIVING_SIDE' if line else 'ORIGINAL_OBSERVED_COHORT_SIDE_LEVEL_AH',
                ah=dict(home_line=line, away_line=-line, home_price=hp, away_price=ap,
                    selected_side_line=line if fav == 'H' else -line,
                    selected_side_price=hp if fav == 'H' else ap,
                    opposite_side_price=ap if fav == 'H' else hp))
            # Never carry a present-time scan receipt into a reconstructed slot.
            for field in ('scan_id', 'scan_run_id', 'schedule_lag_minutes', 'actual_observed_at'):
                row.pop(field, None)
            generated.append(row)
    if len(generated) != EXPECTED_ROWS or Counter(r['football_day'] for r in generated) != EXPECTED_BY_DAY:
        raise ValueError('Reviewed 169-slot population changed')
    identities = {(key(r), r['football_day']) for r in generated}
    return generated, identities, dict(skipped)

def promote(report, manifest, root, dry_run=False):
    raw = (root/SOURCE).read_bytes()
    canonical = read_rows(raw)
    generated, identities, skipped = plan(report, manifest, canonical, read_rows((root/NATIVE).read_bytes()))
    serialized = [json.dumps(r, ensure_ascii=False, separators=(',', ':'))+'\n' for r in generated]
    existing = [r for r in canonical if r.get('historical_provenance') == PROVENANCE]
    if existing:
        if sorted(json.dumps(r,sort_keys=True) for r in existing) != sorted(json.dumps(r,sort_keys=True) for r in generated):
            raise ValueError('Conflicting existing promotion; no overwrite')
        if not (root/RECEIPT).exists():
            raise ValueError('Existing promotion without receipt')
        return {**json.loads((root/RECEIPT).read_text()), 'idempotent_noop':True}
    kept, archived = [], []
    for line in raw.decode().splitlines(keepends=True):
        if not line.strip():
            kept.append(line); continue
        row = json.loads(line)
        replace = 'bookmaker' in row and (key(row),row.get('football_day')) in identities
        (archived if replace else kept).append(line)
    archive_before = (root/ARCHIVE).read_bytes() if (root/ARCHIVE).exists() else b''
    if archive_before:
        raise ValueError('Archive already exists without canonical promotion')
    removed = ''.join(archived).encode()
    proposed = ''.join(kept+serialized).encode()
    receipt = dict(status='PROMOTED', source_run=38867737713, dates=sorted(DAYS),
        historical_balanced_slots=len(generated), by_day=dict(Counter(r['football_day'] for r in generated)),
        promoted_fixture_bookmaker_pairs=len(identities), promoted_unique_fixtures=len({r['fixture_id'] for r in generated}),
        skipped_slot_counts=skipped, archived_original_rows=len(archived), archive_path=str(ARCHIVE),
        original_file_sha256=digest(raw), archived_original_sha256=digest(removed),
        retained_original_sha256=digest(''.join(kept).encode()), promoted_file_sha256=digest(proposed),
        historical_api_requests=0, formula_changed=False, official_mainline_claimed=False,
        missing_1x2_ou_not_imputed=True)
    if not dry_run:
        (root/ARCHIVE).parent.mkdir(parents=True,exist_ok=True)
        (root/ARCHIVE).write_bytes(removed)
        (root/SOURCE).write_bytes(proposed)
        (root/RECEIPT).write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

def main():
    p=argparse.ArgumentParser();p.add_argument('--artifact',type=Path,required=True)
    p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--dry-run',action='store_true')
    args=p.parse_args()
    with zipfile.ZipFile(args.artifact) as z:
        raw_report=z.read('sep15_17_matchdays/results/batch-0/report.json')
        raw_manifest=z.read('sep15_17_matchdays/manifest.json')
        if digest(raw_report)!=REPORT_SHA256 or digest(raw_manifest)!=MANIFEST_SHA256:
            raise ValueError('Pinned research artifact hash mismatch')
        report=json.loads(raw_report)
        manifest=json.loads(raw_manifest)
    print(json.dumps(promote(report,manifest,args.root,args.dry_run),indent=2))

if __name__=='__main__':main()
