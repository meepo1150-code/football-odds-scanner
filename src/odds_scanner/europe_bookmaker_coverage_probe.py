from __future__ import annotations

import json
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .oddspapi_discovery import _rows
from .oddspapi_provider import ENV_KEY, _get
from .oddspapi_quota_health import summarize_account
from .v2_mainline_observer import CATALOG_PATH, _load_json, extract_mainline_snapshot, mainline_shape

TARGET_PATH = Path('reports/europe_discovery_tournaments.json')
REPORT_PATH = Path('reports/europe_pinnacle_coverage_probe.json')
BOOKMAKER = 'pinnacle'
EXPECTED = 15
BATCH_SIZE = 5
REQUESTS_PLANNED = 3
CORE_QUOTA_RESERVE = 30
COOLDOWN = 1.25


def quota_allows_probe(summary: dict, *, reserve: int = CORE_QUOTA_RESERVE, planned: int = REQUESTS_PLANNED) -> bool:
    if summary.get('status') != 'QUOTA_AVAILABLE':
        return False
    try:
        remaining = int(summary.get('request_remaining'))
    except (TypeError, ValueError):
        return False
    return remaining - planned >= reserve


def summarize_rows(rows: list[dict]) -> dict:
    overall_reasons = Counter()
    leagues = defaultdict(lambda: {
        'fixtures': 0,
        'bookmaker_active': 0,
        'ah_main_exactly_one': 0,
        'ou_main_exactly_one': 0,
        'both_main_exactly_one': 0,
        'strict_snapshots': 0,
        'reason_counts': Counter(),
    })
    for row in rows:
        reason = str(row.get('reason') or 'UNKNOWN')
        overall_reasons[reason] += 1
        key = f"{row.get('country') or ''} · {row.get('league') or '—'}"
        x = leagues[key]
        x['fixtures'] += 1
        if row.get('bookmaker_active'):
            x['bookmaker_active'] += 1
        ah_count = int(row.get('ah_main_count') or 0)
        ou_count = int(row.get('ou_main_count') or 0)
        if ah_count == 1:
            x['ah_main_exactly_one'] += 1
        if ou_count == 1:
            x['ou_main_exactly_one'] += 1
        if ah_count == 1 and ou_count == 1:
            x['both_main_exactly_one'] += 1
        if row.get('strict_snapshot'):
            x['strict_snapshots'] += 1
        x['reason_counts'][reason] += 1

    return {
        'fixtures_seen': len(rows),
        'bookmaker_active_fixtures': sum(1 for r in rows if r.get('bookmaker_active')),
        'fixtures_with_exactly_one_main_ah': sum(1 for r in rows if int(r.get('ah_main_count') or 0) == 1),
        'fixtures_with_exactly_one_main_ou': sum(1 for r in rows if int(r.get('ou_main_count') or 0) == 1),
        'fixtures_with_both_exact_mainlines': sum(1 for r in rows if int(r.get('ah_main_count') or 0) == 1 and int(r.get('ou_main_count') or 0) == 1),
        'strict_snapshots': sum(1 for r in rows if r.get('strict_snapshot')),
        'rejection_counts': dict(sorted(overall_reasons.items())),
        'league_coverage': [
            {
                'league': key,
                'fixtures': x['fixtures'],
                'bookmaker_active': x['bookmaker_active'],
                'ah_main_exactly_one': x['ah_main_exactly_one'],
                'ou_main_exactly_one': x['ou_main_exactly_one'],
                'both_main_exactly_one': x['both_main_exactly_one'],
                'strict_snapshots': x['strict_snapshots'],
                'reason_counts': dict(sorted(x['reason_counts'].items())),
            }
            for key, x in sorted(leagues.items())
        ],
    }


