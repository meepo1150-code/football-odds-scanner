"""Offline reproducible research; never writes outside --output. See PROTOCOL.md."""
from __future__ import annotations
import argparse, collections as co, csv, hashlib, json, math, subprocess, sys, gzip
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from odds_scanner.asian_settlement import settle_asian_handicap, settle_asian_total
from odds_scanner.research_population import exclusion_reason
from odds_scanner.research_v2_integrity import trusted_snapshot
BKK=ZoneInfo('Asia/Bangkok'); SEED=20261101; REPS=2000
PRIMARY='CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED'

def dt(x):
    try:
        d=datetime.fromisoformat(str(x).replace('Z','+00:00'))
        return d.astimezone(BKK) if d.tzinfo else None
    except (ValueError,TypeError):return None

def day(t):return (t-timedelta(hours=5)).date().isoformat()
def num(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def quarter(x):return num(x) and abs(x*4-round(x*4))<1e-8

def read(p):
    if not p.exists():return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]

def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [clean(v) for v in x]
    if isinstance(x,np.generic):return clean(x.item())
    if isinstance(x,float) and not math.isfinite(x):return None
    return x

def csvout(p,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})

def ci(a):
    a=np.asarray(a,dtype=float)
    if not len(a):return [None,None]
    rng=np.random.default_rng(SEED); vals=[]
    for _ in range(REPS):vals.append(float(a[rng.integers(len(a),size=len(a))].mean()))
    return np.quantile(vals,[.025,.975]).tolist()

def paired(a):
    a=np.array(a,dtype=float)
    if not len(a):return {'n':0,'mean_difference':None,'ci95':[None,None],'p':None}
    rng=np.random.default_rng(SEED);obs=abs(a.mean())
    p=(1+sum(abs((a*rng.choice([-1,1],len(a))).mean())>=obs-1e-12 for _ in range(REPS)))/(REPS+1)
    return {'n':len(a),'mean_difference':float(a.mean()),'ci95':ci(a),'p':p,'sd':float(a.std(ddof=1)) if len(a)>1 else None}

def fdr(items):
    valid=sorted([(r['p'],i) for i,r in enumerate(items) if r.get('p') is not None]);q=1.
    for rank in range(len(valid)-1,-1,-1):
        p,i=valid[rank];q=min(q,p*len(valid)/(rank+1));items[i]['q_bh']=q


def market(r,m,side=None):
    if m=='AH':
        x=r.get('ah') or {}; side=side or r.get('_favorite')
        if side not in ('H','A'):return None
        prefix='home' if side=='H' else 'away'; opp='away' if side=='H' else 'home'
        line=x.get(prefix+'_line');price=x.get(prefix+'_price');other=x.get(opp+'_price')
        if not quarter(line) or not quarter(x.get(opp+'_line')) or abs(line+x[opp+'_line'])>1e-8:return None
    else:
        x=r.get('ou') or {};side=side or 'O';line=x.get('line')
        price=x.get('over_price' if side=='O' else 'under_price');other=x.get('under_price' if side=='O' else 'over_price')
        if not quarter(line) or line<0:return None
    if not all(num(v) and v>1 for v in (price,other)):return None
    return {'market':m,'side':side,'line':line,'price':price,'opposite_price':other,'fair_share':other/(price+other)}

def bet(r,m,side=None,restrict=True):
    x=market(r,m,side)
    if not x or (restrict and not 1.8<=x['price']<=2.2) or r.get('_ft') is None:return None
    h,a=r['_ft'];s=(settle_asian_handicap if m=='AH' else settle_asian_total)(h,a,x['line'],x['price'],x['side'])
    return {**x,'fixture_id':r['fixture_id'],'league':r.get('league'),'kickoff':r['kickoff'],'observed_at':r['observed_at'],
            'settlement':s.settlement.value,'profit':s.profit_units,'goal_difference':h-a,'total_goals':h+a}


def stats(bets):
    if not bets:return {'bets':0,'fixtures':0,'roi':None,'wr':None,'ci95':[None,None]}
    dist=co.Counter(b['settlement'] for b in bets);w=dist['FULL_WIN']+.5*dist['HALF_WIN'];l=dist['FULL_LOSS']+.5*dist['HALF_LOSS']
    clusters=co.defaultdict(list)
    for b in bets:clusters[b['fixture_id']].append(b['profit'])
    # Equal fixture weight for repeated-snapshot diagnostics; stake ROI separately below.
    c=[np.mean(v) for v in clusters.values()];profits=[b['profit'] for b in sorted(bets,key=lambda b:(b['kickoff'],b['fixture_id']))]
    equity=np.cumsum([0]+profits);peak=np.maximum.accumulate(equity);streak=longest=0
    for p in profits:streak=streak+1 if p<0 else 0;longest=max(longest,streak)
    return {'bets':len(bets),'fixtures':len(clusters),'settlements':dict(dist),'wr':w/(w+l) if w+l else None,
            'positive_return_bet_fraction':sum(p>0 for p in profits)/len(profits),'roi':float(np.mean(profits)),
            'average_profit_units':float(np.mean(profits)),'profit_units':float(sum(profits)),
            'average_odds':float(np.mean([b['price'] for b in bets])),'average_fair_share':float(np.mean([b['fair_share'] for b in bets])),
            'fixture_weighted_roi':float(np.mean(c)),'ci95':ci(c),'max_drawdown':float(max(peak-equity)),
            'longest_losing_streak':longest,'clv':None,'clv_status':'NO_INDEPENDENT_VERIFIED_CLOSE'}


def slotrow(rows,h,grace=15):
    if not rows:return None
    target=datetime.fromisoformat(rows[0]['_day']).replace(tzinfo=BKK)+timedelta(days=h==0,hours=h)
    eligible=[r for r in rows if target<=r['_time']<=target+timedelta(minutes=grace)]
    return min(eligible,key=lambda r:r['_time']) if eligible else None


