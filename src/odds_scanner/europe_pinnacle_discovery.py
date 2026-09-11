from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from .europe_bookmaker_coverage_probe import BOOKMAKER, CORE_QUOTA_RESERVE, EXPECTED, quota_allows_probe, summarize_rows
from .oddspapi_discovery import _rows
from .oddspapi_provider import ENV_KEY, _get
from .oddspapi_quota_health import summarize_account
from .v2_mainline_observer import CATALOG_PATH, _load_json, extract_mainline_snapshot, mainline_shape

TARGET_PATH = Path('reports/europe_discovery_tournaments.json')
SNAPSHOT_PATH = Path('data/normalized/europe_pinnacle_discovery_snapshots.jsonl')
REPORT_PATH = Path('reports/europe_pinnacle_discovery_status.json')
BATCH_SIZE = 5
COOLDOWN = 1.25


def merge_snapshots(path: Path, new_rows: list[dict]) -> int:
    rows: dict[tuple[str, str], dict] = {}
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows[(str(row.get('fixture_id')), str(row.get('observed_at')))] = row
    for row in new_rows:
        rows[(str(row.get('fixture_id')), str(row.get('observed_at')))] = row
    ordered = sorted(rows.values(), key=lambda r: (str(r.get('observed_at')), str(r.get('fixture_id'))))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in ordered), encoding='utf-8')
    return len(ordered)


def _write(report: dict, root: Path) -> dict:
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def run(root: Path = Path('.')) -> dict:
    now = datetime.now(timezone.utc)
    report = {
        'schema_version': '1.0',
        'generated_at': now.isoformat(),
        'classification': 'EUROPE_PINNACLE_DISCOVERY_ONLY',
        'bookmaker': BOOKMAKER,
        'production_promotion_allowed': False,
        'validation_gate_effect': 'NONE',
        'candidate_matching_allowed': False,
        'cross_bookmaker_price_equivalence_allowed': False,
        'core_quota_reserve': CORE_QUOTA_RESERVE,
        'planned_requests': 3,
    }
    key = os.getenv(ENV_KEY, '').strip()
    if not key:
        report['status'] = 'API_KEY_NOT_CONFIGURED'
        return _write(report, root)
    try:
        quota = summarize_account(_get('/account', key))
    except Exception as exc:
        report.update(status='SKIPPED_QUOTA_HEALTH_UNAVAILABLE', requests_used=0, errors=[f'{type(exc).__name__}: {exc}'])
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

    strict: list[dict] = []
    diagnostics: list[dict] = []
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
            tm = {**(meta.get(int(fixture.get('tournamentId') or -1)) or {}), 'universe': 'EUROPE_PINNACLE_DISCOVERY'}
            book = (fixture.get('bookmakerOdds') or {}).get(BOOKMAKER)
            bookmaker_active = isinstance(book, dict) and book.get('bookmakerIsActive') is True and book.get('suspended') is False
            shape = mainline_shape(fixture, catalog, bookmaker=BOOKMAKER)
            snapshot, reason = extract_mainline_snapshot(fixture, catalog, observed_at=now, tournament_meta=tm, bookmaker=BOOKMAKER)
            diagnostics.append({
                'country': tm.get('country'),
                'league': tm.get('tournament_name'),
                'fixture_id': fixture.get('fixtureId'),
                'bookmaker_active': bookmaker_active,
                'ah_main_count': shape.get('ah_main_count', 0),
                'ou_main_count': shape.get('ou_main_count', 0),
                'strict_snapshot': snapshot is not None,
                'reason': reason,
            })
            if snapshot:
                snapshot['discovery_only'] = True
                snapshot['candidate_like_matches'] = []
                snapshot['candidate_matching_allowed'] = False
                snapshot['cross_bookmaker_price_equivalence_allowed'] = False
                strict.append(snapshot)

    total_persisted = merge_snapshots(root / SNAPSHOT_PATH, strict)
    report.update(
        status='DISCOVERY_OBSERVED',
        resolved_leagues=len(selected),
        requests_used=requests,
        strict_snapshots_this_run=len(strict),
        persisted_snapshot_rows=total_persisted,
        **summarize_rows(diagnostics),
        interpretation=(
            'Independent Pinnacle Europe discovery stream. It exists because Bet365 had no active full-time AH coverage in the same 15-league expansion sample. '
            'Pinnacle prices must not be matched to Bet365 candidate price bands and cannot enter frozen Validation v2 or production automatically.'
        ),
    )
    return _write(report, root)


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False))
