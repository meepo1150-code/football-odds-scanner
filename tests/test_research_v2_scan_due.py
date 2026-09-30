from datetime import datetime
from odds_scanner.research_v2_scan_due import due
from odds_scanner import pinnwire_probe as pinn


def test_watchdog_recovers_missed_slot_without_duplicate_attempt():
    now=datetime.fromisoformat('2026-09-30T21:37:00+07:00')
    assert due(now, {'generated_at':'2026-09-30T18:05:00+07:00'})
    assert not due(now, {'generated_at':'2026-09-30T21:05:00+07:00','status':'RATE_LIMITED'})
    assert not due(datetime.fromisoformat('2026-09-30T23:40:00+07:00'), {})


def test_no_background_provider_probe_outside_slots():
    assert not due(datetime.fromisoformat('2026-09-30T07:37:00+07:00'), {})
    assert due(datetime.fromisoformat('2026-10-03T19:37:00+07:00'), {})
    assert due(datetime.fromisoformat('2026-09-30T07:37:00+07:00'), {}, 'workflow_dispatch')


def test_pinnwire_includes_after_midnight_in_previous_football_day(tmp_path, monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls.fromisoformat('2026-09-30T16:00:00+00:00').astimezone(tz)
    monkeypatch.setattr(pinn,'datetime',Clock)
    monkeypatch.setattr(pinn,'SNAP',tmp_path/'snap.jsonl')
    monkeypatch.setattr(pinn,'REPORT',tmp_path/'report.json')
    def ev(i,start):
        return {'id':i,'home':'Home','away':'Away','starts':start,'periods':{'num_0':{'spreads':{'main':{'hdp':-.5,'home':1.9,'away':1.95}}}}}
    events=[ev('after-midnight','2026-09-30T19:00:00Z'),ev('at-end','2026-09-30T23:00:00Z'),ev('started','2026-09-30T15:00:00Z')]
    monkeypatch.setattr(pinn,'_fetch_payload',lambda:({'events':events},1,0))
    report=pinn.collect()
    assert report['strict_snapshots_this_run']==1
    import json
    row=json.loads((tmp_path/'snap.jsonl').read_text())
    assert row['fixture_id']=='pinnwire:after-midnight'
    assert row['football_day']=='2026-09-30'
    assert row['observed_at']=='2026-09-30T16:00:00+00:00'
