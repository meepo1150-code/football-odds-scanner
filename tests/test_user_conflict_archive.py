import json
from datetime import datetime, timezone
from odds_scanner import result_recovery_lifecycle as m

def test_only_authorized_conflicts_archived(tmp_path):
    p=tmp_path/m.SNAP
    p.parent.mkdir(parents=True)
    ids=['pinnwire:1637178704','pinnwire:1637183976','pinnwire:other']
    p.write_text('\n'.join(json.dumps(dict(fixture_id=f,provider='pinnwire',home='Home',away='Away',league='Cup',kickoff='2026-09-29T10:00:00Z')) for f in ids))
    conflicts=(tmp_path/m.RESULTS).with_suffix('.conflicts.jsonl')
    evidence='\n'.join(json.dumps(dict(fixture_id=f)) for f in ids)
    conflicts.write_text(evidence)
    report=m.review(tmp_path,datetime(2026,10,3,tzinfo=timezone.utc))
    assert m.retired_ids(tmp_path)==set(ids[:2])
    assert report['active_matured_unresolved']==1
    assert conflicts.read_text()==evidence
    assert len(m.rows(p))==3
