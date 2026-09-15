from __future__ import annotations

import json
import os
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .oddspapi_provider import ENV_KEY, SPORT_ID, _get

BANGKOK = ZoneInfo('Asia/Bangkok')
FIXTURES_PATH = Path('data/normalized/research_v2_daily_fixtures.jsonl')
REPORT_PATH = Path('reports/research_v2_daily_sync_status.json')


def _rows(payload):
    if isinstance(payload, list): return payload
    if isinstance(payload, dict):
        rows = payload.get('data') or payload.get('fixtures') or []
        return rows if isinstance(rows, list) else []
    return []


def _parse(value):
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError): return None


def _load_report(path: Path) -> dict:
    if not path.exists(): return {}
    try: return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError): return {}


def _existing_day_rows(path: Path, football_day: str) -> list[dict]:
    if not path.exists(): return []
    found = []
    for line in path.read_text(encoding='utf-8').splitlines():
        try: row = json.loads(line)
        except json.JSONDecodeError: continue
        if isinstance(row, dict) and str(row.get('football_day')) == football_day and row.get('fixture_id') is not None: found.append(row)
    return found


def _merge(path: Path, new_rows: list[dict]) -> int:
    rows = {}
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            try: row = json.loads(line)
            except json.JSONDecodeError: continue
            if isinstance(row, dict) and row.get('football_day') and row.get('fixture_id') is not None:
                rows[(str(row['football_day']), str(row['fixture_id']))] = row
    for row in new_rows:
        if row.get('football_day') and row.get('fixture_id') is not None:
            rows[(str(row['football_day']), str(row['fixture_id']))] = row
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows.values(), key=lambda x: (str(x.get('football_day')), str(x.get('kickoff')), str(x.get('fixture_id'))))
    path.write_text(''.join(json.dumps(x, ensure_ascii=False, separators=(',', ':')) + '\n' for x in ordered), encoding='utf-8')
    return len(ordered)


def run(root: Path = Path('.')) -> dict:
    now = datetime.now(timezone.utc); local = now.astimezone(BANGKOK); football_day = local.date().isoformat()
    start_local = datetime.combine(local.date(), dtime(12), BANGKOK); end_local = datetime.combine(local.date() + timedelta(days=1), dtime(6), BANGKOK)
    start_utc, end_utc = start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)
    report = {'schema_version':'1.2','classification':'RESEARCH_V2_DAILY_FIXTURE_RESULT_SYNC','generated_at':now.isoformat(),'football_day':football_day,'window_start':start_utc.isoformat(),'window_end':end_utc.isoformat(),'research_only':True,'odds_requested':False}
    fixtures_path = root / FIXTURES_PATH; report_path = root / REPORT_PATH
    previous = _load_report(report_path); existing = _existing_day_rows(fixtures_path, football_day)
    if str(previous.get('football_day')) == football_day and previous.get('status') in {'FIXTURES_SYNCED','ALREADY_SYNCED'}:
        report.update(status='ALREADY_SYNCED', fixture_requests_used=0, football_day_fixtures=len(existing), persisted_fixture_rows=sum(1 for line in fixtures_path.read_text(encoding='utf-8').splitlines() if line.strip()) if fixtures_path.exists() else 0, completion_marker=True)
    else:
        key = os.getenv(ENV_KEY, '').strip()
        if not key: report.update(status='API_KEY_NOT_CONFIGURED', fixture_requests_used=0, completion_marker=False)
        else:
            try:
                payload = _get('/fixtures', key, {'sportId':SPORT_ID,'from':start_local.date().isoformat(),'to':end_local.date().isoformat()}, 60); api_rows = _rows(payload); selected = []
                for fixture in api_rows:
                    kickoff = _parse(fixture.get('startTime')); fixture_id = fixture.get('fixtureId')
                    if fixture_id is None or kickoff is None or not (start_utc <= kickoff < end_utc): continue
                    external = fixture.get('externalProviders') if isinstance(fixture.get('externalProviders'), dict) else {}
                    selected.append({'football_day':football_day,'fixture_id':fixture_id,'tournament_id':fixture.get('tournamentId'),'league':fixture.get('tournamentName') or fixture.get('tournamentSlug'),'home':fixture.get('participant1Name'),'away':fixture.get('participant2Name'),'kickoff':fixture.get('startTime'),'status_id':fixture.get('statusId'),'status_name':fixture.get('statusName'),'has_odds':fixture.get('hasOdds'),'flashscore_id':fixture.get('flashscoreId') or external.get('flashscoreId'),'discovered_at':now.isoformat(),'source':'oddspapi:/fixtures','research_only':True})
                total = _merge(fixtures_path, selected)
                report.update(status='FIXTURES_SYNCED', fixture_requests_used=1, api_fixtures_returned=len(api_rows), football_day_fixtures=len(selected), persisted_fixture_rows=total, completion_marker=True)
            except Exception as exc: report.update(status='FIXTURE_SYNC_FAILED', fixture_requests_used=1, completion_marker=False, errors=[f'{type(exc).__name__}: {exc}'])
    report_path.parent.mkdir(parents=True, exist_ok=True); report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8'); return report


if __name__ == '__main__': print(json.dumps(run(), ensure_ascii=False))