def audit(root,out):
    inventory=[]
    for p in sorted(root.glob('data/**/*')):
        if p.is_file() and not p.name.startswith('.'):
            inventory.append({'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    csvout(out/'input_manifest.csv',inventory)
    inputs=['europe_pinnacle_research_v2_snapshots','v2_mainline_snapshots']
    raw=[]
    for name in inputs:
        for i,r in enumerate(read(root/f'data/normalized/{name}.jsonl'),1):raw.append({**r,'_source':name,'_row':i})
    results=co.defaultdict(list)
    for r in read(root/'data/normalized/oddspapi_finished_results.jsonl'):results[str(r.get('fixture_id'))].append(r)
    conflicts={str(r.get('fixture_id')) for r in read(root/'data/normalized/oddspapi_finished_results.conflicts.jsonl')}
    identities=co.defaultdict(set)
    for r in raw:
        if dt(r.get('kickoff')):identities[str(r.get('fixture_id'))].add((r.get('home'),r.get('away'),dt(r['kickoff']).isoformat()))
    seen=set();excluded=[];accepted=[];master=[];hist=[];sources=co.Counter()
    for r in raw:
        fid=str(r.get('fixture_id'));sem=r.get('source_semantics');sources[str(sem)]+=1
        t=dt(r.get('observed_at'));k=dt(r.get('kickoff'));flags=[];reason=None
        historical=bool('HISTORICAL' in str(sem) or r.get('historical_provenance'))
        if historical:hist.append(r);reason='HISTORICAL_RECOVERY_SEPARATE'
        elif not t or not k:reason='MISSING_TIME'
        elif t>=k:reason='AT_OR_AFTER_KICKOFF'
        elif len(identities[fid])>1:reason='INCONSISTENT_FIXTURE_IDENTITY'
        elif not r.get('home') or not r.get('away'):reason='MISSING_TEAMS'
        elif not trusted_snapshot(r):reason='UNTRUSTED_SNAPSHOT'
        elif exclusion_reason(r):reason='SCOPE:'+exclusion_reason(r)
        if not reason and sem not in {PRIMARY,'PROPLINE_PINNACLE_TWO_SIDED_CORE_MAINLINE','PINNWIRE_PREMATCH_FULL_SNAPSHOT'}:reason='UNVERIFIED_SOURCE_SEMANTICS'
        score_set={(x.get('ft_home_goals'),x.get('ft_away_goals')) for x in results[fid]}
        score_set={x for x in score_set if all(type(v)is int and v>=0 for v in x)}
        ft=next(iter(score_set)) if len(score_set)==1 and fid not in conflicts else None
        if fid in conflicts or len(score_set)>1:flags.append('FT_CONFLICT')
        if ft is None:flags.append('MISSING_FT')
        one=r.get('one_x_two') or {};hp=one.get('home');ap=one.get('away')
        favorite=('H' if hp<=ap else 'A') if all(num(v) and v>1 for v in (hp,ap)) else r.get('favorite_side')
        if not all(num(v) and v>1 for v in (hp,ap)):flags.append('FAVORITE_FROM_SOURCE_NO_1X2')
        if r.get('price_changed_at'):
            changed=dt(r['price_changed_at'])
            if changed and t and changed>t:reason=reason or 'FUTURE_QUOTE_TIMESTAMP'
            elif changed and t and (t-changed).total_seconds()>3600:flags.append('OLD_CHANGE_TIME_NOT_PROOF_OF_STALENESS')
        else:flags.append('QUOTE_CHANGE_AGE_UNAVAILABLE')
        if sem==PRIMARY:flags.append('CURRENT_ENDPOINT_FRESHNESS_CONTRACT_NOT_PER_ROW_RAW_REVERIFIED')
        else:flags.append('EXECUTION_FRESHNESS_UNPROVEN')
        if k and r.get('football_day')!=day(k):flags.append('STORED_DAY_DIFFERS_FROM_KICKOFF_05_CUTOFF')
        r.update(_time=t,_kick=k,_day=day(k) if k else None,_ft=ft,_favorite=favorite,_flags=flags)
        for m in ('AH','OU'):
            if market(r,m) is None:flags.append('MISSING_OR_INVALID_'+m)
        key=(fid,r.get('bookmaker'),r.get('observed_at'),json.dumps(r.get('ah'),sort_keys=True),json.dumps(r.get('ou'),sort_keys=True))
        if not reason and key in seen:reason='DUPLICATE_OBSERVATION'
        seen.add(key)
        if reason:excluded.append({'source':r['_source'],'row':r['_row'],'fixture_id':fid,'reason':reason})
        else:accepted.append(r)
        for m in ('AH','OU'):
            x=market(r,m);b=bet(r,m,restrict=False)
            master.append({'source_file':r['_source'],'source_row':r['_row'],'fixture_id':fid,'league':r.get('league'),'home':r.get('home'),'away':r.get('away'),
                           'bookmaker':r.get('bookmaker'),'kickoff':r.get('kickoff'),'football_day_05':r['_day'],
                           'scan_slot':r.get('scheduled_target_at'),'actual_observation_time':r.get('observed_at'),
                           'hours_before_kickoff':(k-t).total_seconds()/3600 if k and t else None,'market':m,
                           'ah':r.get('ah'),'ou':r.get('ou'),'one_x_two':one,'ft_home':ft[0] if ft else None,'ft_away':ft[1] if ft else None,
                           'selection':x,'settlement':b['settlement'] if b else None,'profit_units':b['profit'] if b else None,
                           'data_source':sem,'quality_flags':flags,'exclusion':reason,'kind':'HISTORICAL_RECONSTRUCTION' if historical else 'ACTUAL_OBSERVATION'})
    csvout(out/'master_research_dataset.csv',master);csvout(out/'exclusions.csv',excluded)
    primary=[r for r in accepted if r.get('source_semantics')==PRIMARY and r.get('bookmaker')=='pinnacle']
    # Exact-ID cohorts only; do not treat alternative provider IDs as independent in pooled tests.
    coverage=[]
    for label,rows in [('PRIMARY_PINNACLE_CURRENT',primary),('ALL_ACCEPTED_SEPARATE_COHORTS',accepted)]:
        coverage.append({'cohort':label,'snapshots':len(rows),'fixtures':len({r['fixture_id'] for r in rows}),
                         'ft_fixtures':len({r['fixture_id'] for r in rows if r['_ft']}),'first':min((r['observed_at'] for r in rows),default=None),
                         'last':max((r['observed_at'] for r in rows),default=None)})
    leagues=[]
    for league in sorted({r.get('league') or 'UNKNOWN' for r in primary}):
        rs=[r for r in primary if (r.get('league') or 'UNKNOWN')==league]
        leagues.append({'league':league,'snapshots':len(rs),'fixtures':len({r['fixture_id'] for r in rs}),
                        'ft_fixtures':len({r['fixture_id'] for r in rs if r['_ft']}),'ah_rows':sum(market(r,'AH')is not None for r in rs),'ou_rows':sum(market(r,'OU')is not None for r in rs)})
    csvout(out/'league_coverage.csv',leagues)
    ledger=read(root/'data/normalized/research_v2_slot_ledger.jsonl');csvout(out/'scan_ledger.csv',ledger)
    archives=[]
    for name in ['oddspapi_history_ticks','oddspapi_prematch_joined','oddspapi_settled_history','five_dollar_snapshots']:
        rs=read(root/f'data/normalized/{name}.jsonl');archives.append({'file':name,'rows':len(rs),'reason':'HISTORICAL_TICKS_OR_AGGREGATED_OPEN_CLOSE_NOT_LIVE_SCHEDULE_RECEIPTS'})
    report={'base_commit':'3b055dd067629cc134dd834df7afcd4f331182dc','input_files_hashed':len(inventory),'source_rows':len(raw),'source_semantics':dict(sources),'cohorts':coverage,
            'exclusions':dict(co.Counter(r['reason'] for r in excluded)),'quality_flags':dict(co.Counter(f for r in accepted for f in r['_flags'])),
            'historical_recovery_rows':len(hist),'historical_recovery_fixtures':len({r['fixture_id'] for r in hist}),'archives_separate':archives,
            'ledger_states':dict(co.Counter(r.get('state') for r in ledger)),
            'result_conflict_ids':sorted(conflicts),'scope':'All committed data inventoried; historical git deletions and expired Actions artifacts not recovered; dashboard HTML returned HTTP 200 in separate verification; rendered UI and all deployed data not independently reconciled.',
            'raw_receipts':len(read(root/'data/normalized/research_v2_provider_responses.jsonl'))}
    dump(out/'01_coverage.json',report)
    return primary,accepted,ledger,report

def grouped(rows,same_day=False):
    g=co.defaultdict(list)
    for r in rows:
        if same_day and day(r['_time'])!=r['_day']:continue
        g[r['fixture_id']].append(r)
    return {k:sorted(v,key=lambda r:r['_time']) for k,v in g.items()}


def comparisons(groups,out):
    result=[];decisions=[];infer=[];records=[]
    for label,left,right in [('FIRST_LAST',lambda rs:rs[0],lambda rs:rs[-1]),('15_18',lambda rs:slotrow(rs,15),lambda rs:slotrow(rs,18)),('18_21',lambda rs:slotrow(rs,18),lambda rs:slotrow(rs,21))]:
        for m in ('AH','OU'):
            early=[];late=[];diff=[];changed=0;proxy=[];ind_a=[];ind_b=[];ind_diff=[]
            for fid,rs in groups.items():
                a,b=left(rs),right(rs)
                if not a or not b or a['_time']>=b['_time']:continue
                aa=bet(a,m);bb=bet(b,m)
                if aa and bb:ind_a.append(aa);ind_b.append(bb);ind_diff.append(bb['profit']-aa['profit'])
                x=market(a,m);y=market(b,m,x['side'] if x else None)
                if not x or not y:continue
                if x['line']!=y['line']:changed+=1;continue
                aa=bet(a,m,x['side']);bb=bet(b,m,x['side'])
                if not aa or not bb:continue
                early.append(aa);late.append(bb);d=bb['profit']-aa['profit'];diff.append(d);proxy.append(aa['price']/bb['price']-1)
                records.append({'comparison':label,'market':m,'fixture_id':fid,'early':aa,'late':bb,'difference':d})
            p=paired(diff);p.update(comparison=label,market=m,mode='SAME_SIDE_SAME_LINE');infer.append(p)
            result.append({'comparison':label,'market':m,'line_changes_excluded':changed,'early':stats(early),'late':stats(late),
                           'paired_difference':p,'last_observed_price_ratio_proxy':float(np.mean(proxy)) if proxy else None})
            p2=paired(ind_diff);p2.update(comparison=label,market=m,mode='INDEPENDENT_FAVORITE_OR_OVER_ON_MATCHED_FIXTURES');infer.append(p2)
            decisions.append({'comparison':label,'market':m,'early':stats(ind_a),'late':stats(ind_b),'paired_difference':p2})
    fdr(infer);dump(out/'02_first_last.json',{'price_only':result,'independent_benchmark':decisions});csvout(out/'paired_returns.csv',records)
    return infer


def category(a,b,m,side):
    x=market(a,m,side);y=market(b,m,side)
    if not x or not y:return None
    dl=round(y['line']-x['line'],8);dp=y['price']-x['price']
    if abs(dl)>=.5:return 'LINE_UP_050_PLUS' if dl>0 else 'LINE_DOWN_050_PLUS'
    if abs(dl)>=.25:return 'LINE_UP_025' if dl>0 else 'LINE_DOWN_025'
    if dp<-.01:return 'SAME_LINE_PRICE_DOWN'
    if dp>.01:return 'SAME_LINE_PRICE_UP'
    return 'STABLE'


def movements(groups,out):
    buckets=co.defaultdict(list);features=[]
    for fid,rs in groups.items():
        if len(rs)<2:continue
        for m in ('AH','OU'):
            a,b=rs[0],rs[-1];x=market(a,m)
            if not x:continue
            side=x['side'];y=market(b,m,side);entry=bet(b,m,side)
            if not y or not entry:continue
            cat=category(a,b,m,side);path=[market(r,m,side) for r in rs];path=[p for p in path if p]
            # Reversals only comparable on an unchanged line throughout the path.
            rev=None;continuous=None
            if len(path)>=3 and len({p['line'] for p in path})==1:
                dif=np.diff([p['price'] for p in path]);signs=np.sign(dif[np.abs(dif)>.01]);rev=bool(len(signs)>1 and np.any(signs[1:]!=signs[:-1]));continuous=bool(len(signs)>1 and not rev)
            buckets[(m,cat)].append(entry)
            if rev:buckets[(m,'REVERSAL_UNCHANGED_LINE')].append(entry)
            if continuous:buckets[(m,'CONTINUOUS_UNCHANGED_LINE')].append(entry)
            features.append({'fixture_id':fid,'market':m,'league':a.get('league'),'category':cat,'initial_line':x['line'],'last_line':y['line'],
                             'price_change':y['price']-x['price'],'normalized_share_change':y['fair_share']-x['fair_share'],
                             'line_changed_probability_not_comparable':x['line']!=y['line'],'goal_difference':entry['goal_difference'],
                             'total_goals':entry['total_goals'],'profit':entry['profit'],'reversal':rev})
    result=[]
    for (m,c),bets in sorted(buckets.items()):
        result.append({'market':m,'category':c,**stats(bets),'mean_goal_difference':float(np.mean([b['goal_difference'] for b in bets])),
                       'mean_total_goals':float(np.mean([b['total_goals'] for b in bets]))})
    dump(out/'03_movement.json',{'categories':result,'interpretation':'Descriptive correlation only; overlapping reversal categories; final-scan movement is known only at final receipt. Controlled out-of-time model results in predictive_validation.json.'})
    csvout(out/'movement_features.csv',features)
    return result


def timing(rows,out):
    edges=[0,1,2,3,4,6,9,12,18,24,float('inf')];labels=['T-1','T-2','T-3','T-4','T-6','T-9','T-12','T-18','T-24','T-24+']
    buckets=co.defaultdict(list);observations=co.Counter();byfid=co.defaultdict(dict)
    for r in sorted(rows,key=lambda r:r['_time']):
        h=(r['_kick']-r['_time']).total_seconds()/3600
        idx=next(i for i in range(10) if edges[i]<h<=edges[i+1])
        observations[labels[idx]]+=1
        # First entering each bin: online, at most one fixture per bin and bookmaker cohort.
        byfid[r['fixture_id']].setdefault(labels[idx],r)
    results=[]
    for label in labels:
        rs=[d[label] for d in byfid.values() if label in d]
        for m in ('AH','OU'):
            bs=[b for r in rs if (b:=bet(r,m))];binary=[b for b in bs if abs(b['line']*2-round(b['line']*2))<1e-8 and int(round(b['line']*2))%2]
            cal=None
            if binary:
                probs=np.array([b['fair_share'] for b in binary]);actual=np.array([b['settlement']=='FULL_WIN' for b in binary]);cal=float(np.mean((actual-probs)**2))
            results.append({'bin':label,'market':m,'available_fixtures':len(rs),'observations':observations[label],**stats(bs),'binary_half_line_n':len(binary),'binary_half_line_brier':cal})
    contrasts=[]
    for m in ('AH','OU'):
        early=[];late=[];d=[]
        for fid,rs in grouped(rows).items():
            aa=[r for r in rs if 6<(r['_kick']-r['_time']).total_seconds()/3600<=12]
            bb=[r for r in rs if 1<(r['_kick']-r['_time']).total_seconds()/3600<=3]
            if not aa or not bb:continue
            a=aa[0];b=bb[0];x=market(a,m);y=market(b,m,x['side'] if x else None)
            if not x or not y or x['line']!=y['line']:continue
            side=x['side'];x=bet(a,m,side);y=bet(b,m,side)
            if x and y:early.append(x);late.append(y);d.append(y['profit']-x['profit'])
        p=paired(d);p.update(market=m,comparison='MATCHED_SAME_LINE_T6_12_TO_T1_3');contrasts.append(p)
    fdr(contrasts);dump(out/'04_timing.json',{'bins':results,'matched_same_selection_same_line':contrasts,
                                          'note':'Bin samples differ; no optimal-time claim from unpaired ROI. CLV unavailable. Same fixture may enter multiple bins; paired contrasts use each fixture once.'})
    return contrasts


def strategies(groups,ledger,out):
    schedules={};summary=[];coverage=[];betmaps={};bywindow=co.defaultdict(co.Counter)
    for grace in (15,30):
        for name in ('A','B','C','D'):
            picks={};market_picks={'AH':{},'OU':{}};setup_count=0
            for fid,rs in groups.items():
                setup=slotrow(rs,15,grace);decision=slotrow(rs,18,grace)
                if setup:setup_count+=1
                if name=='B':
                    elig=[decision] if decision else [];r=decision
                elif name=='D':
                    elig=[r for r in rs if 1<(r['_kick']-r['_time']).total_seconds()/3600<=3];r=elig[0] if elig else None
                else:
                    hours=[15,18,21]
                    if name=='A':
                        hours+=[0]
                        if datetime.fromisoformat(rs[0]['_day']).weekday()>=5:hours+=[12]
                    elig=[v for h in hours if (v:=slotrow(rs,h,grace))];r=min(elig,key=lambda r:r['_time']) if elig else None
                if r:picks[fid]=r
                for market_name in ('AH','OU'):
                    tradable=[x for x in elig if market(x,market_name) and 1.8<=market(x,market_name)['price']<=2.2]
                    if tradable:market_picks[market_name][fid]=min(tradable,key=lambda x:x['_time'])
                if grace==15 and name=='B':
                    k=rs[0]['_kick'];h=k.hour+k.minute/60
                    label='BEFORE_18' if 6<=h<18 else '18_21' if 18<=h<21 else '21_00' if h>=21 else '00_03' if h<3 else '03_06'
                    bywindow[label]['available_fixtures']+=1;bywindow[label]['decision_present']+=bool(r);bywindow[label]['setup_and_decision']+=bool(r and setup)
                    target=datetime.fromisoformat(rs[0]['_day']).replace(tzinfo=BKK)+timedelta(hours=18)
                    strict=[x for x in rs if target<=x['_time']<=target]  # exact new receipt at strict deadline
                    bywindow[label]['new_18_scan_available_by_1800_exact']+=bool(strict)
                    coverage.append({'fixture_id':fid,'league':rs[0].get('league'),'kickoff':rs[0]['kickoff'],'kickoff_group':label,
                                     'has_1500_setup':bool(setup),'has_1800_receipt_by_1815':bool(r),'strict_1800_new_scan':bool(strict),
                                     'decision_actual_at':r['observed_at'] if r else None,'reason':None if r else 'MISSING_18_RECEIPT_OR_KICKOFF_PASSED'})
            if grace==15:schedules[name]=picks
            for m in ('AH','OU'):
                bs=[b for r in market_picks[m].values() if (b:=bet(r,m))]
                summary.append({'strategy':name,'grace_minutes':grace,'market':m,'coverage_fixtures':len(picks),'population_fixtures':len(groups),
                                'eligible_market_price_fixtures':len(market_picks[m]),**stats(bs)})
                if grace==15:betmaps[(name,m)]={b['fixture_id']:b for b in bs}
    contrasts=[]
    for m in ('AH','OU'):
        a=betmaps['A',m];b=betmaps['B',m];common=sorted(set(a)&set(b));d=[b[k]['profit']-a[k]['profit'] for k in common]
        p=paired(d);p.update(market=m,comparison='B_MINUS_A_MATCHED_BENCHMARK',missing_B_among_A=len(set(a)-set(b)),B_extra=len(set(b)-set(a)))
        p['noninferiority_margin']=-.01;p['exploratory_matched_benchmark_ci_inside_margin']=bool(p['ci95'][0] is not None and p['ci95'][0]>-.01)
        p['required_future_pairs_approx']=math.ceil(((1.644854+.841621)*p['sd']/.01)**2) if p.get('sd') else None
        p['power_note']='Normal approximation, observed SD exploratory; collect NEW independent pairs. No credit for this inspected retrospective data.'
        contrasts.append(p)
    fdr(contrasts)
    # Request evidence is incomplete; sum only recorded requests, retaining zero/failure receipts.
    calls=co.defaultdict(int);dups=set()
    for r in ledger:
        key=json.dumps(r,sort_keys=True)
        if key in dups:continue
        dups.add(key);t=dt(r.get('actual_observed_at'));n=r.get('requests_used')
        if t and type(n)is int:calls[day(t)]+=n
    api={'recorded_ledger_requests_by_day':dict(sorted(calls.items())),'recorded_requests_total':sum(calls.values()),
         'ledger_is_complete_billing_record':False,'planned_rounds_per_week':{'A':30,'B':14,'C':21},
         'equal_cost_per_round_estimated_saving_B_vs_A':1-14/30,'equal_cost_per_round_estimated_saving_C_vs_A':1-21/30,
         'requests_30_day_if_fixed_requests_per_round_k':{'A':'~128.57*k','B':'60*k','C':'90*k','D':'UNKNOWN; depends on kickoff batching'},
         'warning':'Not actual billing savings; workload, quota skips and fixture batches differ.'}
    dump(out/'05_schedules.json',{'summaries':summary,'matched_contrasts':contrasts,'B_kickoff_groups':dict(bywindow),'api':api,
                                'coverage_A_minus_B':len(set(schedules['A'])-set(schedules['B'])),
                                'coverage_A_B_intersection':len(set(schedules['A'])&set(schedules['B'])),
                                'setup_and_decision_pairs':sum(r['has_1500_setup'] and r['has_1800_receipt_by_1815'] for r in coverage),
                                'policy':'A/C first usable scheduled receipt; B first 18 receipt; D first observed T1–3 receipt. No hindsight choice of last scan. Operational B deadline is 18:15, not 18:00.'})
    csvout(out/'two_round_fixture_coverage.csv',coverage)
    csvout(out/'strategy_bets.csv',[{'strategy':name,**b} for (name,m),bs in betmaps.items() for b in bs.values()])
    return contrasts

def predictive(groups,out,all_groups=None):
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder,StandardScaler
    from sklearn.pipeline import make_pipeline
    from sklearn.linear_model import Ridge
    import pandas as pd
    result=[];predictions=[];contrasts=[]
    for experiment in ('FIRST_LAST_CONTROLLED','SETUP_DECISION'):
        for m in ('AH','OU'):
            samples=[]
            for fid,rs in groups.items():
                a,b=(rs[0],rs[-1]) if experiment=='FIRST_LAST_CONTROLLED' else (slotrow(rs,15),slotrow(rs,18))
                if not a or not b or a['_time']>=b['_time'] or not b['_ft']:continue
                x=market(a,m,'H' if m=='AH' else 'O');y=market(b,m,'H' if m=='AH' else 'O')
                if not x or not y:continue
                base=x if experiment=='FIRST_LAST_CONTROLLED' else y
                available=[r for r in (all_groups or groups).get(fid,rs) if r['_time']<=b['_time']]
                path=[market(r,m,'H' if m=='AH' else 'O') for r in available];path=[v for v in path if v]
                h,g=b['_ft'];target=h-g if m=='AH' else h+g
                samples.append({'fixture_id':fid,'date':b['_day'],'target':target,'league':b.get('league') or 'UNKNOWN',
                                'line':base['line'],'price':base['price'],'share':base['fair_share'],'kickoff_hour':b['_kick'].hour+b['_kick'].minute/60,
                                'lead_hours':(a['_kick']-a['_time']).total_seconds()/3600,'line_change':y['line']-x['line'],'price_change':y['price']-x['price'],
                                'share_change':y['fair_share']-x['fair_share'],'initial_line':x['line'],'initial_price':x['price'],
                                'scan_count':len(path),'all_line_range':max(v['line'] for v in path)-min(v['line'] for v in path),
                                'all_price_range':max(v['price'] for v in path)-min(v['price'] for v in path),
                                'decision_time':b['_time'].isoformat()})
            dates=sorted({s['date'] for s in samples})
            if len(dates)<10:
                result.append({'experiment':experiment,'market':m,'status':'INSUFFICIENT_DAYS','n':len(samples)});continue
            d1=dates[int(len(dates)*.6)];d2=dates[int(len(dates)*.8)]
            # 24h embargo (entire previous day removed); all prior labels are retrospective, availability not certified.
            before1=(datetime.fromisoformat(d1)-timedelta(days=1)).date().isoformat()
            before2=(datetime.fromisoformat(d2)-timedelta(days=1)).date().isoformat()
            train=[s for s in samples if s['date']<before1];val=[s for s in samples if d1<=s['date']<before2];test=[s for s in samples if s['date']>=d2]
            info={'experiment':experiment,'market':m,'n':len(samples),'train':len(train),'validation':len(val),'exploratory_test':len(test),'validation_start':d1,'test_start':d2,
                  'status':'EXPLORATORY_RETROSPECTIVE_ONLY','label_availability':'FT join verified by exact ID; historical first-availability of every FT is NOT certified. No deployable trading simulation.'}
            if min(len(train),len(val),len(test))<20:
                info['status']='INSUFFICIENT_SPLIT_SIZE';result.append(info);continue
            basecols=['line','price','share','kickoff_hour','lead_hours'];move=['line_change','price_change','share_change','initial_line','initial_price'];allcols=['scan_count','all_line_range','all_price_range']
            losses={};metrics={}
            for name,cols in [('A_BASELINE',basecols),('B_PLUS_MOVEMENT',basecols+move),('C_PLUS_PAST_SCANS',basecols+move+allcols)]:
                tr=pd.DataFrame(train);va=pd.DataFrame(val);te=pd.DataFrame(test)
                transform=ColumnTransformer([('num',StandardScaler(),cols),('cat',OneHotEncoder(handle_unknown='ignore',sparse_output=False),['league'])])
                model=make_pipeline(transform,Ridge(alpha=10.0))
                model.fit(tr,tr.target);vp=model.predict(va);tp=model.predict(te);loss=(te.target.to_numpy()-tp)**2;losses[name]=loss
                metrics[name]={'validation_mse':float(np.mean((va.target-vp)**2)),'test_mse':float(loss.mean())}
                for s,p in zip(test,tp):predictions.append({'experiment':experiment,'market':m,'model':name,'fixture_id':s['fixture_id'],'date':s['date'],'actual':s['target'],'prediction':float(p)})
            info['metrics']=metrics;result.append(info)
            for name in ('B_PLUS_MOVEMENT','C_PLUS_PAST_SCANS'):
                p=paired(losses['A_BASELINE']-losses[name]);p.update(experiment=experiment,market=m,comparison=name+'_MSE_IMPROVEMENT',relative_lift=1-metrics[name]['test_mse']/metrics['A_BASELINE']['test_mse']);contrasts.append(p)
    fdr(contrasts);dump(out/'predictive_validation.json',{'models':result,'comparisons':contrasts,
           'meaning':'Positive MSE improvement means better FT goal-difference/total prediction on the exploratory chronological test. This is NOT positive betting EV, not causation and not untouched holdout evidence.',
           'selection_policy':'Fixed ridge alpha 10; validation reported without tuning; no model-derived betting picks; frozen production registry has zero patterns.'})
    csvout(out/'out_of_time_predictions.csv',predictions)
    return contrasts


def extended_audit(root,rows,accepted,out):
    primary_byid=grouped(rows);universe={};excluded=co.Counter()
    for r in read(root/'data/normalized/research_v2_daily_fixtures.jsonl'):
        reason=exclusion_reason(r);k=dt(r.get('kickoff'))
        if reason or not k:excluded[reason or 'MISSING_KICKOFF']+=1;continue
        fid=str(r.get('fixture_id'))
        # Scope of the observational study: same kickoff dates as current Pinnacle cohort.
        if rows and min(x['_day'] for x in rows)<=day(k)<=max(x['_day'] for x in rows):universe[fid]=r
    for fid,rs in primary_byid.items():universe.setdefault(fid,rs[0])
    matrix=[];slotcounts=co.defaultdict(co.Counter)
    for fid,r in sorted(universe.items()):
        k=dt(r['kickoff']);fd=day(k);rs=primary_byid.get(fid,[])
        record={'fixture_id':fid,'league':r.get('league'),'football_day':fd,'kickoff':r['kickoff'],'has_primary_snapshot':bool(rs)}
        for h in (0,12,15,18,21):
            target=datetime.fromisoformat(fd).replace(tzinfo=BKK)+timedelta(days=h==0,hours=h)
            eligible=k>target;hit=slotrow(rs,h) if rs else None
            record[f'eligible_{h:02}']=eligible;record[f'observed_{h:02}']=bool(hit)
            slotcounts[(fd,h)]['eligible_fixture_ids']+=eligible;slotcounts[(fd,h)]['observed_ids']+=bool(hit)
        matrix.append(record)
    csvout(out/'discovered_fixture_coverage.csv',matrix)
    csvout(out/'daily_slot_coverage.csv',[{'football_day':d,'slot':f'{h:02}:00',**dict(c)} for (d,h),c in sorted(slotcounts.items())])
    archived=read(root/'data/normalized/oddspapi_history_ticks.jsonl');tickcount=co.Counter()
    def walk(x,k):
        if isinstance(x,dict):
            if 'created_at' in x and 'price' in x:
                t=dt(x.get('created_at'));tickcount['all_ticks']+=1
                tickcount['strict_prematch_ticks' if t and k and t<k else 'missing_time_or_at_after_kickoff']+=1
                if x.get('active')is not True:tickcount['inactive_or_unknown']+=1
            else:
                for v in x.values():walk(v,k)
        elif isinstance(x,list):
            for v in x:walk(v,k)
    for r in archived:walk(r,dt(r.get('kickoff')))
    dump(out/'extended_coverage.json',{'discovered_in_scope_fixture_ids_in_study_dates':len(universe),
                                     'with_primary_snapshot':sum(x['has_primary_snapshot'] for x in matrix),'without_primary_snapshot':sum(not x['has_primary_snapshot'] for x in matrix),
                                     'universe_caveat':'Retrospective discovered-fixture universe; discovery is incomplete and may occur after kickoff. Not proof all fixtures were knowable at decision time. Exact IDs, potential unbridged provider aliases not used as independent tests.',
                                     'discovery_exclusions':dict(excluded),'historical_archive_ticks':dict(tickcount)})
    # Separate archived opening/last comparison: exact same fixture, line, side; no schedule interpretation.
    pairs=co.defaultdict(dict);invalid=co.Counter();used=[]
    for r in read(root/'data/normalized/oddspapi_settled_history.jsonl'):
        t=dt(r.get('quote_at'));k=dt(r.get('kickoff'));m=r.get('market_type');side=r.get('selection');line=r.get('selected_side_line',r.get('line'));price=r.get('price')
        if m not in ('AH','OU') or not t or not k or t>=k or not quarter(line) or not num(price) or not 1.8<=price<=2.2:invalid['invalid_or_outside_price_scope']+=1;continue
        h=r.get('ft_home_goals');a=r.get('ft_away_goals')
        if type(h)is not int or type(a)is not int:invalid['missing_ft']+=1;continue
        s=(settle_asian_handicap if m=='AH' else settle_asian_total)(h,a,line,price,side)
        if abs(s.profit_units-r.get('profit_units',float('inf')))>1e-8:invalid['stored_settlement_mismatch']+=1
        key=(r['fixture_id'],m,line,side);pairs[key][r['snapshot_stage']]={'price':price,'profit':s.profit_units,'quote_at':r['quote_at']}
    summaries=[]
    for m in ('AH','OU'):
        byfixture=co.defaultdict(list);count=0
        for key,v in pairs.items():
            if key[1]!=m or not all(z in v for z in ('OPENING','CLOSING_PREMATCH')):continue
            a=v['OPENING'];b=v['CLOSING_PREMATCH'];d=b['profit']-a['profit'];byfixture[key[0]].append(d);count+=1
            used.append({'fixture_id':key[0],'market':m,'selected_side_line':key[2],'side':key[3],'opening':a,'last_prematch':b,'difference':d})
        summaries.append({'market':m,'fixture_line_side_pairs':count,'fixture_equal_weight_difference':paired([float(np.mean(v)) for v in byfixture.values()])})
    dump(out/'historical_separate_sensitivity.json',{'summaries':summaries,'exclusions':dict(invalid),'warning':'Historical Bet365 change ticks; not live observations or verified execution/closing prices. Alternative lines and sides averaged within fixture; never pooled with primary Pinnacle study.'})
    csvout(out/'historical_same_line_pairs.csv',used)


def render(out):
    a=json.loads((out/'01_coverage.json').read_text());b=json.loads((out/'02_first_last.json').read_text());c=json.loads((out/'03_movement.json').read_text());d=json.loads((out/'04_timing.json').read_text());e=json.loads((out/'05_schedules.json').read_text());p=json.loads((out/'predictive_validation.json').read_text())
    def pct(x):return 'N/A' if x is None else f'{100*x:.2f}%'
    def interval(x):return 'N/A' if x[0] is None else f'[{pct(x[0])}, {pct(x[1])}]'
    common='\n\nEXPLORATORY / NO PROVEN EDGE. Flat stake 1 unit, price 1.80–2.20; AH contemporaneous favorite, OU Over. This benchmark is not a validated betting strategy. WR uses winning/losing stake fractions; pushes excluded. CLV unavailable: last observed quote is not a verified closing quote. All times Asia/Bangkok; football-day cutoff 05:00.\n'
    ext=json.loads((out/'extended_coverage.json').read_text())
    s='# Report 1 — Scan coverage audit\n'+common+f"\nRetrospective discovered in-scope universe during study dates: {ext['discovered_in_scope_fixture_ids_in_study_dates']} IDs; {ext['without_primary_snapshot']} have no current primary quote. Discovery is incomplete and includes post-event records; this is not the decision-time opportunity universe. See discovered_fixture_coverage.csv and daily_slot_coverage.csv for missing observations before outcome filtering.\n"+'\n|Cohort|Snapshots|Fixtures|With FT|\n|---|---:|---:|---:|\n'
    for r in a['cohorts']:s+=f"|{r['cohort']}|{r['snapshots']}|{r['fixtures']}|{r['ft_fixtures']}|\n"
    s+=f"\nHistorical recovery excluded from live analysis: {a['historical_recovery_rows']} rows / {a['historical_recovery_fixtures']} IDs. Exact fixture-ID result join only; other provider cohorts are not pooled as independent fixtures.\n\nExclusions: `{json.dumps(a['exclusions'])}`.\n\n{a['scope']} Raw receipts retained: {a['raw_receipts']}; current endpoint contract was inspected, but every raw market was not independently revalidated. Missing quote-change timestamps are explicitly flagged, never replaced with invented freshness. Scope removals are reported, not silently dropped.\n\nSee input_manifest.csv (all data hashes), master_research_dataset.csv (including excluded and historical rows), league_coverage.csv, scan_ledger.csv, exclusions.csv and 01_coverage.json. Archives, cached provider responses and result evidence are inventoried; existing normalized quotes are the analysis layer, not regenerated from all raw payloads.\n"
    (out/'01_SCAN_COVERAGE.md').write_text(s)
    s='# Report 2 — First versus last scan\n'+common+'\n|Comparison|Market|Paired N|Early ROI|Late ROI|Delta|95% CI delta|BH q|Line changes excluded|\n|---|---|---:|---:|---:|---:|---|---:|---:|\n'
    for r in b['price_only']:
        x=r['paired_difference'];s+=f"|{r['comparison']}|{r['market']}|{x['n']}|{pct(r['early']['roi'])}|{pct(r['late']['roi'])}|{pct(x['mean_difference'])}|{interval(x['ci95'])}|{x.get('q_bh')}|{r['line_changes_excluded']}|\n"
    s+='\nFirst/last are within the kickoff football day. Last is retrospective and not a scheduled execution policy. Different-line returns are excluded from price-only tests. Independent favorite/Over decisions and full five-state settlements are in 02_first_last.json; paired fixture evidence in paired_returns.csv. Odds-only timing differences do not establish predictive edge.\n'
    (out/'02_FIRST_LAST.md').write_text(s)
    s='# Report 3 — Odds movement impact\n'+common+'\n|Market|Category|N|WR|ROI|95% CI|\n|---|---|---:|---:|---:|---|\n'
    for r in c['categories']:s+=f"|{r['market']}|{r['category']}|{r['fixtures']}|{pct(r['wr'])}|{pct(r['roi'])}|{interval(r['ci95'])}|\n"
    s+='\nCategories use the first AH selected-side line, or OU total. A line move changes the contract, so its normalized share change is not a probability change for the same event. Reversal/continuous categories overlap main categories and require an unchanged line throughout. Raw goal difference, total goals and share movements are retained in movement_features.csv.\n\nControlled chronological ridge models condition on initial line, odds/share, league, kickoff hour and lead time; setup/decision models instead start with 18-scan prices. Full sample/split sizes and MSE lift are in predictive_validation.json. FT availability at every historical training date is not certified; these are retrospective diagnostics, not historically executable EV bets.\n'
    for r in p['comparisons']:s+=f"\n- {r['experiment']} / {r['market']} / {r['comparison']}: N={r['n']}, MSE improvement={r['mean_difference']:.5f}, CI={r['ci95']}, q={r.get('q_bh')}, relative lift={pct(r['relative_lift'])}.\n"
    (out/'03_MOVEMENT_IMPACT.md').write_text(s)
    s='# Report 4 — Pre-kickoff timing\n'+common+'\n|Bin|Market|Available fixtures|Bets|WR|ROI|95% CI|\n|---|---|---:|---:|---:|---:|---|\n'
    for r in d['bins']:s+=f"|{r['bin']}|{r['market']}|{r['available_fixtures']}|{r['bets']}|{pct(r['wr'])}|{pct(r['roi'])}|{interval(r['ci95'])}|\n"
    s+='\nBins are (lower, upper] hours before kickoff. First receipt entering each bin is used, one per fixture. These unmatched populations cannot rank optimal timing. Matched same-fixture, same-line, same-side 6–12h vs 1–3h comparisons control league, kickoff and selection by design; price-range restriction fixed in advance.\n'
    for r in d['matched_same_selection_same_line']:s+=f"\n- {r['market']}: N={r['n']}, later-minus-earlier ROI={pct(r['mean_difference'])}, CI={interval(r['ci95'])}, q={r.get('q_bh')}.\n"
    s+='\nCalibration Brier scores are restricted to half-lines; other Asian normalized shares are not binary probabilities. No optimal-time claim or causal interpretation is justified. Global multiple-testing correction across all inferential tests is in all_inference_bh.json; table q-values are within-family.\n'
    (out/'04_TIMING.md').write_text(s)
    s='# Report 5 — Schedule comparison\n'+common+'\nOperational window: scheduled time through +15 minutes, entry at actual receipt. B is therefore an 18:15-deadline experiment, NOT an exact-18:00 decision. No substitute from later scans. A/C enter first available scheduled observation; B enters at 18; D first observation in T-3 to T-1, fixed before outcomes.\n\n|Strategy|Market|Available fixtures|Bets with FT|WR|ROI|Profit|Max DD|Longest loss run|\n|---|---|---:|---:|---:|---:|---:|---:|---:|\n'
    for r in e['summaries']:
        if r['grace_minutes']==15:s+=f"|{r['strategy']}|{r['market']}|{r['coverage_fixtures']}|{r['bets']}|{pct(r['wr'])}|{pct(r['roi'])}|{r.get('profit_units')}|{r.get('max_drawdown')}|{r.get('longest_losing_streak')}|\n"
    s+=f"\nA opportunities absent from B: {e['coverage_A_minus_B']} fixtures (coverage opportunity, not proof of profitable missed bets). Setup + decision pairs: {e['setup_and_decision_pairs']}.\n\n|Kickoff group|Population|18 receipt by 18:15|Both 15 and 18|New 18 scan by exact 18:00|\n|---|---:|---:|---:|---:|\n"
    for key,r in e['B_kickoff_groups'].items():s+=f"|{key}|{r['available_fixtures']}|{r['decision_present']}|{r['setup_and_decision']}|{r['new_18_scan_available_by_1800_exact']}|\n"
    s+='\n03–06 group crosses the 05:00 football-day boundary; actual fixture day controls receipt lookup. Risk metrics are descriptive and sort tied kickoff fixtures by ID; bankroll settlement timestamps are not available. Missing FT remains in coverage but not in ROI. 30-minute sensitivity, paired B-A results and full request ledger are in 05_schedules.json.\n\nPlanned round counts A/B/C = 30/14/21 per week. Equal-cost B saving = 53.33%, C = 30%; these are not measured billable savings. Recorded requests may be incomplete and quota skips distort observed costs. No provider requests were made by this study.\n'
    (out/'05_SCHEDULES.md').write_text(s)
    primary=a['cohorts'][0];A=next(r for r in e['summaries'] if r['strategy']=='A' and r['market']=='AH' and r['grace_minutes']==15);B=next(r for r in e['summaries'] if r['strategy']=='B' and r['market']=='AH' and r['grace_minutes']==15)
    s='# Report 6 — Final recommendation\n'+common+f"\nPrimary current Pinnacle cohort: {primary['snapshots']} observations / {primary['fixtures']} fixtures; {primary['ft_fixtures']} fixtures joined to FT.\n\n"
    answers=[
      ('Do multiple scans improve selection?', 'They increase observed fixture/time coverage. No validated improvement in betting selection is established. Benchmarks and exploratory prediction tests do not pass frozen promotion gates.'),
      ('Does movement predict FT?', 'See controlled out-of-time MSE tests in Report 3; any descriptive association is distinct from incremental prediction. None is proof of positive tradable EV or causation.'),
      ('How different are first and last?', 'Report 2 provides paired same-side/same-line ROI differences and intervals, separately from independent decisions. First/last availability is selective and closing coverage is not proven.'),
      ('What lead time is optimal?', 'NOT ESTABLISHED. Matched T6–12 versus T1–3 tests are reported; bin ROI ranking cannot remove different fixture populations and sparse timing coverage.'),
      ('What is lost at 15/18 only?', f"A covers {A['coverage_fixtures']} fixtures; B covers {B['coverage_fixtures']}; {e['coverage_A_minus_B']} A-covered fixtures lack B coverage. Later movement and opportunities after 18 are unavailable to B; exact missing fixtures are listed."),
      ('Is 15→18 sufficient for real bets?', f"NOT PROVEN. Only {e['setup_and_decision_pairs']} fixtures have both operational receipts. New scan data arriving after 18:00 cannot support an exact-18:00 decision. Missing/incomplete validation and zero frozen validated patterns prevent EV selections."),
      ('Two, three or multiple rounds?', 'Keep current schedule while shadow-testing two and three rounds. Benefit: retain information and avoid premature loss; drawback: higher request and storage cost. Risk: quota failures may impair coverage; request savings must be measured on actual billing receipts.'),
      ('If restricted to two, which times?', 'No statistically defensible optimal pair established. 15/18 is an operational hypothesis for shadow mode, not a recommended performance optimum. It sacrifices late information and pre-18 fixtures; 15/21 or kickoff-relative alternatives need prospective matched evaluation.')]
    for i,(q,ans) in enumerate(answers,1):s+=f'\n{i}. **{q}** {ans}\n'
    s+='\n## Future shadow trial and limitations\n\nDo not change production. Freeze a selection model only after existing gates pass; log all candidate fixtures, actual request/receipt times, missing markets, result first-availability and tradable closing quotes. Use 18:15 as an explicit operational deadline or collect before 18:00; never backdate. Test B-A paired ROI against -1pp, coverage loss <=5%, with one-sided 95% CI and precommitted 90-day minimum / >=3 leagues. Multiple-testing correction and frozen multi-season requirements remain mandatory.\n'
    for r in e['matched_contrasts']:s+=f"\n- {r['market']}: inspected pairs={r['n']}, B-A difference={pct(r['mean_difference'])}, CI={interval(r['ci95'])}; estimated NEW paired fixtures required at 80% power for 1pp margin={r['required_future_pairs_approx']}. This is an SD-based planning estimate, not a proven adequate sample; no retrospective pairs count toward untouched forward evidence.\n"
    s+='\nHistorical recovery can study price paths separately but cannot establish live receipt coverage. Archived snapshots, partial raw receipts, removed leagues, result recovery timing, short season coverage and bookmaker/provider differences constrain external validity. Existing normalized data are not independently reverified against every raw/API source. Repository coverage is not proof of all historically collected or expired-artifact coverage.\n\nReproduce with `python research/multiscan_20261101/analyze.py --output research/multiscan_20261101/results`. Dependencies pinned in requirements.txt. Input SHA-256 manifest identifies exact data; all outputs derive offline. Production schedule, collector, secrets, FT history and dashboard logic are unchanged.\n'
    (out/'06_RECOMMENDATION.md').write_text(s)
    (out/'README.md').write_text('# Multiscan research results\n\nEXPLORATORY — NO PROVEN EDGE\n\n'+''.join(f'- [{p.name}]({p.name})\n' for p in sorted(out.glob('0*.md')))+'\nLarge CSV companions are losslessly gzip-compressed (.csv.gz). See JSON/CSV companions for exact denominators, settlements, paired returns, confidence intervals, quality flags and source hashes.\n')


def compress_outputs(out):
    for p in out.glob('*.csv'):
        if p.stat().st_size>100000:
            p.with_suffix(p.suffix+'.gz').write_bytes(gzip.compress(p.read_bytes(),mtime=0));p.unlink()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=ROOT);ap.add_argument('--output',type=Path,default=ROOT/'research/multiscan_20261101/results');args=ap.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    rows,accepted,ledger,report=audit(args.root,out);groups=grouped(rows,True)
    extended_audit(args.root,rows,accepted,out)
    inference=comparisons(groups,out)+timing(rows,out)+strategies(groups,ledger,out)+predictive(groups,out,grouped(rows));movements(groups,out)
    fdr(inference);dump(out/'all_inference_bh.json',inference)
    # Global correction is authoritative; per-report q_bh is within stated family.
    dump(out/'inference_policy.json',{'global_family_tests':len(inference),'global_q_file':'all_inference_bh.json','individual_reports':'q_bh within family; no promotion from either family or global significance'})
    # Separate-provider sensitivity summaries, never pooled in significance tests.
    sens=[]
    for key in sorted({(str(r.get('source_semantics')),str(r.get('bookmaker'))) for r in accepted}):
        rs=[r for r in accepted if (str(r.get('source_semantics')),str(r.get('bookmaker')))==key];g=grouped(rs,True)
        for m in ('AH','OU'):sens.append({'semantics':key[0],'bookmaker':key[1],'market':m,'available_fixtures':len(g),**stats([b for r in g.values() if (b:=bet(r[0],m))])})
    dump(out/'source_sensitivity.json',sens);render(out);compress_outputs(out)
    print(json.dumps({'primary':report['cohorts'][0],'football_day_fixtures':len(groups),'output':str(out)},indent=2))

if __name__=='__main__':main()
