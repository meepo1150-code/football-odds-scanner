from __future__ import annotations

import json
import os
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .europe_bookmaker_coverage_probe import BOOKMAKER, CORE_QUOTA_RESERVE, EXPECTED, quota_allows_probe, summarize_rows
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


def _merge_jsonl(path: Path, new_rows: list[dict], key_fields: tuple[str, ...]) -> int:
    rows: dict[tuple[str, ...], dict] = {}
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


def _football_day_bounds(now_utc: datetime) -> tuple[datetime, datetime, str]:
    local_now = now_utc.astimezone(BANGKOK)
    if local_now.time() < dtime(FOOTBALL_DAY_END_HOUR, 0):
        label_date = local_now.date() - timedelta(days=1)
    else:
        label_date = local_now.date()
    start_local = datetime.combine(label_date, dtime(FOOTBALL_DAY_START_HOUR, 0), BANGKOK)
    end_local = datetime.combine(label_date + timedelta(days=1), dtime(FOOTBALL_DAY_END_HOUR, 0), BANGKOK)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc), label_date.isoformat()


def _parse_kickoff(value: object) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _in_football_day(kickoff: object, start_utc: datetime, end_utc: datetime) -> bool:
    dt = _parse_kickoff(kickoff)
    return dt is not None and start_utc <= dt < end_utc


def _write(report: dict, root: Path) -> dict:
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def run(root: Path = Path('.')) -> dict:
    now = datetime.now(timezone.utc)
    window_start, window_end, football_day = _football_day_bounds(now)
    report = {
        'schema_version': '2.1', 'generated_at': now.isoformat(),
        'classification': 'PINNACLE_RESEARCH_V2', 'bookmaker': BOOKMAKER,
        'football_day': football_day, 'football_day_timezone': 'Asia/Bangkok',
        'football_day_window_start': window_start.isoformat(), 'football_day_window_end': window_end.isoformat(),
        'research_only': True, 'production_promotion_allowed': False,
        'core_quota_reserve': CORE_QUOTA_RESERVE, 'planned_requests': 1,
        'batching_strategy': 'ALL_SELECTED_TOURNAMENTS_ONE_REQUEST',
    }
    key = os.getenv(ENV_KEY, '').strip()
    if not key:
        report['status'] = 'API_KEY_NOT_CONFIGURED'; return _write(report, root)
    try:
        quota = summarize_account(_get('/account', key))
    except Exception as exc:
        report.update(status='SKIPPED_QUOTA_HEALTH_UNAVAILABLE', requests_used=0, errors=[f'{type(exc).__name__}: {exc}']); return _write(report, root)
    report['quota_remaining_before'] = quota.get('request_remaining')
    if not quota_allows_probe(quota):
        report.update(status='SKIPPED_TO_PROTECT_CORE_QUOTA', requests_used=0); return _write(report, root)

    targets = _load_json(root / TARGET_PATH) or {}
    selected = targets.get('tournaments') or [] if isinstance(targets, dict) else []
    if len(selected) != EXPECTED:
        report.update(status='TARGET_MAP_INCOMPLETE', resolved_leagues=len(selected), requests_used=0); return _write(report, root)
    catalog = _load_json(root / CATALOG_PATH) or []
    meta = {int(x['tournament_id']): x for x in selected}

    # OddsPAPI counts a billable endpoint call, not fixtures returned. The endpoint accepts
    # comma-separated tournamentIds, so keep the entire 15-league universe in one request.
    try:
        payload = _get('/odds-by-tournaments', key, {
            'tournamentIds': ','.join(str(x['tournament_id']) for x in selected),
            'bookmakers': BOOKMAKER, 'language': 'en', 'verbosity': 3,
        }, 60)
    except Exception as exc:
        report.update(status='API_REQUEST_FAILED', requests_used=1, errors=[f'{type(exc).__name__}: {exc}']); return _write(report, root)

    strict, diagnostics, audit_rows = [], [], []
    all_api_fixtures = excluded_outside_window = 0
    for fixture in _rows(payload):
        all_api_fixtures += 1
        if not _in_football_day(fixture.get('startTime'), window_start, window_end):
            excluded_outside_window += 1; continue
        tm = {**(meta.get(int(fixture.get('tournamentId') or -1)) or {}), 'universe': 'PINNACLE_RESEARCH_V2'}
        book = (fixture.get('bookmakerOdds') or {}).get(BOOKMAKER)
        bookmaker_active = isinstance(book, dict) and book.get('bookmakerIsActive') is True and book.get('suspended') is False
        shape = mainline_shape(fixture, catalog, bookmaker=BOOKMAKER)
        snapshot, reason = extract_mainline_snapshot(fixture, catalog, observed_at=now, tournament_meta=tm, bookmaker=BOOKMAKER)
        diagnostics.append({'country': tm.get('country'), 'league': tm.get('tournament_name'), 'fixture_id': fixture.get('fixtureId'), 'bookmaker_active': bookmaker_active, 'ah_main_count': shape.get('ah_main_count', 0), 'ou_main_count': shape.get('ou_main_count', 0), 'strict_snapshot': snapshot is not None, 'reason': reason})
        audit_rows.append({'football_day': football_day, 'fixture_id': fixture.get('fixtureId'), 'tournament_id': fixture.get('tournamentId'), 'country': tm.get('country'), 'league': tm.get('tournament_name'), 'home': fixture.get('participant1Name'), 'away': fixture.get('participant2Name'), 'kickoff': fixture.get('startTime'), 'observed_at': now.isoformat(), 'bookmaker': BOOKMAKER, 'eligibility_status': 'MATCH' if snapshot is not None else 'NOT_MATCH', 'eligibility_reason': reason, 'bookmaker_active': bookmaker_active, 'ah_main_count': shape.get('ah_main_count', 0), 'ou_main_count': shape.get('ou_main_count', 0), 'research_population': True, 'interpretation': 'All fixtures in the Bangkok football-day window are retained for research. MATCH is descriptive metadata only.'})
        if snapshot:
            snapshot['football_day'] = football_day; snapshot['research_only'] = True; strict.append(snapshot)

    total_snapshots = _merge_jsonl(root / SNAPSHOT_PATH, strict, ('observed_at', 'fixture_id'))
    total_audit = _merge_jsonl(root / AUDIT_PATH, audit_rows, ('observed_at', 'fixture_id'))
    report.update(status='RESEARCH_V2_OBSERVED', resolved_leagues=len(selected), requests_used=1, api_fixtures_returned=all_api_fixtures, excluded_outside_football_day=excluded_outside_window, football_day_fixtures=len(audit_rows), strict_snapshots_this_run=len(strict), non_strict_fixtures_this_run=len(audit_rows)-len(strict), persisted_snapshot_rows=total_snapshots, persisted_audit_rows=total_audit, **summarize_rows(diagnostics), interpretation='Day-scoped research population. Every selected-league fixture in the Bangkok football-day window is counted; strict status is a feature, not a recommendation.')
    return _write(report, root)


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False))
