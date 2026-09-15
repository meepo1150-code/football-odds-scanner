from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .daily_fixture_result_sync import FIXTURES_PATH
from .flashscore_result_provider import fetch_exact_result
from .oddspapi_result_cache import RESULTS_PATH, merge_normalized_results

REPORT_PATH = Path('reports/research_v2_daily_result_backfill.json')
RESULT_MATURITY_DELAY = timedelta(hours=3)


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _utc(value) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def select_candidates(fixtures: list[dict], existing_ids: set[str], *, now: datetime) -> list[dict]:
    by_fixture = {}
    for row in fixtures:
        fixture_id = str(row.get('fixture_id') or '').strip()
        flashscore_id = str(row.get('flashscore_id') or '').strip()
        kickoff = _utc(row.get('kickoff'))
        if not fixture_id or not flashscore_id or fixture_id in existing_ids or fixture_id in by_fixture:
            continue
        if kickoff is None or now < kickoff + RESULT_MATURITY_DELAY:
            continue
        by_fixture[fixture_id] = {
            'fixture_id': fixture_id,
            'home': row.get('home'),
            'away': row.get('away'),
            'kickoff': row.get('kickoff'),
            'external_providers': {'flashscoreId': flashscore_id},
            'mapping_source': 'ODDSPAPI_DAILY_FIXTURE_FLASHSCORE_ID_EXACT_ONLY',
        }
    return sorted(by_fixture.values(), key=lambda r: (str(r.get('kickoff') or ''), str(r.get('fixture_id') or '')))


def run_backfill(root: Path = Path('.'), *, now: datetime | None = None, max_requests: int = 40, sleep_seconds: float = 0.5) -> dict:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    fixtures = _load_jsonl(root / FIXTURES_PATH)
    existing = _load_jsonl(root / RESULTS_PATH)
    existing_ids = {str(r.get('fixture_id')) for r in existing if r.get('fixture_id') is not None}
    candidates = select_candidates(fixtures, existing_ids, now=current)
    attempted = 0
    normalized = []
    failures = []
    for ref in candidates[:max_requests]:
        attempted += 1
        result, meta = fetch_exact_result(ref)
        if result:
            result['daily_fixture_result_track'] = 'RESEARCH_V2_DAILY_EXACT_ID'
            normalized.append(result)
        else:
            failures.append({'fixture_id': ref.get('fixture_id'), 'flashscore_id': (ref.get('external_providers') or {}).get('flashscoreId'), **meta})
        if sleep_seconds > 0 and attempted < min(max_requests, len(candidates)):
            time.sleep(sleep_seconds)
    added = merge_normalized_results(root / RESULTS_PATH, normalized)
    payload = {
        'schema_version': '1.0',
        'classification': 'RESEARCH_V2_DAILY_FIXTURE_EXACT_RESULT_BACKFILL',
        'status': 'RESULTS_ADDED' if added else ('REQUESTS_ATTEMPTED_NO_NEW_RESULTS' if attempted else 'NO_MATURE_EXACT_ID_CANDIDATES'),
        'generated_at': current.isoformat(),
        'daily_fixture_rows': len(fixtures),
        'existing_result_rows': len(existing),
        'eligible_exact_id_fixtures': len(candidates),
        'requests_attempted': attempted,
        'results_parsed': len(normalized),
        'results_added': added,
        'maturity_delay_hours': 3,
        'mapping_policy': 'EXACT_FLASHSCORE_ID_FROM_ODDSPAPI_DAILY_FIXTURE_ONLY',
        'team_name_or_date_fuzzy_matching_allowed': False,
        'odds_api_requests': 0,
        'failures': failures[:40],
        'research_only': True,
    }
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return payload


if __name__ == '__main__':
    print(json.dumps(run_backfill(), ensure_ascii=False))
