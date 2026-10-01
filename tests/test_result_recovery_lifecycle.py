import json
from datetime import datetime,timezone
from odds_scanner import result_recovery_lifecycle as p


def setup(root):
    s={'fixture_id':'x','provider':'pinnwire','home':'Home','away':'Away','league':'League','kickoff':'2026-09-20T12:00:00Z','observed_at':'2026-09-20T09:00:00Z'}
    (root/p.SNAP).parent.mkdir(parents=True)
    (root/p.SNAP).write_text(json.dumps(s)+'\n')
    return s


def attempt(root,provider,day,commit):
    p.record(root,provider,{'generated_at':day,'days_requested':['2026-09-19','2026-09-20','2026-09-21']},proof_commit=commit,legacy_direct=True)


def test_retire_after_four_distinct_rounds_two_sources_preserves_raw(tmp_path):
    setup(tmp_path);raw=(tmp_path/p.SNAP).read_bytes()
    for provider,stamp,key in [('fotmob','2026-09-22T01:00:00Z','a'),('fotmob','2026-09-22T10:00:00Z','b'),('fotmob','2026-09-23T01:00:00Z','c'),('espn','2026-09-23T10:00:00Z','d')]:attempt(tmp_path,provider,stamp,key)
    report=p.review(tmp_path,datetime(2026,9,25,tzinfo=timezone.utc))
    assert report['retired_from_active_queue']==1 and p.retired_ids(tmp_path)=={'x'}
    assert (tmp_path/p.SNAP).read_bytes()==raw
    (tmp_path/p.RESULTS).write_text(json.dumps({'fixture_id':'x','ft_home_goals':1,'ft_away_goals':0})+'\n')
    assert p.review(tmp_path,datetime(2026,9,25,tzinfo=timezone.utc))['retired_from_active_queue']==0


def test_three_rounds_or_one_source_cannot_retire(tmp_path):
    setup(tmp_path)
    for i in range(4):attempt(tmp_path,'fotmob',f'2026-09-{22+i}T01:00:00Z',str(i))
    assert p.review(tmp_path,datetime(2026,9,26,tzinfo=timezone.utc))['retired_from_active_queue']==0


def test_same_cached_evidence_never_counts_twice(tmp_path):
    setup(tmp_path)
    evidence=[{'day':d,'source':'CACHE','fetched_at':'2026-09-22T00:00:00Z'} for d in ['2026-09-19','2026-09-20','2026-09-21']]
    for day in (23,24,25,26):p.record(tmp_path,'fotmob',{'generated_at':f'2026-09-{day}T00:00:00Z','fetch_evidence':evidence})
    assert len(p.state(tmp_path)['fixtures']['x'])==1


def test_failed_or_premature_fetch_is_not_recovery_evidence(tmp_path):
    setup(tmp_path)
    evidence=[{'day':d,'source':'NETWORK','fetched_at':'2026-09-20T10:00:00Z'} for d in ['2026-09-19','2026-09-20','2026-09-21']]
    p.record(tmp_path,'espn',{'generated_at':'2026-09-25T00:00:00Z','fetch_evidence':evidence})
    assert not p.state(tmp_path)['fixtures']