def _write(report: dict, root: Path = Path('.')) -> dict:
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def run(root: Path = Path('.')) -> dict:
    now = datetime.now(timezone.utc)
    report = {
        'schema_version': '1.0',
        'generated_at': now.isoformat(),
        'classification': 'EUROPE_DISCOVERY_ONLY',
        'purpose': 'ALTERNATE_BOOKMAKER_MARKET_COVERAGE_PROBE',
        'bookmaker': BOOKMAKER,
        'production_promotion_allowed': False,
        'validation_gate_effect': 'NONE',
        'candidate_matching_allowed': False,
        'cross_bookmaker_price_equivalence_allowed': False,
        'core_quota_reserve': CORE_QUOTA_RESERVE,
        'planned_requests': REQUESTS_PLANNED,
    }
    key = os.getenv(ENV_KEY, '').strip()
    if not key:
        report['status'] = 'API_KEY_NOT_CONFIGURED'
        return _write(report, root)

    try:
        quota = summarize_account(_get('/account', key))
    except Exception as exc:
        report.update(status='SKIPPED_QUOTA_HEALTH_UNAVAILABLE', errors=[f'{type(exc).__name__}: {exc}'])
        return _write(report, root)
    report['quota_remaining_before'] = quota.get('request_remaining')
    if not quota_allows_probe(quota):
        report.update(status='SKIPPED_TO_PROTECT_CORE_QUOTA', requests_used=0)
        return _write(report, root)

    targets = _load_json(root / TARGET_PATH) or {}
    selected = targets.get('tournaments') or [] if isinstance(targets, dict) else []
    if len(selected) != EXPECTED:
        report.update(status='TARGET_MAP_INCOMPLETE', resolved_leagues=len(selected), requests_used=0)
        return _write(report, root)

    catalog = _load_json(root / CATALOG_PATH) or []
    diagnostic_rows: list[dict] = []
    requests = 0
    last_finished = None
    for start in range(0, len(selected), BATCH_SIZE):
        batch = selected[start:start + BATCH_SIZE]
        if last_finished is not None:
            wait = COOLDOWN - (time.monotonic() - last_finished)
            if wait > 0:
                time.sleep(wait)
        payload = _get('/odds-by-tournaments', key, {
            'tournamentIds': ','.join(str(x['tournament_id']) for x in batch),
            'bookmakers': BOOKMAKER,
            'language': 'en',
            'verbosity': 3,
        }, 30)
        requests += 1
        last_finished = time.monotonic()
        meta = {int(x['tournament_id']): x for x in batch}
        for fixture in _rows(payload):
            tm = {**(meta.get(int(fixture.get('tournamentId') or -1)) or {}), 'universe': 'EUROPE_DISCOVERY_ALT_BOOKMAKER'}
            book = (fixture.get('bookmakerOdds') or {}).get(BOOKMAKER)
            bookmaker_active = isinstance(book, dict) and book.get('bookmakerIsActive') is True and book.get('suspended') is False
            shape = mainline_shape(fixture, catalog, bookmaker=BOOKMAKER)
            snapshot, reason = extract_mainline_snapshot(
                fixture,
                catalog,
                observed_at=now,
                tournament_meta=tm,
                bookmaker=BOOKMAKER,
            )
            diagnostic_rows.append({
                'country': tm.get('country'),
                'league': tm.get('tournament_name'),
                'fixture_id': fixture.get('fixtureId'),
                'bookmaker_active': bookmaker_active,
                'ah_main_count': shape.get('ah_main_count', 0),
                'ou_main_count': shape.get('ou_main_count', 0),
                'strict_snapshot': snapshot is not None,
                'reason': reason,
            })

    report.update(
        status='PROBE_COMPLETE',
        resolved_leagues=len(selected),
        requests_used=requests,
        **summarize_rows(diagnostic_rows),
        interpretation=(
            'Coverage probe only. Pinnacle observations are not interchangeable with Bet365 prices, do not match frozen candidate price bands, '
            'and cannot enter Validation v2 or production. A positive result only shows alternate-bookmaker AH/O-U market availability.'
        ),
    )
    return _write(report, root)


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False))
