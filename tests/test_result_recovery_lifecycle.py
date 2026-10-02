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


def test_missing_names_can_retire_only_after_full_evidence(tmp_path):
    s=setup(tmp_path);s.update(home=None,away=None)
    (tmp_path/p.SNAP).write_text(json.dumps(s)+'\n');raw=(tmp_path/p.SNAP).read_bytes()
    for provider,stamp,key in [('fotmob','2026-09-22T01:00:00Z','a'),('fotmob','2026-09-22T10:00:00Z','b'),('fotmob','2026-09-23T01:00:00Z','c')]:attempt(tmp_path,provider,stamp,key)
    report=p.review(tmp_path,datetime(2026,9,25,tzinfo=timezone.utc))
    assert report['retired_from_active_queue']==0
    assert 'MINIMUM_SOURCES' in report['pending'][0]['unmet_gates']
    attempt(tmp_path,'espn','2026-09-23T10:00:00Z','d')
    assert p.review(tmp_path,datetime(2026,9,25,tzinfo=timezone.utc))['retired_from_active_queue']==1
    row=p.rows(tmp_path/p.RETIRED)[0]
    assert row['reason']=='MISSING_TEAM_IDENTITY_AFTER_EXHAUSTED_RECOVERY'
    assert (tmp_path/p.SNAP).read_bytes()==raw
    assert not (tmp_path/p.RESULTS).exists()


def test_recent_fixture_keeps_age_gate_and_conflict_is_not_retired(tmp_path):
    setup(tmp_path)
    for provider,stamp,key in [('fotmob','2026-09-20T16:00:00Z','a'),('espn','2026-09-20T20:00:00Z','b'),('fotmob','2026-09-21T16:00:00Z','c'),('espn','2026-09-21T20:00:00Z','d')]:attempt(tmp_path,provider,stamp,key)
    report=p.review(tmp_path,datetime(2026,9,22,tzinfo=timezone.utc))
    assert 'MINIMUM_AGE_72H' in report['pending'][0]['unmet_gates']
    assert report['pending'][0]['age_eligible_at']=='2026-09-23T12:00:00+00:00'
    conflict=(tmp_path/p.RESULTS).with_suffix('.conflicts.jsonl')
    conflict.write_text(json.dumps({'fixture_id':'x'})+'\n')
    assert p.review(tmp_path,datetime(2026,9,25,tzinfo=timezone.utc))['retired_from_active_queue']==0


def test_low_tier_backlog_scope_is_narrow_reversible_and_evidence_based(tmp_path):
    s=setup(tmp_path);s['league']='Germany - Regionalliga North'
    (tmp_path/p.SNAP).write_text(json.dumps(s)+'\n');raw=(tmp_path/p.SNAP).read_bytes()
    for i in range(3):attempt(tmp_path,'fotmob',f'2026-09-20T{16+i}:00:00Z',str(i))
    now=datetime(2026,9,21,tzinfo=timezone.utc)
    assert p.review(tmp_path,now)['retired_from_active_queue']==0
    attempt(tmp_path,'espn','2026-09-20T20:00:00Z','last')
    assert p.review(tmp_path,now)['low_tier_scope_exclusions']==1
    assert p.rows(tmp_path/p.RETIRED)[0]['classification_source'].startswith('https://')
    assert (tmp_path/p.SNAP).read_bytes()==raw
    conflict=(tmp_path/p.RESULTS).with_suffix('.conflicts.jsonl')
    conflict.write_text(json.dumps({'fixture_id':'x'})+'\n')
    assert p.review(tmp_path,now)['retired_from_active_queue']==0
    conflict.unlink()
    s['league']='Mongolia - Premier League'
    (tmp_path/p.SNAP).write_text(json.dumps(s)+'\n')
    assert p.review(tmp_path,now)['retired_from_active_queue']==0
    s['league']='Germany - Regionalliga North'
    (tmp_path/p.SNAP).write_text(json.dumps(s)+'\n')
    (tmp_path/p.RESULTS).write_text(json.dumps({'fixture_id':'x','ft_home_goals':1,'ft_away_goals':0})+'\n')
    assert p.review(tmp_path,now)['retired_from_active_queue']==0


def test_low_tier_scope_does_not_change_future_fixture_policy(tmp_path,monkeypatch):
    s=setup(tmp_path);s['league']='Israel - Liga Alef'
    (tmp_path/p.SNAP).write_text(json.dumps(s)+'\n')
    for i in range(4):attempt(tmp_path,'fotmob' if i<3 else 'espn',f'2026-09-20T{16+i}:00:00Z',str(i))
    monkeypatch.setattr(p,'LOW_TIER_REVIEW_CUTOFF','2026-09-19T00:00:00Z')
    assert p.review(tmp_path,datetime(2026,9,21,tzinfo=timezone.utc))['retired_from_active_queue']==0
