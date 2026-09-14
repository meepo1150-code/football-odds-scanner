from __future__ import annotations

import json
import os
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .europe_bookmaker_coverage_probe import BOOKMAKER, CORE_QUOTA_RESERVE, quota_allows_probe, summarize_rows
from .oddspapi_discovery import _rows
from .oddspapi_provider import ENV_KEY, _get
from .oddspapi_quota_health import summarize_account
from .v2_mainline_observer import CATALOG_PATH, _load_json, extract_mainline_snapshot, mainline_shape

TARGET_PATH = Path('reports/europe_discovery_tournaments.json')
SNAPSHOT_PATH = Path('data/normalized/europe_pinnacle_research_v2_snapshots.jsonl')
AUDIT_PATH = Path('data/normalized/europe_pinnacle_research_v2_audit.jsonl')
REPORT_PATH = Path('reports/europe_pinnacle_research_v2_status.json')
BANGKOK = ZoneInfo('Asia/Bangkok')
FOOTBALL_DAY_START_HOUR = 12
FOOTBALL_DAY_END_HOUR = 6
BATCH_SIZE = 5


def _merge_jsonl(path: Path, new_rows: list[dict], key_fields: tuple[str, ...]) -> int:
    rows = {}
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows[tuple(str(row.get(k)) for k in key_fields)] = row
    for row in new_rows:
        rows[tuple(str(row.get(k)) for k in key_fields)] = row
    ordered = sorted(rows.values(), key=lambda r: tuple(str(r.get(k)) for k in key_fields))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in ordered), encoding='utf-8')
    return len(ordered)


def _football_day_bounds(now_utc: datetime):
    local_now = now_utc.astimezone(BANGKOK)
    label_date = local_now.date() - timedelta(days=1) if local_now.time() < dtime(FOOTBALL_DAY_END_HOUR) else local_now.date()
    start = datetime.combine(label_date, dtime(FOOTBALL_DAY_START_HOUR), BANGKOK)
    end = datetime.combine(label_date + timedelta(days=1), dtime(FOOTBALL_DAY_END_HOUR), BANGKOK)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc), label_date.isoformat()


