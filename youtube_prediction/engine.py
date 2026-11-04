"""Offline, fail-closed prediction archive and exact-ID Asian settlement."""
import fcntl
import hashlib
import json
import math
import os
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Asia/Bangkok')

def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def iso_time(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('Timestamp requires UTC offset')
    return result

def label(p):
    if p['market'] == 'AH':
        return f"{p['home'] if p['selection'] == 'HOME' else p['away']} {p['line']:+g} AH"
    return f"{p['selection'].title()} {p['line']:g} goals"

def validate(data):
    date.fromisoformat(data['date'])
    published = iso_time(data['published_at'])
    if data.get('source_type') != 'REVIEWED_PREDICTION':
        raise ValueError('Explicit reviewed input required; synthetic production is forbidden')
    if not isinstance(data.get('predictions'), list):
        raise ValueError('predictions must be a list')
    ids, markets = set(), set()
    for p in data['predictions']:
        for key in ('id', 'fixture_id', 'home', 'away', 'kickoff'):
            if not isinstance(p.get(key), str) or not p[key].strip():
                raise ValueError('Missing ' + key)
        if p['id'] in ids:
            raise ValueError('Duplicate prediction ID')
        ids.add(p['id'])
        market = p.get('market')
        if market not in ('AH', 'OU') or p.get('selection') not in ({'HOME', 'AWAY'} if market == 'AH' else {'OVER', 'UNDER'}):
            raise ValueError('Unsupported market or selection')
        line = p.get('line')
        if type(line) not in (float, int) or not math.isfinite(line) or line * 4 != int(line * 4) or (market == 'OU' and line < 0):
            raise ValueError('Finite quarter-grid line required')
        key = (p['fixture_id'], market)
        if key in markets:
            raise ValueError('Only one selection per fixture and market')
        markets.add(key)
        if iso_time(p['kickoff']) <= published:
            raise ValueError('Prediction at/after kickoff')
        if iso_time(p['kickoff']).astimezone(TZ).date() not in (date.fromisoformat(data['date']), date.fromisoformat(data['date']) + timedelta(days=1)):
            raise ValueError('Kickoff outside episode day window')
    return 'REVIEWED'

def read_ledger(path):
    rows, previous, ids, markets = [], '0' * 64, set(), set()
    if not Path(path).exists():
        return rows
    for line in Path(path).read_text().splitlines():
        row = json.loads(line)
        payload = {k: v for k, v in row.items() if k != 'hash'}
        if row['previous_hash'] != previous or fingerprint(payload) != row['hash']:
            raise ValueError('Ledger hash chain failed')
        p = row['prediction']
        key = (p['fixture_id'], p['market'])
        if p['id'] in ids or key in markets:
            raise ValueError('Duplicate ledger prediction')
        if iso_time(row['recorded_at']) >= iso_time(p['kickoff']):
            raise ValueError('Late ledger prediction')
        ids.add(p['id']); markets.add(key)
        previous = row['hash']; rows.append(row)
    return rows

def verify_fixtures(data, fixtures):
    index = {}
    needed = {p['fixture_id'] for p in data['predictions']}
    for f in fixtures:
        if f['fixture_id'] not in needed:
            continue
        fid = f['fixture_id']
        identity = (f['home'], f['away'], iso_time(f['kickoff']))
        if fid in index and index[fid] != identity:
            raise ValueError('Conflicting fixture identity: ' + fid)
        index[fid] = identity
    for p in data['predictions']:
        if index.get(p['fixture_id']) != (p['home'], p['away'], iso_time(p['kickoff'])):
            raise ValueError('Unverified fixture identity: ' + p['fixture_id'])

def append_ledger(path, data, fixtures=()):
    validate(data)
    verify_fixtures(data, fixtures)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with Path(str(path) + '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        rows = read_ledger(path)
        existing = {r['prediction']['id']: r for r in rows}
        markets = {(r['prediction']['fixture_id'], r['prediction']['market']) for r in rows}
        now = datetime.now(timezone.utc)
        if iso_time(data['published_at']) > now:
            raise ValueError('Future claimed publication timestamp')
        additions = []
        previous = rows[-1]['hash'] if rows else '0' * 64
        for original in data['predictions']:
            p = {k: original[k] for k in ('id','fixture_id','home','away','kickoff','market','selection','line')}
            if p['id'] in existing:
                old = existing[p['id']]
                if old['prediction'] != p or old['date'] != data['date'] or old['published_at'] != data['published_at']:
                    raise ValueError('Immutable prediction conflict')
                continue
            if (p['fixture_id'], p['market']) in markets:
                raise ValueError('Fixture market already archived')
            if iso_time(p['kickoff']) <= now:
                raise ValueError('Cannot backdate a prediction')
            row = dict(prediction=p, date=data['date'], published_at=data['published_at'], recorded_at=now.isoformat(), previous_hash=previous)
            row['hash'] = fingerprint(row); previous = row['hash']; additions.append(row)
        if additions:
            with path.open('a') as handle:
                handle.write(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in additions))
                handle.flush(); os.fsync(handle.fileno())
        return len(additions)

def settle(p, home, away):
    line = p['line']
    legs = [line] if int(line * 4) % 2 == 0 else [line - .25, line + .25]
    scores = []
    for leg in legs:
        value = ((home-away) if p['selection'] == 'HOME' else (away-home)) + leg if p['market'] == 'AH' else ((home+away-leg) * (1 if p['selection'] == 'OVER' else -1))
        scores.append((value > 0) - (value < 0))
    return {-1:'FULL_LOSS', -.5:'HALF_LOSS', 0:'PUSH', .5:'HALF_WIN', 1:'FULL_WIN'}[sum(scores)/len(scores)]

def result_index(results):
    index = {}
    for r in results:
        fid = r['fixture_id']
        if not r.get('result_source'):
            raise ValueError('FT provenance missing')
        score = (r.get('ft_home_goals'), r.get('ft_away_goals'))
        if any(type(n) is not int or n < 0 for n in score):
            raise ValueError('Explicit nonnegative FT scores required')
        if fid in index and index[fid] != score:
            raise ValueError('Conflicting FT: ' + fid)
        index[fid] = score
    return index

def summarize(rows, results, episode_date):
    scores = result_index(results)
    yesterday = (date.fromisoformat(episode_date) - timedelta(days=1)).isoformat()
    eligible = [r for r in rows if r['date'] < episode_date]
    def group(records):
        output = {}
        for market in ('AH', 'OU'):
            counts = {k:0 for k in ('FULL_WIN','HALF_WIN','PUSH','HALF_LOSS','FULL_LOSS','PENDING')}
            for r in records:
                p = r['prediction']
                if p['market'] == market:
                    counts[settle(p,*scores[p['fixture_id']]) if p['fixture_id'] in scores else 'PENDING'] += 1
            won = counts['FULL_WIN'] + .5 * counts['HALF_WIN']
            lost = counts['FULL_LOSS'] + .5 * counts['HALF_LOSS']
            output[market] = dict(counts=counts, decisive_units=won+lost, wr=won/(won+lost) if won+lost else None)
        return output
    details = []
    for r in eligible:
        if r['date'] == yesterday:
            p = r['prediction']; score = scores.get(p['fixture_id'])
            details.append(dict(**p, ft=score, settlement=settle(p,*score) if score else 'PENDING'))
    return dict(yesterday=yesterday, details=details, daily=group([r for r in eligible if r['date']==yesterday]), cumulative=group(eligible), wr_definition='(full wins + 0.5 half wins) / (full wins + 0.5 half wins + full losses + 0.5 half losses); pushes and pending excluded')
