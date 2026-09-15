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
RESEARCH_AUDIT_PATH = Path('data/normalized/europe_pinnacle_research_v2_audit.jsonl')


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


def _research_ids(path: Path, days: set[str]) -> set[str]:
    ids = set()
    if not path.exists(): return ids
    for line in path.read_text(encoding='utf-8').splitlines():
        try: row = json.loads(line)
        except json.JSONDecodeError: continue
        if not isinstance(row, dict) or str(row.get('football_day')) not in days: continue
        fixture_id = str(row.get('fixture_id') or '').strip()
        if fixture_id: ids.add(fixture_id)
    return ids


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


def _football_window(day, *, start_hour=12, end_hour=6):
    start_local = datetime.combine(day, dtime(start_hour), BANGKOK)
    end_local = datetime.combine(day + timedelta(days=1), dtime(end_hour), BANGKOK)
    return start_local, end_local, start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def run(root: Path = Path('.')) -> dict:
    now = datetime.now(timezone.utc); local = now.astimezone(BANGKOK); day = local.date(); football_day = day.isoformat(); previous_day = (day - timedelta(days=1)).isoformat()
    start_local, end_local, start_utc, end_utc = _football_window(day)
    prev_start_local, _, prev_start_utc, prev_end_utc = _football_window(day - timedelta(days=1))
    coverage_days = [previous_day, football_day]
    report = {'schema_version':'1.4','classification':'RESEARCH_V2_DAILY_FIXTURE_RESULT_SYNC','generated_at':now.isoformat(),'football_day':football_day,'coverage_days':coverage_days,'window_start':start_utc.isoformat(),'window_end':end_utc.isoformat(),'research_only':True,'odds_requested':False}
    fixtures_path = root / FIXTURES_PATH; report_path = root / REPORT_PATH
    previous = _load_report(report_path); existing = _existing_day_rows(fixtures_path, football_day); existing_prev = _existing_day_rows(fixtures_path, previous_day)
    existing_ids = {str(r.get('fixture_id')) for r in existing + existing_prev if r.get('fixture_id') is not None}
    required_research_ids = _research_ids(root / RESEARCH_AUDIT_PATH, {previous_day, football_day})
    missing_research_ids = sorted(required_research_ids - existing_ids)
    prior_coverage = [str(x) for x in (previous.get('coverage_days') or [])]
    complete = str(previous.get('football_day')) == football_day and previous.get('status') in {'FIXTURES_SYNCED','ALREADY_SYNCED'} and all(x in prior_coverage for x in coverage_days) and not missing_research_ids
    if complete:
        report.update(status='ALREADY_SYNCED', fixture_requests_used=0, football_day_fixtures=len(existing), previous_day_fixtures=len(existing_prev), persisted_fixture_rows=sum(1 for line in fixtures_path.read_text(encoding='utf-8').splitlines() if line.strip()) if fixtures_path.exists() else 0, required_research_fixture_ids=len(required_research_ids), missing_research_fixture_ids=0, completion_marker=True)
    else:
        key = os.getenv(ENV_KEY, '').strip()
        if not key: report.update(status='API_KEY_NOT_CONFIGURED', fixture_requests_used=0, missing_research_fixture_ids=len(missing_research_ids), completion_marker=False)
        else:
            try:
                payload = _get('/fixtures', key, {'sportId':SPORT_ID,'from':prev_start_local.date().isoformat(),'to':end_local.date().isoformat()}, 60); api_rows = _rows(payload); selected = []
                counts = {previous_day: 0, football_day: 0}
                for fixture in api_rows:
                    kickoff = _parse(fixture.get('startTime')); fixture_id = fixture.get('fixtureId')
                    if fixture_id is None or kickoff is None: continue
                    fd = None
                    if prev_start_utc <= kickoff < prev_end_utc: fd = previous_day
                    elif start_utc <= kickoff < end_utc: fd = football_day
                    if fd is None: continue
                    external = fixture.get('externalProviders') if isinstance(fixture.get('externalProviders'), dict) else {}
                    selected.append({'football_day':fd,'fixture_id':fixture_id,'tournament_id':fixture.get('tournamentId'),'league':fixture.get('tournamentName') or fixture.get('tournamentSlug'),'home':fixture.get('participant1Name'),'away':fixture.get('participant2Name'),'kickoff':fixture.get('startTime'),'status_id':fixture.get('statusId'),'status_name':fixture.get('statusName'),'has_odds':fixture.get('hasOdds'),'flashscore_id':fixture.get('flashscoreId') or external.get('flashscoreId'),'discovered_at':now.isoformat(),'source':'oddspapi:/fixtures','research_only':True})
                    counts[fd] += 1
                total = _merge(fixtures_path, selected)
                merged_ids = {str(r.get('fixture_id')) for r in _existing_day_rows(fixtures_path, previous_day) + _existing_day_rows(fixtures_path, football_day) if r.get('fixture_id') is not None}
                still_missing = sorted(required_research_ids - merged_ids)
                report.update(status='FIXTURES_SYNCED' if not still_missing else 'FIXTURES_SYNCED_RESEARCH_IDS_MISSING', fixture_requests_used=1, api_fixtures_returned=len(api_rows), football_day_fixtures=counts[football_day], previous_day_fixtures=counts[previous_day], persisted_fixture_rows=total, required_research_fixture_ids=len(required_research_ids), missing_research_fixture_ids=len(still_missing), missing_research_fixture_id_sample=still_missing[:20], completion_marker=not still_missing)
            except Exception as exc: report.update(status='FIXTURE_SYNC_FAILED', fixture_requests_used=1, completion_marker=False, errors=[f'{type(exc).__name__}: {exc}'])
    report_path.parent.mkdir(parents=True, exist_ok=True); report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8'); return report


if __name__ == '__main__': print(json.dumps(run(), ensure_ascii=False))
