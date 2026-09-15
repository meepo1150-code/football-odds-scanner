from __future__ import annotations

import json, math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from .asian_settlement import settle_asian_handicap, settle_asian_total

SNAPSHOTS=Path('data/normalized/europe_pinnacle_research_v2_snapshots.jsonl'); RESULTS=Path('data/normalized/oddspapi_finished_results.jsonl')
AUDIT=Path('data/normalized/europe_pinnacle_research_v2_audit.jsonl'); OUTCOMES=Path('data/normalized/research_v2_pattern_outcomes.jsonl'); REPORT=Path('reports/research_v2_pattern_statistics.json')

def _rows(path):
    if not path.exists(): return []
    out=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        try: x=json.loads(line)
        except (json.JSONDecodeError,TypeError): continue
        if isinstance(x,dict): out.append(x)
    return out

def _num(v):
    try: return float(v)
    except (TypeError,ValueError): return None

def _score(r):
    try: h,a=int(r.get('ft_home_goals')),int(r.get('ft_away_goals'))
    except (TypeError,ValueError): return None
    return (h,a) if h>=0 and a>=0 else None

def _prob_bucket(v):
    p=_num(v)
    if p is None:return 'UNKNOWN'
    lo=int((p*100)//5)*5; return f'{lo:02d}-{lo+4:02d}%'

def _water_bucket(v):
    x=_num(v)
    if x is None:return 'UNKNOWN'
    if x<.80:return '<0.80'
    if x>1.20:return '>1.20'
    lo=math.floor((x+.000001)*20)/20
    return f'{lo:.2f}-{lo+.049:.3f}'

def _core(v):
    x=_num(v); return x is not None and .80<=x<=1.20

def _result_index(rows):
    g=defaultdict(list)
    for r in rows:
        if r.get('fixture_id') and _score(r) is not None:g[str(r['fixture_id'])].append(r)
    idx={}; ambiguous=set()
    for fid,items in g.items():
        scores={_score(x) for x in items}
        if len(scores)==1:idx[fid]=items[-1]
        else:ambiguous.add(fid)
    return idx,ambiguous

def _price_result(s):return {'FULL_WIN':'WIN','HALF_WIN':'HALF_WIN','PUSH':'PUSH','HALF_LOSS':'HALF_LOSS','FULL_LOSS':'LOSS'}.get(s,'UNSETTLED')

def _movement(first,last):
    fa,la=first.get('ah') or {},last.get('ah') or {}; fl,ll=_num(fa.get('selected_side_line')),_num(la.get('selected_side_line')); fw,lw=_num(fa.get('selected_side_price')),_num(la.get('selected_side_price'))
    if fl is None or ll is None:return 'AH_LINE_UNKNOWN'
    line='AH_LINE_UNCHANGED' if ll==fl else ('AH_FAVORITE_LINE_STRONGER' if ll<fl else 'AH_FAVORITE_LINE_WEAKER')
    if fw is None or lw is None:return line
    water='WATER_FLAT' if abs(lw-fw)<.005 else ('WATER_DOWN' if lw<fw else 'WATER_UP')
    return f'{line}__{water}'

def _wilson(w,n):
    if not n:return [None,None]
    z=1.959963984540054; p=w/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; m=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/d
    return [round(100*(c-m),2),round(100*(c+m),2)]

def build(root=Path('.')):
    snaps=_rows(root/SNAPSHOTS); audits=_rows(root/AUDIT); results,ambiguous=_result_index(_rows(root/RESULTS)); ag={(str(x.get('fixture_id')),str(x.get('observed_at'))):x for x in audits}; grouped=defaultdict(list)
    for s in snaps:
        if s.get('fixture_id'):grouped[str(s['fixture_id'])].append(s)
    for ss in grouped.values():ss.sort(key=lambda x:str(x.get('observed_at') or ''))
    outcomes=[]; missing=0
    for fid,ss in sorted(grouped.items()):
        if fid in ambiguous:continue
        r=results.get(fid)
        if not r:missing+=1;continue
        s=ss[-1]; h,a=_score(r); fav=str(s.get('favorite_side') or '').upper(); one=s.get('one_x_two') or {}; ah=s.get('ah') or {}; ou=s.get('ou') or {}; au=ag.get((fid,str(s.get('observed_at'))),{})
        outright='DRAW' if h==a else ('WIN' if (h>a and fav=='H') or (a>h and fav=='A') else 'LOSS'); ah_settle=None
        try:ah_settle=settle_asian_handicap(h,a,float(ah.get('selected_side_line')),float(ah.get('selected_side_price')),fav).settlement.value
        except (TypeError,ValueError):pass
        ou_out={}
        for side,key in [('O','over_price'),('U','under_price')]:
            try:ou_out[side]=settle_asian_total(h,a,float(ou.get('line')),float(ou.get(key)),side).settlement.value
            except (TypeError,ValueError):pass
        fp=one.get('home') if fav=='H' else one.get('away') if fav=='A' else None; water=ah.get('selected_side_price')
        outcomes.append({'fixture_id':fid,'football_day':s.get('football_day'),'league':s.get('league'),'home':s.get('home'),'away':s.get('away'),'favorite_side':fav,'favorite_1x2_price':fp,'favorite_fair_probability':s.get('favorite_fair_probability'),'favorite_probability_bucket':_prob_bucket(s.get('favorite_fair_probability')),'ah_line':ah.get('selected_side_line'),'ah_water':water,'ah_water_bucket':_water_bucket(water),'ah_core_water':_core(water),'ou_line':ou.get('line'),'scan_count':len(ss),'first_observed_at':ss[0].get('observed_at'),'last_observed_at':s.get('observed_at'),'first_ah_line':(ss[0].get('ah') or {}).get('selected_side_line'),'first_ah_water':(ss[0].get('ah') or {}).get('selected_side_price'),'movement':_movement(ss[0],s),'match_status':au.get('eligibility_status','UNCLASSIFIED'),'ft_home_goals':h,'ft_away_goals':a,'favorite_outright_ft_outcome':outright,'favorite_ah_settlement':ah_settle,'price_result':_price_result(ah_settle),'over_settlement':ou_out.get('O'),'under_settlement':ou_out.get('U'),'result_join':'EXACT_FIXTURE_ID_ONLY','research_only':True})
    p=root/OUTCOMES;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in outcomes),encoding='utf-8')
    def aggregate(keys,core_only=False):
        groups=defaultdict(list)
        for x in outcomes:
            if core_only and not x['ah_core_water']:continue
            groups[tuple(str(x.get(k,'UNKNOWN')) for k in keys)].append(x)
        out=[]
        for vals,rs in groups.items():
            pc=Counter(x['price_result'] for x in rs);n=sum(pc[x] for x in ('WIN','HALF_WIN','PUSH','HALF_LOSS','LOSS')); ci=_wilson(pc['WIN'],n)
            out.append({**dict(zip(keys,vals)),'n':len(rs),'settled_n':n,'full_win':pc['WIN'],'half_win':pc['HALF_WIN'],'push':pc['PUSH'],'half_loss':pc['HALF_LOSS'],'full_loss':pc['LOSS'],'full_win_pct':round(100*pc['WIN']/n,2) if n else None,'full_win_wilson95_low':ci[0],'full_win_wilson95_high':ci[1],'sample_label':'VERY_LOW_SAMPLE' if n<10 else 'LOW_SAMPLE' if n<20 else 'DEVELOPING' if n<50 else 'DESCRIPTIVE_50_PLUS'})
        return sorted(out,key=lambda x:-x['n'])
    payload={'schema_version':'2.0','classification':'RESEARCH_V2_AH_HISTORICAL_PATTERN_STATISTICS','generated_at':datetime.now(timezone.utc).isoformat(),'research_only':True,'recommendation_semantics':False,'primary_market':'ASIAN_HANDICAP','core_ah_water_range':[.80,1.20],'one_x_two_role':'CONTEXT_FAIR_PROBABILITY_ONLY','price_win_definition':'ASIAN_HANDICAP_SETTLEMENT_ONLY','notes':['PRICE WIN is Asian Handicap settlement only; outright FT winner is separate.','Every scan snapshot remains in the source timeline; fixture-level outcome statistics use the latest pre-match observation once per fixture.','Movement is derived from first versus last observed AH line/water and is descriptive only.','1X2 is contextual probability information, not PRICE WIN settlement.','All FT joins require exact fixture_id.'],'snapshot_rows':len(snaps),'unique_snapshot_fixtures':len(grouped),'settled_fixtures':len(outcomes),'core_water_settled_fixtures':sum(x['ah_core_water'] for x in outcomes),'missing_result_fixtures':missing,'ambiguous_result_fixtures':len(ambiguous),'core_by_ah_line_water':aggregate(['ah_line','ah_water_bucket'],True),'core_by_ah_line_probability':aggregate(['ah_line','favorite_probability_bucket'],True),'core_by_ah_line_movement':aggregate(['ah_line','movement'],True),'core_by_line_water_probability':aggregate(['ah_line','ah_water_bucket','favorite_probability_bucket'],True),'core_by_line_water_movement':aggregate(['ah_line','ah_water_bucket','movement'],True),'all_by_ah_line':aggregate(['ah_line']),'all_by_movement':aggregate(['movement'])}
    q=root/REPORT;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');return payload

if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False))