def _parse_kickoff(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _in_football_day(kickoff, start_utc, end_utc):
    dt = _parse_kickoff(kickoff)
    return dt is not None and start_utc <= dt < end_utc


def _write(report, root):
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def _chunks(values, size):
    for i in range(0, len(values), size):
        yield values[i:i + size]


def run(root: Path = Path('.')):
    now = datetime.now(timezone.utc)
    window_start, window_end, football_day = _football_day_bounds(now)
    report = {
        'schema_version': '2.3',
        'generated_at': now.isoformat(),
        'classification': 'PINNACLE_RESEARCH_V2',
        'bookmaker': BOOKMAKER,
        'football_day': football_day,
        'football_day_timezone': 'Asia/Bangkok',
        'football_day_window_start': window_start.isoformat(),
        'football_day_window_end': window_end.isoformat(),
        'research_only': True,
        'production_promotion_allowed': False,
        'core_quota_reserve': CORE_QUOTA_RESERVE,
        'batch_size': BATCH_SIZE,
        'batching_strategy': 'VERIFIED_TOURNAMENTS_BATCHED',
    }

    targets = _load_json(root / TARGET_PATH) or {}
    selected = targets.get('tournaments') or [] if isinstance(targets, dict) else []
    ids = [x.get('tournament_id') for x in selected if isinstance(x, dict) and x.get('tournament_id') is not None]
    if not ids or len(ids) != len(set(ids)):
        report.update(status='TARGET_MAP_INVALID', resolved_competitions=len(ids), requests_used=0, planned_requests=0)
        return _write(report, root)

    planned = (len(ids) + BATCH_SIZE - 1) // BATCH_SIZE
    report['resolved_competitions'] = len(ids)
    report['planned_requests'] = planned
    report['competition_type_counts'] = {
        t: sum(1 for x in selected if x.get('competition_type', 'LEAGUE') == t)
        for t in sorted({x.get('competition_type', 'LEAGUE') for x in selected})
    }

    key = os.getenv(ENV_KEY, '').strip()
    if not key:
        report['status'] = 'API_KEY_NOT_CONFIGURED'
        report['requests_used'] = 0
        return _write(report, root)
    try:
        quota = summarize_account(_get('/account', key))
    except Exception as exc:
        report.update(status='SKIPPED_QUOTA_HEALTH_UNAVAILABLE', requests_used=0, errors=[f'{type(exc).__name__}: {exc}'])
        return _write(report, root)
    report['quota_remaining_before'] = quota.get('request_remaining')
    if not quota_allows_probe(quota, planned=planned):
        report.update(status='SKIPPED_TO_PROTECT_CORE_QUOTA', requests_used=0)
        return _write(report, root)

    catalog = _load_json(root / CATALOG_PATH) or []
    meta = {int(x['tournament_id']): x for x in selected}
    payloads = []
    requests_used = 0
    for batch_number, batch in enumerate(_chunks(ids, BATCH_SIZE), start=1):
        try:
            payloads.append(_get('/odds-by-tournaments', key, {
                'tournamentIds': ','.join(str(x) for x in batch),
                'bookmakers': BOOKMAKER,
                'language': 'en',
                'verbosity': 3,
            }, 90))
            requests_used += 1
        except Exception as exc:
            report.update(
                status='API_REQUEST_FAILED',
                requests_used=requests_used + 1,
                failed_batch=batch_number,
                failed_batch_size=len(batch),
                errors=[f'{type(exc).__name__}: {exc}'],
            )
            return _write(report, root)

    strict = []
    diagnostics = []
    audit_rows = []
    all_api_fixtures = 0
    excluded = 0
    for payload in payloads:
        for fixture in _rows(payload):
            all_api_fixtures += 1
            if not _in_football_day(fixture.get('startTime'), window_start, window_end):
                excluded += 1
                continue
            tm = {**(meta.get(int(fixture.get('tournamentId') or -1)) or {}), 'universe': 'PINNACLE_RESEARCH_V2'}
            book = (fixture.get('bookmakerOdds') or {}).get(BOOKMAKER)
            active = isinstance(book, dict) and book.get('bookmakerIsActive') is True and book.get('suspended') is False
            shape = mainline_shape(fixture, catalog, bookmaker=BOOKMAKER)
            snapshot, reason = extract_mainline_snapshot(fixture, catalog, observed_at=now, tournament_meta=tm, bookmaker=BOOKMAKER)
            diagnostics.append({
                'country': tm.get('country'),
                'league': tm.get('tournament_name'),
                'fixture_id': fixture.get('fixtureId'),
                'bookmaker_active': active,
                'ah_main_count': shape.get('ah_main_count', 0),
                'ou_main_count': shape.get('ou_main_count', 0),
                'strict_snapshot': snapshot is not None,
                'reason': reason,
            })
            audit_rows.append({
                'football_day': football_day,
                'fixture_id': fixture.get('fixtureId'),
                'tournament_id': fixture.get('tournamentId'),
                'competition_type': tm.get('competition_type', 'LEAGUE'),
                'country': tm.get('country'),
                'league': tm.get('tournament_name'),
                'home': fixture.get('participant1Name'),
                'away': fixture.get('participant2Name'),
                'kickoff': fixture.get('startTime'),
                'observed_at': now.isoformat(),
                'bookmaker': BOOKMAKER,
                'eligibility_status': 'MATCH' if snapshot else 'NOT_MATCH',
                'eligibility_reason': reason,
                'bookmaker_active': active,
                'ah_main_count': shape.get('ah_main_count', 0),
                'ou_main_count': shape.get('ou_main_count', 0),
                'research_population': True,
            })
            if snapshot:
                snapshot.update(football_day=football_day, research_only=True, competition_type=tm.get('competition_type', 'LEAGUE'))
                strict.append(snapshot)

    total_snapshots = _merge_jsonl(root / SNAPSHOT_PATH, strict, ('observed_at', 'fixture_id'))
    total_audit = _merge_jsonl(root / AUDIT_PATH, audit_rows, ('observed_at', 'fixture_id'))
    report.update(
        status='RESEARCH_V2_OBSERVED',
        requests_used=requests_used,
        api_fixtures_returned=all_api_fixtures,
        excluded_outside_football_day=excluded,
        football_day_fixtures=len(audit_rows),
        strict_snapshots_this_run=len(strict),
        non_strict_fixtures_this_run=len(audit_rows) - len(strict),
        persisted_snapshot_rows=total_snapshots,
        persisted_audit_rows=total_audit,
        **summarize_rows(diagnostics),
    )
    return _write(report, root)


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False))
