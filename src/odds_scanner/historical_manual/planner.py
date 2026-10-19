"""Thai football-day planning from exact native provider evidence, without HTTP."""
import hashlib
import json
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BKK = ZoneInfo('Asia/Bangkok')
DAY_POLICY = 'BKK_KICKOFF_BEFORE_0600_PREVIOUS_DAY_V1'
EXTERNAL_FIXTURE_SOURCE = 'data/research/manual_historical_verified_fixtures.jsonl'
SOURCES = (
    'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl',
    'data/normalized/v2_mainline_snapshots.jsonl',
    'data/research/pre_sep14_historical_originals.jsonl',
    'data/research/pre_sep15_17_historical_originals.jsonl',
)


def stamp(value):
    result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('TIMEZONE_REQUIRED')
    return result.astimezone(timezone.utc)


def football_day(kickoff):
    local = stamp(kickoff).astimezone(BKK)
    return local.date() - timedelta(days=1) if local.hour < 6 else local.date()


def parse_days(start, end):
    if not all(re.fullmatch(r'\d{4}-\d{2}-\d{2}', v) for v in (start, end)):
        raise ValueError('DATES_REQUIRE_YYYY_MM_DD')
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if not 0 <= (last-first).days <= 6:
        raise ValueError('RANGE_MUST_BE_1_TO_7_DAYS')
    return [first + timedelta(days=i) for i in range((last-first).days+1)]


def parse_times(value):
    values = value.split(',')
    if not 1 <= len(values) <= 8:
        raise ValueError('SELECT_1_TO_8_TIMES')
    result = []
    for token in values:
        token = token.strip()
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', token):
            raise ValueError('TIMES_REQUIRE_HH_MM')
        result.append(time.fromisoformat(token))
    if len(set(result)) != len(result):
        raise ValueError('DUPLICATE_TARGET_TIME')
    return sorted(result, key=lambda t: (t.hour < 6, t))


def target(day, clock):
    # 01:45 selected for football day 14 means calendar day 15, 01:45 BKK.
    calendar = day + timedelta(days=1) if clock.hour < 6 else day
    return datetime.combine(calendar, clock, BKK)


def request_for(fid, book):
    return {'endpoint': '/v4/historical-odds', 'params': {'fixtureId': fid, 'bookmakers': book}}


