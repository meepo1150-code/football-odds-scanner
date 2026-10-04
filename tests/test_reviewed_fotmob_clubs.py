import json
import pytest
from odds_scanner import fotmob_result_backfill as f


@pytest.mark.parametrize('home,source,league', [
    ('UD Almeria','Almería','LaLiga 2'),
    ('Rochdale AFC','Rochdale','League Two'),
    ('Leyton Orient London','Leyton Orient','League One'),
    ('Vitesse Arnhem','Vitesse','Eerste Divisie'),
])
def test_reviewed_clubs_are_league_and_category_scoped(home,source,league):
    snapshot={'home':home,'away':'Opponent','league':league}
    event={'home':source,'away':'Opponent','league':league.replace('LaLiga 2','LaLiga2')}
    assert f._reviewed_identity(snapshot,event)
    assert not f._reviewed_identity(snapshot,{**event,'league':'Other competition'})
    assert not f._reviewed_identity(snapshot,{**event,'away':'Other opponent'})
    assert not f._reviewed_identity({**snapshot,'home':home+' U19'},event)
    assert not f._reviewed_identity({**snapshot,'home':home+' Women'},event)


@pytest.mark.parametrize('change,added', [('none',1),('kickoff',0),('duplicate',0),('unfinished',0)])
def test_recovery_keeps_exact_kickoff_unique_ft_gate(tmp_path,monkeypatch,change,added):
    snapshot={'fixture_id':'test:almeria','home':'UD Almeria','away':'Burgos CF',
              'league':'LaLiga 2','kickoff':'2026-01-01T14:15:00Z'}
    path=tmp_path/f.SNAP;path.parent.mkdir(parents=True)
    path.write_text(json.dumps(snapshot)+'\n')
    event={'id':123,'home':{'name':'Almería','score':2},'away':{'name':'Burgos CF','score':1},
           'status':{'utcTime':snapshot['kickoff'],'finished':True,'reason':{'short':'FT'}}}
    if change=='kickoff':event['status']['utcTime']='2026-01-01T14:16:00Z'
    if change=='unfinished':event['status']['finished']=False
    events=[event,{**event,'id':456}] if change=='duplicate' else [event]
    monkeypatch.setattr(f,'_fetch',lambda day:{'leagues':[{'name':'LaLiga2','matches':events}]})
    report=f.run(tmp_path)
    assert report['exact_results_added']==added
    if added:
        row=json.loads((tmp_path/f.RESULTS).read_text().splitlines()[0])
        assert row['ft_home_goals']==2 and row['ft_away_goals']==1
        assert row['provider_evidence']['reviewed_club_identity_sources']


@pytest.mark.parametrize('home,away,source_home,source_away', [
    ('Hoedd IL','Odds BK','Hødd','Odds Ballklubb'),
    ('Stroemsgodset IF','Aasane Fotball','Strømsgodset','Åsane'),
])
def test_norwegian_competition_bridge_requires_both_reviewed_clubs(home,away,source_home,source_away):
    s={'home':home,'away':away,'league':'1st Division'}
    e={'home':source_home,'away':source_away,'league':'1. Divisjon'}
    assert f._reviewed_identity(s,e)
    assert not f._reviewed_identity(s,{**e,'league':'1st Division'})
    assert not f._reviewed_identity({**s,'away':'Other'}, {**e,'away':'Other'})
