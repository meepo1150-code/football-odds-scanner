"""Bind the reviewed November 4 storyboard to exact ledger selections."""
from .engine import settle

EXPECTED=[('id1000000774166004','OU','UNDER',3.5),('id1000000774166006','OU','UNDER',3.5),('id1000000774165998','AH','HOME',1.25),('id1000003875953678','AH','AWAY',.25),('id1000001872340000','AH','HOME',.25)]

def validate_edition(data,recap,ledger):
    if data['date']!='2026-11-04' or data.get('display_timezone')!='UTC':raise ValueError('Storyboard requires reviewed 4 November UTC edition')
    actual=[(p['fixture_id'],p['market'],p['selection'],p['line']) for p in data['predictions']]
    if actual!=EXPECTED:raise ValueError('Selections differ from reviewed narration')
    stored={r['prediction']['id']:r['prediction'] for r in ledger}
    if len(stored)!=len(EXPECTED):raise ValueError('Ledger coverage mismatch')
    for p in data['predictions']:
        if stored.get(p['id'])!={k:p[k] for k in ('id','fixture_id','home','away','kickoff','market','selection','line')}:raise ValueError('Display differs from ledger')
    if len(recap)!=8 or len({r['fixture_id'] for r in recap})!=8:raise ValueError('Incomplete prior selections')
    for p in recap:
        r=p['result_evidence']
        if r['fixture_id']!=p['fixture_id'] or [r['ft_home_goals'],r['ft_away_goals']]!=p['ft']:raise ValueError('FT evidence mismatch')
        if settle(p,*p['ft'])!=p['settlement']:raise ValueError('Settlement mismatch')
    if sum(r['settlement']=='FULL_WIN' for r in recap)!=2 or sum(r['settlement']=='FULL_LOSS' for r in recap)!=6:raise ValueError('Recap differs from reviewed narration')
