"""Auto is the proven Manual job plus cron, not a different collector."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

WORKFLOWS = Path('.github/workflows')


def workflow(name):
    return yaml.safe_load((WORKFLOWS/name).read_text())


def events(value):
    return value.get('on', value.get(True))


def test_auto_job_is_manual_copy_with_only_trigger_and_publication_names_changed():
    manual = workflow('manual-current-day-odds.yml')
    auto = workflow('auto-scan.yml')
    assert auto['name'] == 'Auto Scan'
    for key in ('permissions', 'concurrency'):
        assert auto[key] == manual[key]
    assert auto['concurrency']['cancel-in-progress'] is False
    assert events(auto)['workflow_dispatch'] == events(manual)['workflow_dispatch']
    assert set(events(auto)) == {'schedule', 'workflow_dispatch'}
    copied = deepcopy(auto['jobs'])
    copied['observe']['if'] = manual['jobs']['observe']['if']
    publication = copied['observe']['steps'][-1]
    publication['run'] = publication['run'].replace('/tmp/auto-observation', '/tmp/manual-observation').replace(
        'data: auto current-day odds observation [skip ci]',
        'data: manual current-day odds observation [skip ci]')
    assert copied == manual['jobs']
    condition = auto['jobs']['observe']['if']
    assert "github.ref == 'refs/heads/main'" in condition
    assert "github.event_name == 'schedule' || inputs.confirm_live_requests == true" in condition
    assert auto['jobs']['observe']['env']['ODDSPAPI_KEY'] == '${{ secrets.HISTORICAL_ODDSPAPI_KEY }}'


def test_utc_cron_yields_exact_bangkok_rounds_including_weekend_noon():
    schedules = events(workflow('auto-scan.yml'))['schedule']
    assert {item['cron'] for item in schedules} == {'0 8,11,14,17 * * *', '0 5 * * 6,0'}
    bkk = ZoneInfo('Asia/Bangkok')
    start = datetime(2026, 10, 19, tzinfo=bkk)
    slots = []
    for hour in range(7*24):
        utc = start.astimezone(timezone.utc) + timedelta(hours=hour)
        for item in schedules:
            minute, hours, day, month, weekdays = item['cron'].split()
            assert minute == '0' and day == month == '*'
            if str(utc.hour) in hours.split(',') and (weekdays == '*' or str((utc.weekday()+1)%7) in weekdays.split(',')):
                slots.append(utc.astimezone(bkk))
    assert len(slots) == len(set(slots)) == 30
    for day in range(7):
        date = (start + timedelta(days=day)).date()
        expected = [0, 12, 15, 18, 21] if day >= 5 else [0, 15, 18, 21]
        assert sorted(s.hour for s in slots if s.date() == date) == expected


def test_auto_and_manual_publish_even_when_collection_reports_a_failure():
    pages = workflow('pages.yml')
    assert {'Auto Scan', 'Manual Current-Day Odds Observation'} <= set(events(pages)['workflow_run']['workflows'])
    condition = pages['jobs']['deploy']['if']
    for name in ('Auto Scan', 'Manual Current-Day Odds Observation'):
        assert f"github.event.workflow_run.name == '{name}'" in condition
    assert "github.event.workflow_run.head_branch == 'main'" in condition


def test_weekend_noon_copy_collects_actual_time_with_mocked_provider(tmp_path, monkeypatch):
    from odds_scanner import europe_pinnacle_discovery as collector
    from test_collector_observation_contract import setup
    clock, fixture = setup(tmp_path, monkeypatch, now='2026-10-18T05:00:00+00:00')
    monkeypatch.chdir(tmp_path)
    for key in ('RESEARCH_V2_MANUAL_BREADTH', 'RESEARCH_V2_MANUAL_UNRESTRICTED', 'RESEARCH_V2_FORCE_RUN'):
        monkeypatch.setenv(key, 'true')
    monkeypatch.setenv('RESEARCH_V2_FORCE_TARGET_AT', clock.current.isoformat())
    monkeypatch.delenv('RESEARCH_QUOTA_DURABLE', raising=False)
    fixture['startTime'] = '2026-10-18T08:00:00Z'
    calls = []
    def get(path, *args):
        calls.append(path)
        if path == '/account':
            return {}
        clock.current = datetime.fromisoformat('2026-10-18T05:00:05+00:00')
        return [fixture]
    monkeypatch.setattr(collector, '_get', get)
    result = collector.run(tmp_path)
    assert result['status'] == 'RESEARCH_V2_OBSERVED'
    assert result['strict_snapshots_this_run'] == 1
    assert calls == ['/account', '/odds-by-tournaments']
    snapshot = json.loads((tmp_path/collector.SNAPSHOT_PATH).read_text())
    assert snapshot['observed_at'] == '2026-10-18T05:00:05+00:00'
    assert snapshot['scheduled_target_at'] == '2026-10-18T12:00:00+07:00'
