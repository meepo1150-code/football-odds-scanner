from copy import deepcopy
from datetime import datetime,timezone
import json
from odds_scanner import espn_result_backfill as p


def payload():
    return {'leagues':[],'events':[{'id':'123','uid':'soccer:league:123','competitions':[{'date':'2026-09-29T16:00Z','status':{'period':2,'type':{'name':'STATUS_FULL_TIME','completed':True}},'competitors':[{'homeAway':'home','team':{'displayName':'Home'},'score':'2'},{'homeAway':'away','team':{'displayName':'Away'},'score':'1'}]}]}]}


def test_normal_ft_only():
    assert p.events(payload())[0]['hg']==2
    for name,period in [('STATUS_FINAL_AET',4),('STATUS_FINAL_PEN',5),('STATUS_IN_PROGRESS',2)]:
        data=payload();data['events'][0]['competitions'][0]['status'].update(period=period,type={'name':name,'completed':True})
        assert p.events(data)==[]
    data=payload();data['events'][0]['competitions'][0]['competitors'][0]['score']=True
    assert p.events(data)==[]


def test_exact_bridge_cache_reuse_and_quarantine(tmp_path,monkeypatch):
    path=tmp_path/'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl';path.parent.mkdir(parents=True)
    rows=[{'fixture_id':fid,'provider':'pinnwire','home':'Home','away':'Away','kickoff':ko} for fid,ko in [('exact','2026-09-29T16:00:00Z'),('wrong-time','2026-09-29T16:01:00Z'),('blocked','2026-09-29T16:00:00Z')]]
    path.write_text(''.join(json.dumps(x)+'\n' for x in rows))
    (tmp_path/p.RESULTS).with_suffix('.conflicts.jsonl').write_text(json.dumps({'fixture_id':'blocked'})+'\n')
    calls=[]
    monkeypatch.setattr(p,'fetch',lambda day:(calls.append(day) or payload()))
    now=datetime(2026,9,30,tzinfo=timezone.utc)
    r=p.run(tmp_path,now=now);assert r['results_added']==1 and r['not_found']==1
    assert len(calls)==3
    r=p.run(tmp_path,now=now);assert len(calls)==3 and r['cache_hits']==3 and r['results_added']==0


def test_conflicting_provider_copies_not_joined(tmp_path,monkeypatch):
    path=tmp_path/'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl';path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'fixture_id':'x','provider':'pinnwire','home':'Home','away':'Away','kickoff':'2026-09-29T16:00Z'})+'\n')
    data=payload();duplicate=deepcopy(data['events'][0]);duplicate['competitions'][0]['competitors'][0]['score']='3';data['events'].append(duplicate)
    monkeypatch.setattr(p,'fetch',lambda day:data)
    r=p.run(tmp_path,now=datetime(2026,9,30,tzinfo=timezone.utc))
    assert r['ambiguous']==1 and r['results_added']==0
