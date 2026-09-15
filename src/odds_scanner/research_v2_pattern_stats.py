from __future__ import annotations

import json, math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from .asian_settlement import settle_asian_handicap

SNAPSHOTS=Path('data/normalized/europe_pinnacle_research_v2_snapshots.jsonl'); RESULTS=Path('data/normalized/oddspapi_finished_results.jsonl')
AUDIT=Path('data/normalized/europe_pinnacle_research_v2_audit.jsonl'); OUTCOMES=Path('data/normalized/research_v2_pattern_outcomes.jsonl'); REPORT=Path('reports/research_v2_pattern_statistics.json')

def _rows(path):
    if not path.exists(): return []
    out=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        try:x=json.loads(line)
        except (json.JSONDecodeError,TypeError):continue
        if isinstance(x,dict):out.append(x)
    return out

def _num(v):
    try:return float(v)
    except (TypeError,ValueError):return None

def _score(r):
    try:h,a=int(r.get('ft_home_goals')),int(r.get('ft_away_goals'))
    except (TypeError,ValueError):return None
    return (h,a) if h>=0 and a>=0 else None

def _prob_bucket(v):
    p=_num(v)
    if p is None:return 'UNKNOWN'
    lo=int((p*100)//5)*5;return f'{lo:02d}-{lo+4:02d}%'

def _price_bucket(v):
    x=_num(v)
    if x is None:return 'UNKNOWN'
    if x<1.80:return '<1.80'
    if x>2.20:return '>2.20'
    if x<1.90:return '1.80-1.89'
    if x<2.00:return '1.90-1.99'
    if x<2.10:return '2.00-2.09'
    return '2.10-2.20'

def _core(v):
    x=_num(v);return x is not None and 1.80<=x<=2.20

def _result_index(rows):
    g=defaultdict(list)
    for r in rows:
        if r.get('fixture_id') and _score(r) is not None:g[str(r['fixture_id'])].append(r)
    idx={};ambiguous=set()
    for fid,items in g.items():
        scores={_score(x) for x in items}
        if len(scores)==1:idx[fid]=items[-1]
        else:ambiguous.add(fid)
    return idx,ambiguous

def _price_result(s):return {'FULL_WIN':'WIN','HALF_WIN':'HALF_WIN','PUSH':'PUSH','HALF_LOSS':'HALF_LOSS','FULL_LOSS':'LOSS'}.get(s,'UNSETTLED')

def _movement(first,last):
    if str(first.get('favorite_side') or '').upper()!=str(last.get('favorite_side') or '').upper():return 'FAVORITE_SWITCH'
    fa,la=first.get('ah') or {},last.get('ah') or {};fl,ll=_num(fa.get('selected_side_line')),_num(la.get('selected_side_line'));fp,lp=_num(fa.get('selected_side_price')),_num(la.get('selected_side_price'))
    if fl is None or ll is None:return 'AH_LINE_UNKNOWN'
    line='AH_LINE_UNCHANGED' if ll==fl else ('AH_FAVORITE_LINE_STRONGER' if ll<fl else 'AH_FAVORITE_LINE_WEAKER')
    if fp is None or lp is None:return line
    price='PRICE_FLAT' if abs(lp-fp)<.005 else ('PRICE_DOWN' if lp<fp else 'PRICE_UP')
    return f'{line}__{price}'

def _wilson(w,n):
    if not n:return [None,None]
    z=1.959963984540054;p=w/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;m=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/d
    return [round(100*(c-m),2),round(100*(c+m),2)]

def _sample(n):
    if n<30:return 'VERY_LOW'
    if n<100:return 'DEVELOPING'
    if n<300:return 'MODERATE'
    return 'STRONG_300_PLUS'

def build(root=Path('.')):
    snaps=_rows(root/SNAPSHOTS);audits=_rows(root/AUDIT);results,ambiguous=_result_index(_rows(root/RESULTS));ag={(str(x.get('fixture_id')),str(x.get('observed_at'))):x for x in audits};grouped=defaultdict(list)
    for s in snaps:
        if s.get('fixture_id'):grouped[str(s['fixture_id'])].append(s)
    for ss in grouped.values():ss.sort(key=lambda x:str(x.get('observed_at') or ''))
    outcomes=[];missing=0
    for fid,ss in sorted(grouped.items()):
        if fid in ambiguous:continue
        r=results.get(fid)
        if not r:missing+=1;continue
        s=ss[-1];h,a=_score(r);fav=str(s.get('favorite_side') or '').upper();ah=s.get('ah') or {};one=s.get('one_x_two') or {};au=ag.get((fid,str(s.get('observed_at'))),{})
        settle=None
        try:settle=settle_asian_handicap(h,a,float(ah.get('selected_side_line')),float(ah.get('selected_side_price')),fav).settlement.value
        except (TypeError,ValueError):pass
        price=ah.get('selected_side_price');market_side='HOME_FAVORITE' if fav=='H' else 'AWAY_FAVORITE' if fav=='A' else 'UNKNOWN'
        outcomes.append({'fixture_id':fid,'football_day':s.get('football_day'),'league':s.get('league'),'home':s.get('home'),'away':s.get('away'),'favorite_side':fav,'market_side':market_side,'favorite_team':s.get('home') if fav=='H' else s.get('away') if fav=='A' else None,'underdog_team':s.get('away') if fav=='H' else s.get('home') if fav=='A' else None,'favorite_1x2_price':one.get('home') if fav=='H' else one.get('away') if fav=='A' else None,'favorite_fair_probability':s.get('favorite_fair_probability'),'favorite_probability_bucket':_prob_bucket(s.get('favorite_fair_probability')),'ah_line':ah.get('selected_side_line'),'ah_price':price,'ah_price_bucket':_price_bucket(price),'ah_core_price':_core(price),'scan_count':len(ss),'first_ah_line':(ss[0].get('ah') or {}).get('selected_side_line'),'first_ah_price':(ss[0].get('ah') or {}).get('selected_side_price'),'movement':_movement(ss[0],s),'match_status':au.get('eligibility_status','UNCLASSIFIED'),'ft_home_goals':h,'ft_away_goals':a,'favorite_ah_settlement':settle,'price_result':_price_result(settle),'price_winner_side':'FAVORITE' if settle in ('FULL_WIN','HALF_WIN') else 'UNDERDOG' if settle in ('FULL_LOSS','HALF_LOSS') else 'PUSH' if settle=='PUSH' else 'UNSETTLED','price_winner_home_away':('HOME' if fav=='H' else 'AWAY') if settle in ('FULL_WIN','HALF_WIN') else ('AWAY' if fav=='H' else 'HOME') if settle in ('FULL_LOSS','HALF_LOSS') else 'PUSH' if settle=='PUSH' else 'UNSETTLED','result_join':'EXACT_FIXTURE_ID_ONLY','research_only':True})
    p=root/OUTCOMES;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in outcomes),encoding='utf-8')
    def aggregate(keys,core_only=False):
        groups=defaultdict(list)
        for x in outcomes:
            if core_only and not x['ah_core_price']:continue
            groups[tuple(str(x.get(k,'UNKNOWN')) for k in keys)].append(x)
        out=[]
        for vals,rs in groups.items():
            pc=Counter(x['price_result'] for x in rs);n=sum(pc[x] for x in ('WIN','HALF_WIN','PUSH','HALF_LOSS','LOSS'));favwin=pc['WIN']+pc['HALF_WIN'];dogwin=pc['LOSS']+pc['HALF_LOSS'];ci=_wilson(favwin,n)
            out.append({**dict(zip(keys,vals)),'n':len(rs),'settled_n':n,'full_win':pc['WIN'],'half_win':pc['HALF_WIN'],'push':pc['PUSH'],'half_loss':pc['HALF_LOSS'],'full_loss':pc['LOSS'],'favorite_price_win_n':favwin,'underdog_price_win_n':dogwin,'favorite_price_win_pct':round(100*favwin/n,2) if n else None,'underdog_price_win_pct':round(100*dogwin/n,2) if n else None,'push_pct':round(100*pc['PUSH']/n,2) if n else None,'favorite_win_wilson95_low':ci[0],'favorite_win_wilson95_high':ci[1],'sample_label':_sample(n)})
        return sorted(out,key=lambda x:-x['n'])
    baseline=aggregate(['market_side','ah_line'],True);bmap={(x['market_side'],x['ah_line']):x.get('favorite_price_win_pct') for x in baseline}
    by_state=aggregate(['market_side','ah_line','ah_price_bucket'],True)
    for x in by_state:
        b=bmap.get((x['market_side'],x['ah_line']));x['baseline_favorite_price_win_pct']=b;x['difference_vs_line_baseline_pp']=round(x['favorite_price_win_pct']-b,2) if b is not None and x['favorite_price_win_pct'] is not None else None
    payload={'schema_version':'2.1','classification':'RESEARCH_V2_AH_MARKET_STATE_STATISTICS','generated_at':datetime.now(timezone.utc).isoformat(),'research_only':True,'recommendation_semantics':False,'primary_market':'ASIAN_HANDICAP','core_ah_decimal_odds_range':[1.80,2.20],'price_buckets':['1.80-1.89','1.90-1.99','2.00-2.09','2.10-2.20'],'one_x_two_role':'CONTEXT_FAIR_PROBABILITY_ONLY','price_win_definition':'ASIAN_HANDICAP_SETTLEMENT_ONLY','notes':['Market states separate HOME_FAVORITE from AWAY_FAVORITE.','PRICE WIN includes FULL/HALF win for descriptive side-frequency; five settlement states remain preserved.','Fixture statistics use one latest observed pre-match market state; all scan observations remain in the source timeline.','Movement is first-to-last; favorite-side switches are isolated as FAVORITE_SWITCH.','All FT joins require exact fixture_id.'],'snapshot_rows':len(snaps),'unique_snapshot_fixtures':len(grouped),'settled_fixtures':len(outcomes),'core_price_settled_fixtures':sum(x['ah_core_price'] for x in outcomes),'missing_result_fixtures':missing,'ambiguous_result_fixtures':len(ambiguous),'baseline_by_market_side_line':baseline,'market_state_by_side_line_price':by_state,'market_state_by_side_line_price_probability':aggregate(['market_side','ah_line','ah_price_bucket','favorite_probability_bucket'],True),'market_state_by_side_line_price_movement':aggregate(['market_side','ah_line','ah_price_bucket','movement'],True),'all_by_movement':aggregate(['movement'])}
    q=root/REPORT;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');return payload

if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False))
