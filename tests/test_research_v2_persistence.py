import json
import pytest
from odds_scanner.research_v2_persistence import merge_jsonl, merge_staged


def write(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(''.join(json.dumps(x)+'\n' for x in rows))


def test_concurrent_observations_and_conflicting_evidence_survive(tmp_path):
    a, b = tmp_path/'latest', tmp_path/'staged'
    first = {'fixture_id':'x', 'observed_at':'t1', 'price':1.9}
    later = dict(first, observed_at='t2')
    conflict = dict(first, price=2.0)
    write(a, [first, later]); write(b, [first, conflict])
    assert merge_jsonl(a, b) == 3
    assert merge_jsonl(a, b) == 3
    assert later in [json.loads(x) for x in a.read_text().splitlines()]


def test_corrupt_record_fails_before_overwriting(tmp_path):
    a, b = tmp_path/'latest', tmp_path/'staged'
    write(a, [{'fixture_id':'x'}]); b.write_text('{broken')
    original = a.read_text()
    with pytest.raises(json.JSONDecodeError): merge_jsonl(a, b)
    assert a.read_text() == original


def test_stale_provider_report_cannot_replace_newer(tmp_path):
    root, staged = tmp_path/'root', tmp_path/'staged'
    rel = 'reports/propline_research_v2_status.json'
    write(root/rel, [{'generated_at':'2026-09-29T15:00:00+00:00','status':'new'}])
    write(staged/rel, [{'generated_at':'2026-09-29T14:00:00+00:00','status':'old'}])
    merge_staged(root, staged)
    assert json.loads((root/rel).read_text())['status'] == 'new'
