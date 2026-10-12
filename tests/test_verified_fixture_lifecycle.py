import json
from copy import deepcopy
from pathlib import Path
from odds_scanner.verified_fixture_lifecycle import verified_statuses,PATH
from odds_scanner.research_v2_pattern_stats import build,SNAPSHOTS,RESULTS


def receipt():
    identity={'fixture_id':'one','home':'Alpha','away':'Beta','league':'League','kickoff':'2026-10-01T12:00:00Z'}
    return {**identity,'status':'POSTPONED','retrieved_at':'2026-10-02T12:00:00Z',
        'source':{'tier':'A_OFFICIAL','url':'https://club.example/postponed','source_title':'Fixture postponed',
        'assertion':{'verification_method':'MANUAL_WEB_REVIEW','status':'POSTPONED',
            'home':'Alpha','away':'Beta','league':'League','original_kickoff':identity['kickoff']}}}


def write(root,rows):
    p=root/PATH;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(''.join(json.dumps(r)+'\n' for r in rows))


def test_exact_lifecycle_identity_rejects_changed_teams_league_kickoff_and_conflicts(tmp_path):
    r=receipt();write(tmp_path,[r]);assert verified_statuses(tmp_path,[r])['one']['status']=='POSTPONED'
    for key,value in [('home','Other'),('away','Other'),('league','Other'),('kickoff','2026-10-01T13:00:00Z')]:
        changed=dict(r,**{key:value});assert not verified_statuses(tmp_path,[changed])
    for key,value in [('tier','B_REPUTABLE'),('url','http://club.example/postponed'),('assertion',None)]:
        changed=deepcopy(r);changed['source'][key]=value;write(tmp_path,[changed]);assert not verified_statuses(tmp_path,[r])
    other=deepcopy(r);other['status']='CANCELLED';other['source']['assertion']['status']='CANCELLED'
    write(tmp_path,[r,other]);assert not verified_statuses(tmp_path,[r])


def test_postponed_never_generates_ft_or_roi_and_is_disclosed_in_denominator(tmp_path):
    r=receipt();write(tmp_path,[r])
    s={**r,'provider':'pinnwire','observed_at':'2026-10-01T10:00:00Z','favorite_side':'H',
        'ah':{'home_line':-.5,'away_line':.5,'home_price':1.9,'away_price':2.0,
            'selected_side_line':-.5,'selected_side_price':1.9}}
    p=tmp_path/SNAPSHOTS;p.parent.mkdir(parents=True);p.write_text(json.dumps(s)+'\n')
    report=build(tmp_path)
    assert report['settled_fixtures']==0 and report['ft_completeness_denominator']==1
    assert report['postponed_cancelled_abandoned_fixtures']==1
    assert report['verified_non_ft_lifecycles']['one']['status']=='POSTPONED'
    assert report['active_overdue_ft_fixtures']==0
    assert not (tmp_path/RESULTS).exists()
