from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .asian_settlement import settle_asian_handicap, settle_asian_total

SNAPSHOTS=Path('data/normalized/europe_pinnacle_research_v2_snapshots.jsonl'); RESULTS=Path('data/normalized/oddspapi_finished_results.jsonl')
OUTCOMES=Path('data/normalized/research_v2_pattern_outcomes.jsonl'); REPORT=Path('reports/research_v2_pattern_statistics.json')

def _rows(path):
    if not path.exists(): return []
    out=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        try: x=json.loads(line)
        except (json.JSONDecodeError,TypeError): continue
        if isinstance(x,dict): out.append(x)
    return out

def _score(r):
    try: h,a=int(r.get('ft_home_goals')),int(r.get('ft_away_goals'))
    except (TypeError,ValueError): return None
    return (h,a) if h>=0 and a>=0 else None

def _bucket(v,step=.20):
    try: v=float(v)
    except (TypeError,ValueError): return 'UNKNOWN'
    lo=1+int(max(0,v-1)/step)*step; return f'{lo:.2f}-{lo+step-.01:.2f}'

def _prob_bucket(v):
    try: p=float(v)*100
    except (TypeError,ValueError): return 'UNKNOWN'
    lo=int(p//5)*5; return f'{lo:02d}-{lo+4:02d}%'

def _result_index(rows):
    g=defaultdict(list)
    for r in rows:
        if r.get('fixture_id') and _score(r) is not None: g[str(r['fixture_id'])].append(r)
    idx={}; ambiguous=set()
    for fid,items in g.items():
        scores={_score(x) for x in items}
        if len(scores)==1: idx[fid]=items[-1]
        else: ambiguous.add(fid)
    return idx,ambiguous

def _label(s,keys,allowed=None):
    for k in keys:
        v=s.get(k)
        if isinstance(v,bool): return 'MATCH' if v else 'NOT MATCH'
        if v not in (None,''):
            z=str(v).upper().replace('_',' ')
            if allowed is None or z in allowed: return z
    return 'UNCLASSIFIED'

def _price_result(settlement):
    # "Win the price" means Asian Handicap settlement, never merely winning FT.
    return {'FULL_WIN':'WIN','HALF_WIN':'HALF_WIN','PUSH':'PUSH','HALF_LOSS':'HALF_LOSS','FULL_LOSS':'LOSS'}.get(settlement,'UNSETTLED')

def build(root=Path('.')):
    snaps=_rows(root/SNAPSHOTS); results,ambiguous=_result_index(_rows(root/RESULTS)); latest={}
    for s in snaps:
        fid=str(s.get('fixture_id') or '')
        if fid and (fid not in latest or str(s.get('observed_at') or '')>str(latest[fid].get('observed_at') or '')): latest[fid]=s
    outcomes=[]; missing=0
    for fid,s in sorted(latest.items()):
        if fid in ambiguous: continue
        r=results.get(fid)
        if not r: missing+=1; continue
        h,a=_score(r); fav=str(s.get('favorite_side') or '').upper(); one=s.get('one_x_two') or {}; ah=s.get('ah') or {}; ou=s.get('ou') or {}
        fav_price=one.get('home') if fav=='H' else one.get('away') if fav=='A' else None
        outright='DRAW' if h==a else ('WIN' if (h>a and fav=='H') or (a>h and fav=='A') else 'LOSS')
        ah_settle=None
        try: ah_settle=settle_asian_handicap(h,a,float(ah.get('selected_side_line')),float(ah.get('selected_side_price')),fav).settlement.value
        except (TypeError,ValueError): pass
        ou_out={}
        for side,key in [('O','over_price'),('U','under_price')]:
            try: ou_out[side]=settle_asian_total(h,a,float(ou.get('line')),float(ou.get(key)),side).settlement.value
            except (TypeError,ValueError): pass
        outcomes.append({'fixture_id':fid,'football_day':s.get('football_day'),'league':s.get('league'),'home':s.get('home'),'away':s.get('away'),'observed_at':s.get('observed_at'),'favorite_side':fav,'favorite_1x2_price':fav_price,'favorite_price_bucket':_bucket(fav_price),'favorite_fair_probability':s.get('favorite_fair_probability'),'favorite_probability_bucket':_prob_bucket(s.get('favorite_fair_probability')),'ah_line':ah.get('selected_side_line'),'ah_price':ah.get('selected_side_price'),'ou_line':ou.get('line'),'match_status':_label(s,('match_status','match','classification','pattern_match'),{'MATCH','NOT MATCH'}),'movement':_label(s,('movement','movement_type','movement_label')),'ft_home_goals':h,'ft_away_goals':a,'favorite_outright_ft_outcome':outright,'favorite_ah_settlement':ah_settle,'price_result':_price_result(ah_settle),'over_settlement':ou_out.get('O'),'under_settlement':ou_out.get('U'),'result_join':'EXACT_FIXTURE_ID_ONLY','research_only':True})
    p=root/OUTCOMES; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in outcomes),encoding='utf-8')
    def aggregate(keys):
        groups=defaultdict(list)
        for x in outcomes: groups[tuple(str(x.get(k,'UNKNOWN')) for k in keys)].append(x)
        out=[]
        for vals,rs in groups.items():
            pc=Counter(x['price_result'] for x in rs); oc=Counter(x['favorite_outright_ft_outcome'] for x in rs); n=len(rs); settled=sum(pc[x] for x in ('WIN','HALF_WIN','PUSH','HALF_LOSS','LOSS'))
            out.append({**dict(zip(keys,vals)),'n':n,'handicap_settled_n':settled,'price_win':pc['WIN'],'price_half_win':pc['HALF_WIN'],'price_push':pc['PUSH'],'price_half_loss':pc['HALF_LOSS'],'price_loss':pc['LOSS'],'price_full_win_pct':round(100*pc['WIN']/settled,2) if settled else None,'price_non_loss_pct':round(100*(pc['WIN']+pc['HALF_WIN']+pc['PUSH'])/settled,2) if settled else None,'outright_win':oc['WIN'],'outright_draw':oc['DRAW'],'outright_loss':oc['LOSS']})
        return sorted(out,key=lambda x:(-x['n'],)+tuple(str(x[k]) for k in keys))
    payload={'schema_version':'1.1','classification':'RESEARCH_V2_HISTORICAL_PATTERN_STATISTICS','generated_at':datetime.now(timezone.utc).isoformat(),'research_only':True,'recommendation_semantics':False,'price_win_definition':'ASIAN_HANDICAP_SETTLEMENT_ONLY','price_win_examples':{'H_-1.5_FT_1_0':'LOSS','H_-1.0_FT_1_0':'PUSH','H_-0.75_FT_1_0':'HALF_WIN','H_-0.5_FT_1_0':'WIN'},'notes':['PRICE WIN is defined exclusively by Asian Handicap settlement, not by outright FT winner.','Quarter lines retain FULL_WIN, HALF_WIN, PUSH, HALF_LOSS, FULL_LOSS semantics.','MATCH and movement are descriptive research dimensions only; not picks, edge, CLV, or profit signals.','Latest available snapshot per fixture avoids duplicate-fixture weighting.','All result joins require exact fixture_id.'],'snapshot_rows':len(snaps),'unique_snapshot_fixtures':len(latest),'settled_fixtures':len(outcomes),'missing_result_fixtures':missing,'ambiguous_result_fixtures':len(ambiguous),'by_favorite_price_bucket':aggregate(['favorite_price_bucket']),'by_probability_bucket':aggregate(['favorite_probability_bucket']),'by_ah_line':aggregate(['ah_line']),'by_match_status':aggregate(['match_status']),'by_movement':aggregate(['movement']),'by_price_ah_match_movement':aggregate(['favorite_price_bucket','ah_line','match_status','movement']),'by_league_price_bucket':aggregate(['league','favorite_price_bucket'])}
    q=root/REPORT; q.parent.mkdir(parents=True,exist_ok=True); q.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8'); return payload

if __name__=='__main__': print(json.dumps(build(),ensure_ascii=False))