def build(root, start, end, times, bookmakers, now):
    days, clocks = parse_days(start, end), parse_times(times)
    books = set(bookmakers.split(','))
    if not books or not books <= {'pinnacle', 'bet365'}:
        raise ValueError('UNSUPPORTED_BOOKMAKER')
    targets = {d: [target(d, t) for t in clocks] for d in days}
    if any(t >= now for ts in targets.values() for t in ts):
        raise ValueError('TARGETS_MUST_BE_IN_THE_PAST')
    by_key, identities, conflicts = {}, {}, set()
    for source in SOURCES:
        path = root/source
        if not path.exists():
            continue
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if (not str(row.get('source_semantics', '')).startswith('CURRENT_ODDSPAPI_')
                    or row.get('data_origin') == 'BACKFILLED'
                    or row.get('bookmaker') not in books):
                continue
            fid = row.get('fixture_id', '')
            if not re.fullmatch(r'id\d+', fid) or not all(row.get(k) for k in ('home', 'away', 'kickoff', 'league')):
                continue
            ko = stamp(row['kickoff'])
            identity = (row['home'], row['away'], ko.isoformat())
            if fid in identities and identities[fid] != identity:
                conflicts.add(fid)
            identities[fid] = identity
            day = football_day(row['kickoff'])
            if day not in targets:
                continue
            key = fid, row['bookmaker']
            c = by_key.setdefault(key, dict(fixture_id=fid, bookmaker=row['bookmaker'],
                home=row['home'], away=row['away'], league=row['league'], kickoff=ko.isoformat(),
                football_day=day.isoformat(), request=request_for(*key), evidence=[], observations=[],
                source_day_labels=[]))
            c['evidence'].append(dict(path=source, line=number,
                sha256=hashlib.sha256(line.encode()).hexdigest()))
            c['observations'].append(row)
            if row.get('football_day') and row['football_day'] not in c['source_day_labels']:
                c['source_day_labels'].append(row['football_day'])
    # Native, SHA-bound provider /fixtures evidence. Never infer OddsPapi
    # fixture IDs from names, match results, or bookmaker pricing.
    from odds_scanner.master_schedule_plan import registry, items
    approved = {str(r['tournament_id']): r for r in registry()}
    # Persisted day-scoped, hash-bound /fixtures receipts provide native
    # identity evidence for dates without original current-day observations.
    discovery_dir = root / 'research/historical_backfill/data/fixture_discovery_receipts'
    receipt_sources = (
        'data/normalized/research_v2_provider_responses.jsonl',
        'data/research/manual_historical_provider_receipts.jsonl',
    ) + tuple(str(p.relative_to(root)) for p in sorted(discovery_dir.glob('*.json')))
    for relative in receipt_sources:
        receipts = root / relative
        if not receipts.exists():
            continue
        from_discovery_cache = relative.startswith('research/historical_backfill/data/fixture_discovery_receipts/')
        is_research_receipt = relative.startswith('data/research/') or from_discovery_cache
        records = ([(1, receipts.read_text(), json.loads(receipts.read_text()))]
                   if from_discovery_cache else
                   [(number, line, json.loads(line)) for number, line in
                    enumerate(receipts.read_text().splitlines(), 1) if line.strip()])
        for number, line, receipt in records:
            if receipt.get('provider') != 'oddspapi' or receipt.get('endpoint') != '/fixtures':
                continue
            if not receipt.get('response_id') or not receipt.get('observed_at'):
                continue
            if is_research_receipt:
                record = {k: v for k, v in receipt.items() if k != 'response_id'}
                actual = hashlib.sha256(json.dumps(record, sort_keys=True,
                    ensure_ascii=False).encode()).hexdigest()
                if receipt['response_id'] != actual:
                    raise ValueError('MANUAL_FIXTURE_RECEIPT_HASH_MISMATCH')
            for fixture in items(receipt.get('payload')):
                fid = str(fixture.get('fixtureId') or '')
                tournament = approved.get(str(fixture.get('tournamentId')))
                if not tournament or not re.fullmatch(r'id\d+', fid):
                    continue
                if is_research_receipt and fixture.get('statusId') != 2:
                    # Historical reconstruction is restricted to finished matches.
                    continue
                home, away, kickoff = (fixture.get('participant1Name'),
                    fixture.get('participant2Name'), fixture.get('startTime'))
                if not home or not away or not kickoff:
                    continue
                ko = stamp(kickoff)
                day = football_day(kickoff)
                if day not in targets:
                    continue
                identity = (home, away, ko.isoformat())
                if fid in identities and identities[fid] != identity:
                    conflicts.add(fid)
                identities[fid] = identity
                for book in sorted(books):
                    key = fid, book
                    if key in by_key:
                        c = by_key[key]
                        if (c['home'], c['away'], c['kickoff']) != identity:
                            raise ValueError('PROVIDER_RECEIPT_FIXTURE_CONFLICT')
                    else:
                        c = dict(fixture_id=fid, bookmaker=book, home=home, away=away,
                            league=tournament['tournament_name'], kickoff=ko.isoformat(),
                            football_day=day.isoformat(), request=request_for(*key),
                            evidence=[], observations=[], source_day_labels=[])
                        by_key[key] = c
                    c['evidence'].append(dict(path=relative, line=number,
                        sha256=hashlib.sha256(line.encode()).hexdigest(),
                        mapping_source='ODDSPAPI_NATIVE_FIXTURES_RECEIPT',
                        response_id=receipt['response_id']))
    # Independently verified historical fixture identities. These are not live
    # snapshots; require explicit OddsPapi identity evidence and league provenance.
    external = root / EXTERNAL_FIXTURE_SOURCE
    if external.exists():
        for number, line in enumerate(external.read_text().splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            required = ('fixture_id', 'bookmaker', 'home', 'away', 'league',
                        'kickoff', 'mapping_source', 'evidence_url')
            if any(not row.get(k) for k in required):
                raise ValueError('EXTERNAL_FIXTURE_EVIDENCE_INCOMPLETE')
            fid, book = row['fixture_id'], row['bookmaker']
            if row.get('football_day') and row['football_day'] != football_day(row['kickoff']).isoformat():
                raise ValueError('EXTERNAL_FOOTBALL_DAY_CONFLICT')
            if (not re.fullmatch(r'id\d+', fid) or book not in {'pinnacle', 'bet365'}
                    or not str(row['mapping_source']).startswith('ODDSPAPI_')
                    or not str(row['evidence_url']).startswith('https://')):
                raise ValueError('EXTERNAL_FIXTURE_EVIDENCE_INVALID')
            ko = stamp(row['kickoff'])
            identity = (row['home'], row['away'], ko.isoformat())
            if fid in identities and identities[fid] != identity:
                conflicts.add(fid)
            identities[fid] = identity
            day = football_day(row['kickoff'])
            if day not in targets or book not in books:
                continue
            key = fid, book
            if key in by_key:
                c = by_key[key]
                if (c['home'], c['away'], c['league'], c['kickoff']) != (
                        row['home'], row['away'], row['league'], ko.isoformat()):
                    raise ValueError('EXTERNAL_FIXTURE_CONFLICT')
            else:
                c = dict(fixture_id=fid, bookmaker=book, home=row['home'],
                    away=row['away'], league=row['league'], kickoff=ko.isoformat(),
                    football_day=day.isoformat(), request=request_for(*key),
                    evidence=[], observations=[], source_day_labels=[])
                by_key[key] = c
            c['evidence'].append(dict(path=EXTERNAL_FIXTURE_SOURCE, line=number,
                sha256=hashlib.sha256(line.encode()).hexdigest(),
                evidence_url=row['evidence_url'], mapping_source=row['mapping_source']))
    if conflicts & {c['fixture_id'] for c in by_key.values()}:
        raise ValueError('EXACT_IDENTITY_CONFLICT')
    candidates = sorted(by_key.values(), key=lambda c: (c['football_day'], c['fixture_id'], c['bookmaker']))
    for c in candidates:
        ts = targets[date.fromisoformat(c['football_day'])]
        c['targets'] = [dict(target_thai=t.isoformat(), target_utc=t.astimezone(timezone.utc).isoformat(),
            status='PENDING' if t < stamp(c['kickoff']) else 'NOT_PREMATCH_SLOT') for t in ts]
        c['source_day_conflict'] = any(d != c['football_day'] for d in c['source_day_labels'])
    return dict(schema_version=1, timezone='Asia/Bangkok', day_policy=DAY_POLICY,
        start_day=start, end_day=end, target_times_thai=times, scope='VERIFIED_NATIVE_OR_EXTERNAL_ODDSPAPI_FIXTURES',
        full_provider_universe_claimed=False, unique_fixtures=len({c['fixture_id'] for c in candidates}),
        fixture_bookmaker_pairs=len(candidates), candidates=candidates)
