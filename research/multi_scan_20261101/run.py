"""Offline research. Run from repository root; writes only inside this directory."""
from __future__ import annotations
import sys, json, hashlib, math, subprocess, platform, gzip
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import Ridge
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from odds_scanner.asian_settlement import settle_asian_handicap, settle_asian_total
from odds_scanner.research_population import in_scope, exclusion_reason
from odds_scanner.research_v2_integrity import trusted_snapshot
OUT=Path(__file__).resolve().parent
BKK=timezone(timedelta(hours=7)); SEED=20261101; DRAWS=2000
BASE='c75f7be2c87ea981487d0e4fb9b02a9e9f54dde8'
TESTS=[]

def read(path):
 p=ROOT/path
 if not p.exists(): return []
 return [json.loads(s) for s in p.read_text().splitlines() if s.strip()]
def stamp(v):
 try:
  t=datetime.fromisoformat(str(v).replace('Z','+00:00'))
  return t.astimezone(timezone.utc) if t.tzinfo else None
 except (ValueError,TypeError): return None
def day(t):return (t.astimezone(BKK)-timedelta(hours=5)).date().isoformat()
def number(x):
 try:return float(x) if math.isfinite(float(x)) else None
 except (TypeError,ValueError):return None
def validline(x):return number(x) is not None and abs(float(x)*4-round(float(x)*4))<1e-8
def write_json(name,x):
 (OUT/name).write_text(json.dumps(x,indent=2,ensure_ascii=False,default=str,allow_nan=False)+'\n')
def csv(name,rows):
 pd.DataFrame(rows).to_csv(OUT/name,index=False)
def slot(r):
 t=stamp(r.get('scheduled_target_at')); o=stamp(r.get('observed_at'))
 if not t or not o:return 'MANUAL',False,None
 l=t.astimezone(BKK)
 label=f'{l.hour:02d}:00' if l.minute<15 and l.hour in (0,12,15,18,21) else 'OTHER'
 nominal=l.replace(minute=0,second=0,microsecond=0)
 # Scheduled target seconds can drift; enforce deadline against nominal hour.
 return label, -60 <= (o-nominal).total_seconds() <= 900,nominal

def boot(values,ids, null=0.):
 if not len(values):return {'effect':None,'ci95_low':None,'ci95_high':None,'p':None,'clusters':0}
 f=pd.DataFrame({'id':ids,'v':values}).groupby('id').v.agg(['sum','count'])
 a=f['sum'].to_numpy(); n=f['count'].to_numpy(); rng=np.random.default_rng(SEED)
 means=[]
 for _ in range(20):
  ix=rng.integers(0,len(a),(DRAWS//20,len(a)));means.extend(a[ix].sum(1)/n[ix].sum(1))
 means=np.array(means); m=float(np.mean(values)); lo,hi=np.quantile(means,[.025,.975])
 # Centered bootstrap null, not posterior tail probability.
 p=(1+int(np.sum(abs(means-m)>=abs(m-null))))/(len(means)+1)
 return {'effect':m,'ci95_low':float(lo),'ci95_high':float(hi),'p':p,'clusters':len(a)}

def test(name,values,ids):
 b=boot(values,ids);TESTS.append({'test':name,**b});return b

def bet(r,market,side=None,core=False):
 if not r:return None
 m=r.get('ah' if market=='AH' else 'ou') or {}
 if market=='AH':
  side=side or r['favorite']; key='home' if side=='H' else 'away'
  line=number(m.get(key+'_line'));price=number(m.get(key+'_price'));opp=number(m.get(('away' if side=='H' else 'home')+'_price'))
  if not validline(line) or not validline(m.get(('away' if side=='H' else 'home')+'_line')):return None
  if abs(line+float(m[('away' if side=='H' else 'home')+'_line']))>1e-8:return None
 else:
  side=side or 'O';line=number(m.get('line'));price=number(m.get('over_price' if side=='O' else 'under_price'));opp=number(m.get('under_price' if side=='O' else 'over_price'))
  if not validline(line):return None
 if price is None or opp is None or min(price,opp)<=1:return None
 if core and not 1.8<=price<=2.2:return None
 b={k:r[k] for k in ['fixture_id','league','home','away','kickoff','observed_at','football_day','bookmaker','provider','slot','hours','source_file','source_row','cohort','on_time','same_day']}
 b['country']=r.get('country') or 'UNKNOWN'
 b['league_context']=b['country']+' / '+str(r['league'])
 b.update(market=market,side=side,line=line,price=price,opposite_price=opp,fair_share=opp/(price+opp),ft_home=r.get('ft_home'),ft_away=r.get('ft_away'),result_source=r.get('result_source'),profit=None,settlement=None,win_stake=None,loss_stake=None,clv=None)
 if r.get('ft_home') is not None:
  settled=(settle_asian_handicap if market=='AH' else settle_asian_total)(r['ft_home'],r['ft_away'],line,price,side)
  s=settled.settlement.value;b.update(profit=settled.profit_units,settlement=s,win_stake={'FULL_WIN':1.,'HALF_WIN':.5}.get(s,0.),loss_stake={'FULL_LOSS':1.,'HALF_LOSS':.5}.get(s,0.),goal_difference=r['ft_home']-r['ft_away'],total_goals=r['ft_home']+r['ft_away'])
 return b

def metrics(bets):
 bs=[b for b in bets if b is not None]; settled=[b for b in bs if b['profit'] is not None]
 out={'opportunities':len(bs),'fixtures_available':len({b['fixture_id'] for b in bs}),'bets':len(settled),'fixtures':len({b['fixture_id'] for b in settled}),'missing_ft':len(bs)-len(settled),'clv':None}
 dist=Counter(b['settlement'] for b in settled)
 for k in ['FULL_WIN','HALF_WIN','PUSH','HALF_LOSS','FULL_LOSS']:out[k]=dist[k]
 if not settled:return out
 w=sum(b['win_stake'] for b in settled);l=sum(b['loss_stake'] for b in settled)
 profits=[b['profit'] for b in settled];bt=boot(profits,[b['fixture_id'] for b in settled])
 out.update(wr=w/(w+l) if w+l else None,roi=np.mean(profits).item(),average_profit=np.mean(profits).item(),profit_units=sum(profits),average_odds=float(np.mean([b['price'] for b in settled])),de_vig_price_share=float(np.mean([b['fair_share'] for b in settled])),roi_ci95_low=bt['ci95_low'],roi_ci95_high=bt['ci95_high'])
 # Exact clustered WR confidence interval via cluster stake sums.
 g=pd.DataFrame(settled).groupby('fixture_id')[['win_stake','loss_stake']].sum();ar=g.to_numpy();rng=np.random.default_rng(SEED); wrs=[]
 for _ in range(20):
  ix=rng.integers(0,len(ar),(DRAWS//20,len(ar)));z=ar[ix].sum(1);den=z.sum(1);wrs.extend(z[den>0,0]/den[den>0])
 out.update(wr_ci95_low=float(np.quantile(wrs,.025)) if wrs else None,wr_ci95_high=float(np.quantile(wrs,.975)) if wrs else None)
 # Fixed 0.1 price-share bins; weighted by resolved stake.
 ece=0
 for _,g in pd.DataFrame(settled).groupby(pd.cut(pd.DataFrame(settled).fair_share,np.linspace(0,1,11)),observed=True):
  weight=g.win_stake+g.loss_stake;den=float(weight.sum())
  if den:ece+=den*abs(float(g.win_stake.sum())/den-float((g.fair_share*weight).sum())/den)
 out['stake_share_calibration_error']=ece/(w+l) if w+l else None
 ordered=sorted(settled,key=lambda b:(b['kickoff'],b['fixture_id'],b['side']))
 bytime=defaultdict(float)
 for b in ordered:bytime[b['kickoff']]+=b['profit']
 eq=np.cumsum([0]+list(bytime.values()));out['max_drawdown_units']=float(np.max(np.maximum.accumulate(eq)-eq))
 streak=longest=0
 for b in ordered:
  streak=streak+1 if b['profit']<0 else 0;longest=max(longest,streak)
 out['longest_losing_streak']=longest
 return out

def timing(h):
 for edge,name in [(1,'T-1'),(2,'T-2'),(3,'T-3'),(4,'T-4'),(6,'T-6'),(9,'T-9'),(12,'T-12'),(18,'T-18'),(24,'T-24')]:
  if h<edge:return name
 return 'T-24+'

def movement(a,b,series,market,side):
 x=bet(a,market,side);y=bet(b,market,side)
 if not x or not y:return None
 dl=y['line']-x['line'];dp=y['price']-x['price']
 if dl:cat=('LINE_UP_' if dl>0 else 'LINE_DOWN_')+('0.25' if abs(dl)==.25 else '0.50_PLUS')
 elif dp<-.01:cat='SAME_LINE_PRICE_DOWN'
 elif dp>.01:cat='SAME_LINE_PRICE_UP'
 else:cat='STABLE'
 # Reversal only within a single fixed line, never compare odds across lines.
 seq=[bet(s,market,side) for s in series];seq=[s for s in seq if s]
 steps=[v['price']-u['price'] for u,v in zip(seq,seq[1:]) if u['line']==v['line']]
 signs={int(np.sign(v)) for v in steps if abs(v)>.01}
 rev=signs=={-1,1};continuous=len(steps)>=2 and len(signs)==1 and all(s['line']==seq[0]['line'] for s in seq)
 return {**y,'category':cat,'line_change':dl,'price_change':dp,'fair_share_change':y['fair_share']-x['fair_share'],'reversal':rev,'continuous':continuous,'initial_price':x['price'],'initial_line':x['line'],'initial_fair_share':x['fair_share'],'initial_hours':a['hours']}

def main():
 # Complete versioned data inventory, hashes pin every cache/archive used or excluded.
 inventory=[]
 for name in sorted(subprocess.check_output(['git','ls-files','data'],cwd=ROOT,text=True).splitlines()):
  p=ROOT/name
  if not p.is_file():continue
  raw=p.read_bytes(); inventory.append({'path':str(p.relative_to(ROOT)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'lines':raw.count(b'\n'),'role':'INVENTORIED_NOT_INFERRED_AS_LIVE'})
 csv('data_inventory.csv',inventory)
 sources=['data/normalized/europe_pinnacle_research_v2_snapshots.jsonl','data/normalized/v2_mainline_snapshots.jsonl']
 raw=[]
 for p in sources:
  for i,r in enumerate(read(p),1):raw.append({**r,'source_file':p,'source_row':i})
 identities=defaultdict(set)
 for r in raw:
  if 'HISTORICAL' not in str(r.get('source_semantics')):identities[str(r.get('fixture_id'))].add((r.get('home'),r.get('away'),str(stamp(r.get('kickoff')))))
 badids={k for k,v in identities.items() if len(v)>1}
 results=defaultdict(list)
 for p in ['data/normalized/oddspapi_finished_results.jsonl','data/normalized/dashboard_verified_results.jsonl']:
  for r in read(p):
   if type(r.get('ft_home_goals')) is int and type(r.get('ft_away_goals')) is int and min(r['ft_home_goals'],r['ft_away_goals'])>=0:results[str(r['fixture_id'])].append(r)
 conflict={f for f,v in results.items() if len({(r['ft_home_goals'],r['ft_away_goals']) for r in v})>1}
 conflict |= {str(r['fixture_id']) for r in read('data/normalized/oddspapi_finished_results.conflicts.jsonl')}
 idx={f:v[-1] for f,v in results.items() if f not in conflict}
 exclusions=[];clean=[]; seen={}; semantics=Counter(); recovered=[]
 for r in raw:
  sem=str(r.get('source_semantics') or 'UNKNOWN');semantics[sem]+=1;f=str(r.get('fixture_id'));o=stamp(r.get('observed_at'));k=stamp(r.get('kickoff'));reason=None
  if 'HISTORICAL' in sem: recovered.append(r);reason='HISTORICAL_RECOVERY_SEPARATE'
  elif not o or not k:reason='MISSING_AWARE_TIMESTAMP'
  elif o>=k:reason='AT_OR_AFTER_KICKOFF'
  elif f in badids or not r.get('home') or not r.get('away'):reason='IDENTITY_UNRESOLVED_OR_CONFLICT'
  elif not trusted_snapshot(r):reason='QUARANTINED_SOURCE_CONTRACT'
  elif sem=='UNKNOWN':reason='UNVERIFIED_SOURCE_SEMANTICS'
  if reason:
   exclusions.append({'source_file':r['source_file'],'source_row':r['source_row'],'fixture_id':f,'reason':reason});continue
  provider=r.get('provider') or ('oddspapi' if sem.startswith('CURRENT_ODDSPAPI') else 'UNKNOWN')
  key=(f,r.get('bookmaker'),provider,o.isoformat())
  signature=json.dumps({z:r.get(z) for z in ['ah','ou','one_x_two']},sort_keys=True)
  if key in seen:
   reason='EXACT_DUPLICATE' if seen[key]==signature else 'CONFLICTING_SAME_TIME_ODDS'
   exclusions.append({'source_file':r['source_file'],'source_row':r['source_row'],'fixture_id':f,'reason':reason})
   if reason=='CONFLICTING_SAME_TIME_ODDS':
    for q in clean:
     if q['_key']==key:q['cohort']='CONFLICT'
   continue
  seen[key]=signature;sl,ontime,nominal=slot(r);res=idx.get(f,{})
  odds=r.get('one_x_two') or {};h=number(odds.get('home'));a=number(odds.get('away'));hl=number((r.get('ah') or {}).get('home_line'))
  favorite=('H' if h<=a else 'A') if h and a and min(h,a)>1 else ('A' if hl is not None and hl>0 else 'H')
  primary=sem=='CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED' and r.get('mainline_verified') is True
  flags=[]
  if f in conflict:flags.append('FT_CONFLICT')
  if not res:flags.append('MISSING_FT')
  if not in_scope(r):flags.append('OUT_OF_CURRENT_LEAGUE_SCOPE')
  if not ontime:flags.append('MANUAL_OR_DELAYED_SLOT')
  # A change timestamp is not the observation timestamp; report age, do not call unchanged quotes stale.
  changed=stamp(r.get('price_changed_at'));change_age=(o-changed).total_seconds()/60 if changed else None
  if changed and changed>o:flags.append('FUTURE_CHANGE_TIMESTAMP')
  clean.append({**r,'fixture_id':f,'_key':key,'_o':o,'_k':k,'_nominal':nominal,'provider':provider,'slot':sl,'on_time':ontime,'football_day':day(k),'observed_day':day(o),'same_day':day(k)==day(o),'hours':(k-o).total_seconds()/3600,'favorite':favorite,'cohort':'PRIMARY' if primary else 'OTHER_CURRENT','in_scope':in_scope(r),'quality_flags':flags,'price_change_age_minutes':change_age,'ft_home':res.get('ft_home_goals'),'ft_away':res.get('ft_away_goals'),'result_source':res.get('result_source')})
 clean=[r for r in clean if r['cohort']!='CONFLICT']
 serial=[{k:v for k,v in r.items() if not k.startswith('_')} for r in clean]
 (OUT/'master_observations.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,default=str)+'\n' for r in serial))
 (OUT/'historical_recovery_separate.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in recovered))
 csv('exclusions.csv',exclusions)
 primary=[r for r in clean if r['cohort']=='PRIMARY' and r['in_scope'] and 'FUTURE_CHANGE_TIMESTAMP' not in r['quality_flags']]
 # Primary schedule population Pinnacle; bet365 isolated sensitivity.
 live=[r for r in primary if str(r.get('bookmaker')).lower()=='pinnacle']
 sd=[r for r in live if r['same_day']]
 settled_master=[]
 for r in clean:
  for market,sides in [('AH',['H','A']),('OU',['O','U'])]:
   for s in sides:
    b=bet(r,market,s)
    if b:settled_master.append(b)
 csv('master_settlements.csv',settled_master)
 coverage=[]
 for dimension in ['cohort','slot','league','football_day','bookmaker','provider']:
  groups=defaultdict(list)
  for r in clean:groups[str(r[dimension])].append(r)
  for label,rs in sorted(groups.items()):coverage.append({'dimension':dimension,'label':label,'observations':len(rs),'fixtures':len({r['fixture_id'] for r in rs}),'with_ft_fixtures':len({r['fixture_id'] for r in rs if r['ft_home'] is not None}),'on_time_observations':sum(r['on_time'] for r in rs),'same_day_observations':sum(r['same_day'] for r in rs),'valid_ah':sum(bet(r,'AH') is not None for r in rs),'valid_ou':sum(bet(r,'OU') is not None for r in rs)})
 csv('coverage.csv',coverage)
 discovery={}
 for d in read('data/normalized/research_v2_daily_fixtures.jsonl'):
  if in_scope(d) and stamp(d.get('kickoff')):discovery[str(d['fixture_id'])]=d
 liveids={r['fixture_id'] for r in clean};discovery_rows=[]
 for f,d in discovery.items():
  discovery_rows.append({'fixture_id':f,'league':d.get('league'),'home':d.get('home'),'away':d.get('away'),'football_day':day(stamp(d['kickoff'])),'kickoff':d['kickoff'],'discovered_at':d.get('discovered_at'),'has_actual_current_observation':f in liveids,'has_ft_exact_id':f in idx,'status':d.get('status_name')})
 csv('discovered_fixture_coverage.csv',discovery_rows)
 dash=json.loads((ROOT/'reports/research_v2_pattern_statistics.json').read_text())
 write_json('dashboard_audit.json',{'source':'apps/dashboard/index.html and reports/research_v2_pattern_statistics.json at pinned main','report_generated_at':dash.get('generated_at'),'report_fields':{k:dash.get(k) for k in ['snapshot_rows','fixtures','settled_fixtures','ft_completeness_denominator','ft_completeness_pct','scope_excluded_snapshot_rows','quarantined_snapshot_rows']},'caution':'Dashboard includes historical and mixed providers and canonical bridge population. Not the denominator of the current-only Pinnacle experiment. Browser-rendered live deployment not independently checked.'})

 groups=defaultdict(list)
 for r in sd:groups[r['fixture_id']].append(r)
 groups={f:sorted(rs,key=lambda r:r['_o']) for f,rs in groups.items()}
 stages=defaultdict(dict)
 for f,rs in groups.items():
  stages['FIRST'][f]=rs[0];stages['LAST'][f]=rs[-1]
  for label in ['00:00','12:00','15:00','18:00','21:00']:
   eligible=[r for r in rs if r['slot']==label and r['on_time']]
   if eligible:stages[label][f]=eligible[0]
 stage_metrics=[]
 for stage,fs in stages.items():
  for market,sides in [('AH',[None,'H','A']),('OU',['O','U'])]:
   for s in sides:
    stage_metrics.append({'stage':stage,'market':market,'selection':s or 'FAVORITE',**metrics([bet(r,market,s,True) for r in fs.values()])})
 csv('stage_metrics.csv',stage_metrics)
 pairs=[]; movement_rows=[];pairs_summary=[]
 for market in ['AH','OU']:
  for left,right in [('FIRST','LAST'),('15:00','18:00'),('18:00','21:00')]:
   pp=[];same=0;changed=0;singles=0
   for f in stages[left].keys() & stages[right].keys():
    a=stages[left][f];b=stages[right][f]
    if a['_o']>=b['_o']:singles+=1;continue
    side=a['favorite'] if market=='AH' else 'O';x=bet(a,market,side);y=bet(b,market,side)
    if not x or not y:continue
    if x['line']!=y['line']:changed+=1;continue
    same+=1
    if x['profit'] is None or y['profit'] is None:continue
    p={'comparison':left+'→'+right,'market':market,'fixture_id':f,'line':x['line'],'side':side,'first_price':x['price'],'last_price':y['price'],'first_profit':x['profit'],'last_profit':y['profit'],'profit_difference':y['profit']-x['profit'],'first_observed':a['observed_at'],'last_observed':b['observed_at']};pp.append(p);pairs.append(p)
   bt=test(market+' '+left+'→'+right+' price-only',[p['profit_difference'] for p in pp],[p['fixture_id'] for p in pp])
   pairs_summary.append({'market':market,'comparison':left+'→'+right,'same_line_pairs':same,'line_changes_excluded':changed,'single_observation_excluded':singles,'settled_pairs':len(pp),'first_roi':float(np.mean([p['first_profit'] for p in pp])) if pp else None,'last_roi':float(np.mean([p['last_profit'] for p in pp])) if pp else None,**bt})
  for f,rs in groups.items():
   if len(rs)<2:continue
   side=rs[0]['favorite'] if market=='AH' else 'O';m=movement(rs[0],rs[-1],rs,market,side)
   if m:movement_rows.append(m)
 csv('price_only_pairs.csv',pairs);csv('first_last_comparisons.csv',pairs_summary);csv('movement_observations.csv',movement_rows)
 mov_summary=[]
 for market in ['AH','OU']:
  ms=[r for r in movement_rows if r['market']==market]
  baseline=metrics(ms)
  for category in sorted({r['category'] for r in ms}|{'REVERSAL','CONTINUOUS'}):
   bs=[r for r in ms if (r['reversal'] if category=='REVERSAL' else r['continuous'] if category=='CONTINUOUS' else r['category']==category)]
   mm=metrics(bs);ss=[r for r in bs if r['profit'] is not None]
   mov_summary.append({'market':market,'category':category,**mm,'roi_lift_descriptive':mm.get('roi',0)-baseline.get('roi',0) if mm.get('roi') is not None else None,'mean_goal_difference':float(np.mean([r['goal_difference'] for r in ss])) if ss else None,'mean_total_goals':float(np.mean([r['total_goals'] for r in ss])) if ss else None,'mean_probability_share_change':float(np.mean([r['fair_share_change'] for r in bs])) if bs else None})
 csv('movement_categories.csv',mov_summary)
 # Timing: one latest observation per fixture per bin; raw observation count retained.
 bins=defaultdict(list)
 for r in live:bins[timing(r['hours'])].append(r)
 timing_rows=[];chosen={}
 for label,rs in bins.items():
  per={}
  for r in sorted(rs,key=lambda r:r['_o']):per[r['fixture_id']]=r
  chosen[label]=per
  for market in ['AH','OU']:timing_rows.append({'time_bin':label,'raw_observations':len(rs),'unique_fixtures':len(per),'market':market,**metrics([bet(r,market,core=True) for r in per.values()])})
 csv('timing_metrics.csv',timing_rows)
 timing_pairs=[]
 for market in ['AH','OU']:
  early={};late={}
  for r in sorted(live,key=lambda r:r['_o']):
   if 6<=r['hours']<12:early[r['fixture_id']]=r
   if 1<=r['hours']<3:late[r['fixture_id']]=r
  deltas=[];fids=[]
  for f in early.keys()&late.keys():
   side=early[f]['favorite'] if market=='AH' else 'O';a=bet(early[f],market,side,True);b=bet(late[f],market,side,True)
   if a and b and a['profit'] is not None and b['profit'] is not None and a['line']==b['line']:deltas.append(b['profit']-a['profit']);fids.append(f)
  timing_pairs.append({'market':market,'comparison':'T1–3 minus T6–12 same fixture/selection/line/core odds',**test(market+' timing matched',deltas,fids)})
 csv('timing_matched.csv',timing_pairs)
 # Schedule simulations use observed rows only.
 schedules={}; upper={}; strict18={}
 for name,slots in [('A',{'00:00','12:00','15:00','18:00','21:00'}),('B',{'18:00'}),('C',{'15:00','18:00','21:00'})]:
  fs={};last={}
  for f,rs in groups.items():
   allowed=[r for r in rs if r['on_time'] and r['slot'] in slots and (r['slot']!='12:00' or r['_nominal'].weekday()>=5)]
   if allowed:fs[f]=allowed[0];last[f]=allowed[-1]
  schedules[name]=fs;upper[name]=last
 for f,rs in groups.items():
  eligible=[r for r in rs if r['_o']<=r['_k']-timedelta(hours=3)]
  if eligible:schedules.setdefault('D_T3',{})[f]=eligible[-1]
  deadline=datetime.fromisoformat(rs[0]['football_day']+'T18:00:00+07:00')
  available=[r for r in rs if r['_o']<=deadline<r['_k']]
  if available:strict18[f]=available[-1]
 schedules['B_EXACT18_AVAILABLE']=strict18
 schedule_rows=[];schedule_bets={}
 for mode,mapping in [('DEPLOYABLE_FIRST_ELIGIBLE',schedules),('LAST_AVAILABLE_ORACLE',upper)]:
  for name,fs in mapping.items():
   for market in ['AH','OU']:
    bs=[b for r in fs.values() if (b:=bet(r,market,core=True))];schedule_bets[mode,name,market]=bs
    schedule_rows.append({'mode':mode,'strategy':name,'market':market,'snapshot_fixtures':len(fs),'snapshot_coverage':len(fs)/len(groups) if groups else 0,'snapshot_missing':len(groups)-len(fs),**metrics(bs)})
 csv('schedule_metrics.csv',schedule_rows)
 allfixtures=set(groups);a_ids=set(schedules['A']);b_ids=set(schedules['B']);band_rows=[]
 for label in ['BEFORE18','18–21','21–00','00–03','03–06']:
  ids=[]
  for f,rs in groups.items():
   h=rs[0]['_k'].astimezone(BKK).hour;band='00–03' if h<3 else '03–06' if h<6 else 'BEFORE18' if h<18 else '18–21' if h<21 else '21–00'
   if band==label:ids.append(f)
  band_rows.append({'kickoff_band':label,'fixtures':len(ids),'A_covered':len(set(ids)&a_ids),'B_18slot_covered':len(set(ids)&b_ids),'B_missing':len(set(ids)-b_ids),'setup_and_decision':len(set(ids)&set(stages['15:00'])&b_ids),'B_exact18_prior_available':len(set(ids)&set(strict18))})
 csv('two_round_kickoff_bands.csv',band_rows)
 era_rows=[]
 for start in ['2026-10-18','2026-10-21']:
  eligible={f for f,rs in groups.items() if rs[0]['football_day']>=start}
  for name,fs in schedules.items():
   subset={f:r for f,r in fs.items() if f in eligible}
   for market in ['AH','OU']:era_rows.append({'since':start,'strategy':name,'market':market,'population':len(eligible),'covered':len(subset),'coverage':len(subset)/len(eligible) if eligible else None,**metrics([bet(r,market,core=True) for r in subset.values()])})
 csv('current_era_sensitivity.csv',era_rows)

 schedule_pairs=[]
 for market in ['AH','OU']:
  aa={r['fixture_id']:r for r in schedule_bets['DEPLOYABLE_FIRST_ELIGIBLE','A',market]};bb={r['fixture_id']:r for r in schedule_bets['DEPLOYABLE_FIRST_ELIGIBLE','B',market]};diff=[];ids=[]
  for f in aa.keys()&bb.keys():
   a,b=aa[f],bb[f]
   if a['profit'] is not None and b['profit'] is not None:diff.append(b['profit']-a['profit']);ids.append(f)
  bt=test(market+' B-A matched policy ROI',diff,ids);sdiff=float(np.std(diff,ddof=1)) if len(diff)>1 else None
  n=math.ceil(((norm.ppf(.95)+norm.ppf(.8))*sdiff/.02)**2) if sdiff is not None else None
  # For lost opportunity impact, per-union fixture use zero only for NO BET, never fabricate odds.
  uniondiff=[];unionids=[]
  for f in aa.keys()|bb.keys():
   a,b=aa.get(f),bb.get(f)
   if (a and a['profit'] is None) or (b and b['profit'] is None):continue
   uniondiff.append((b['profit'] if b else 0)-(a['profit'] if a else 0));unionids.append(f)
  union=test(market+' B-A union profit per fixture',uniondiff,unionids)
  schedule_pairs.append({'market':market,**bt,'missing_B_vs_A':len(aa.keys()-bb.keys()),'additional_future_pairs_for_80pct_power':n,'paired_sd':sdiff,'noninferiority_margin':-.02,'union_effect':union['effect'],'union_ci_low':union['ci95_low'],'union_ci_high':union['ci95_high'],'noninferiority_proven':False})
 csv('schedule_paired.csv',schedule_pairs)
 # All slot pairs coverage; selection on coverage only is exploratory and not optimization evidence.
 candidates=[]
 from itertools import combinations
 for s1,s2 in combinations(['00:00','12:00','15:00','18:00','21:00'],2):
  union=set(stages[s1])|set(stages[s2]);both=set(stages[s1])&set(stages[s2]);candidates.append({'slots':s1+' + '+s2,'union_fixture_coverage':len(union),'both_scans':len(both),'decision_second_slot_coverage':len(stages[s2])})
 csv('two_slot_coverage_candidates.csv',candidates)
 # Ledger audit: deduplicate by target plus actual receipt; missing requests remain unknown.
 led=read('data/normalized/research_v2_slot_ledger.jsonl');seenledger=set();lr=[]
 for r in led:
  key=(r.get('scheduled_target_at'),r.get('actual_observed_at'),r.get('state'),r.get('requests_used'))
  if key in seenledger:continue
  seenledger.add(key);t=stamp(r.get('scheduled_target_at'));h=t.astimezone(BKK).hour if t else None
  lr.append({'target':r.get('scheduled_target_at'),'actual':r.get('actual_observed_at'),'slot':h,'requests':number(r.get('requests_used')),'state':r.get('state'),'strategy_B_retained':h in (15,18),'strategy_C_retained':h in (15,18,21)})
 csv('ledger_requests.csv',lr)
 requests={'ledger_rows':len(lr),'known_request_rows':sum(r['requests'] is not None for r in lr),'unknown_request_rows':sum(r['requests'] is None for r in lr),'known_requests_total':sum(r['requests'] or 0 for r in lr),'known_B_retained':sum(r['requests'] or 0 for r in lr if r['strategy_B_retained']),'known_C_retained':sum(r['requests'] or 0 for r in lr if r['strategy_C_retained']),'caution':'Ledger receipts may omit other callers and account refreshes; not a verified counterfactual monthly bill. D batching cost unknown.'}
 write_json('request_audit.json',requests)
 request_periods=[]
 for period in ['day','month']:
  gs=defaultdict(list)
  for r in lr:
   ts=stamp(r['actual'] or r['target'])
   if ts:gs[ts.astimezone(BKK).strftime('%Y-%m-%d' if period=='day' else '%Y-%m')].append(r)
  for label,rr in sorted(gs.items()):request_periods.append({'period':period,'label':label,'ledger_rows':len(rr),'unknown_rows':sum(r['requests'] is None for r in rr),'known_requests':sum(r['requests'] or 0 for r in rr),'B_known_retained':sum(r['requests'] or 0 for r in rr if r['strategy_B_retained']),'C_known_retained':sum(r['requests'] or 0 for r in rr if r['strategy_C_retained'])})
 csv('request_periods.csv',request_periods)

 # Models on complete 15→18 cohort; no future variables passed to X.
 modelrows=[]
 for market in ['AH','OU']:
  for f in stages['15:00'].keys()&stages['18:00'].keys():
   a=stages['15:00'][f];b=stages['18:00'][f]
   if a['_o']>=b['_o']:continue
   side=b['favorite'] if market=='AH' else 'O';x=bet(a,market,side);y=bet(b,market,side,True)
   if not x or not y or y['profit'] is None:continue
   history=[r for r in groups[f] if r['_o']<=b['_o']];z=bet(history[0],market,side)
   if not z:continue
   modelrows.append({**y,'delta_line':y['line']-x['line'],'delta_price':y['price']-x['price'],'delta_fair':y['fair_share']-x['fair_share'],'initial_line':x['line'],'initial_price':x['price'],'initial_fair':x['fair_share'],'initial_hours':a['hours'],'all_delta_line':y['line']-z['line'],'all_delta_price':y['price']-z['price'],'history_count':len(history)})
 broad=[b for market in ['AH','OU'] for r in stages['18:00'].values() if (b:=bet(r,market,core=True)) and b['profit'] is not None]
 model_results=model_analysis(modelrows,'setup_decision',broader=broad)
 # First→last controlled association uses baseline initial line/odds and ending hours.
 association=[]
 for r in movement_rows:
  if r['profit'] is not None:
   association.append({**r,'initial_fair':r['initial_fair_share'],'delta_line':r['line_change'],'delta_price':r['price_change'],'delta_fair':r['fair_share_change'],'all_delta_line':r['line_change'],'all_delta_price':r['price_change'],'history_count':len(groups[r['fixture_id']])})
 assoc_results=model_analysis(association,'initial_controlled',initial=True)
 # Multiple comparisons corrected as ONE family, including all model contrasts actually tested.
 valid=[t for t in TESTS if t['p'] is not None];ordered=sorted(valid,key=lambda t:t['p']);prev=0
 for rank,t in enumerate(ordered):prev=max(prev,min(1.,t['p']*(len(ordered)-rank)));t['holm_p']=prev
 csv('statistical_tests.csv',TESTS)
 audit={'base_commit':BASE,'data_files_inventoried':len(inventory),'raw_current_shape_rows':len(raw),'semantics':dict(semantics),'exclusions':dict(Counter(x['reason'] for x in exclusions)),'unique_clean_current_fixtures':len({r['fixture_id'] for r in clean}),'clean_current_observations':len(clean),'primary_all_books':len(primary),'primary_pinnacle_observations':len(live),'primary_pinnacle_same_day_observations':len(sd),'primary_same_day_fixtures':len(groups),'primary_same_day_with_ft':sum(rs[0]['ft_home'] is not None for rs in groups.values()),'primary_dates':sorted({r['football_day'] for r in sd}),'primary_leagues':len({r['league'] for r in sd}),'identity_conflict_ids':sorted(badids),'result_conflict_ids':sorted(conflict),'historical_recovery_rows':len(recovered),'full_setup_decision_pairs':len(set(stages['15:00'])&set(stages['18:00'])),'strict_18_same_round_rows':sum(r['slot']=='18:00' and r['on_time'] and r['_o']<=r['_nominal'] for r in sd),'slot_fixtures':{s:len(v) for s,v in stages.items()},'api_requests_made':0,'promotion_allowed':False,'status':'EXPLORATORY / NO PROVEN EDGE','clv':'N/A — no independently verified closing observation','quote_freshness':'Current endpoint contract used; change timestamp not freshness. No per-row stale-feed receipt proof; executable freshness unproven for historical reconstruction.'}
 write_json('audit.json',audit)
 # Separate historical tick inventory: exact unique record hashes prevent sharded mirrors double count.
 histseen=set();hf=set();ticks=Counter();hfiles=[]
 for p in [ROOT/'data/normalized/oddspapi_history_ticks.jsonl',*sorted((ROOT/'data/normalized/oddspapi_history_ticks').glob('*.jsonl'))]:
  for row in read(p.relative_to(ROOT)):
   sig=hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()
   if sig in histseen:continue
   histseen.add(sig);hf.add(str(row.get('fixture_id')));k=stamp(row.get('kickoff'))
   def walk(x):
    if isinstance(x,dict):
     if 'created_at' in x and 'price' in x:
      t=stamp(x['created_at']);ticks['total']+=1
      ticks['strict_pre']+=int(bool(t and k and t<k));ticks['at_or_after']+=int(bool(t and k and t>=k));ticks['active_false']+=int(x.get('active') is False)
     else:
      for v in x.values():walk(v)
    elif isinstance(x,list):
     for v in x:walk(v)
   walk(row)
 write_json('historical_tick_audit.json',{'unique_fixture_ids':len(hf),'unique_archive_records':len(histseen),'ticks_within_deduplicated_records':dict(ticks),'caution':'Different versions of an archive fixture may overlap ticks; counts are record-level, not unique market quote events. Never pooled with actual scans.','results_joinable_exact_ids':len(hf&set(idx))})
 # Sensitivity: sources/bookmakers and excluded league populations stay separate.
 sens=[]
 for key in sorted({(r['cohort'],r['provider'],r['bookmaker'],r['in_scope']) for r in clean}):
  fs={}
  for r in sorted(clean,key=lambda r:r['_o']):
   if (r['cohort'],r['provider'],r['bookmaker'],r['in_scope'])==key and r['same_day']:fs[r['fixture_id']]=r
  for market in ['AH','OU']:sens.append({'cohort':key[0],'provider':key[1],'bookmaker':key[2],'current_scope':key[3],'market':market,**metrics([bet(r,market,core=True) for r in fs.values()])})
 csv('source_sensitivity.csv',sens)
 write_reports(audit,pairs_summary,mov_summary,timing_rows,timing_pairs,schedule_rows,schedule_pairs,band_rows,requests,model_results,assoc_results,candidates)
 for name in ['master_observations.jsonl','master_settlements.csv','historical_recovery_separate.jsonl']:
  path=OUT/name;(OUT/(name+'.gz')).write_bytes(gzip.compress(path.read_bytes(),mtime=0));path.unlink()
 write_json('environment.json',{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'seed':SEED,'bootstrap_draws':DRAWS,'base':BASE})
 print(json.dumps(audit,ensure_ascii=False,indent=2))

def model_analysis(rows,label,initial=False,broader=None):
 output=[];predictions=[]
 for market in ['AH','OU']:
  data=pd.DataFrame([r for r in rows if r['market']==market])
  if data.empty:output.append({'market':market,'status':'INSUFFICIENT_NO_ROWS'});continue
  days=sorted(data.football_day.unique());i=int(len(days)*.6);j=int(len(days)*.8)
  tr=data[data.football_day.isin(days[:i])];va=data[data.football_day.isin(days[i:j])];te=data[data.football_day.isin(days[j:])]
  sizes={'train':len(tr),'validation':len(va),'retrospective_test':len(te),'train_dates':days[:i],'validation_dates':days[i:j],'test_dates':days[j:],'leagues':int(data.league.nunique())}
  if min(len(tr),len(va),len(te))<5:
   output.append({'market':market,'status':'INSUFFICIENT_SPLIT',**sizes});continue
  base=['initial_line','initial_price','initial_fair','initial_hours','hours'] if initial else ['line','price','fair_share','hours']
  feature_sets={'A':base,'B':base+['delta_line','delta_price','delta_fair'],'C':base+['delta_line','delta_price','delta_fair','all_delta_line','all_delta_price','history_count']}
  preds={}
  for model,cols in feature_sets.items():
   options=[]
   for alpha in [1.,10.,100.]:
    pre=ColumnTransformer([('numeric',StandardScaler(),cols),('league',OneHotEncoder(handle_unknown='ignore',sparse_output=False),['league_context'])])
    pipe=make_pipeline(pre,Ridge(alpha=alpha));pipe.fit(tr,tr.profit)
    options.append((float(np.mean((pipe.predict(va)-va.profit)**2)),alpha,pipe))
   _,alpha,pipe=min(options,key=lambda v:v[0]);pred=pipe.predict(te);preds[model]=pred
   selected=[{k:v for k,v in r.items()} for r,p in zip(te.to_dict('records'),pred) if p>0]
   output.append({'market':market,'model':model,'status':'EXPLORATORY_SUFFICIENT_MINIMUM' if len(tr)>=150 and len(va)>=80 and len(te)>=40 and sizes['leagues']>=3 else 'INSUFFICIENT_FROZEN_MINIMUM','alpha':alpha,**sizes,'test_mse':float(np.mean((pred-te.profit)**2)),'selected_metrics':metrics(selected)})
   if model=='A' and broader:
    broad=pd.DataFrame([x for x in broader if x['market']==market and x['football_day'] in days[j:]])
    if not broad.empty:
     bp=pipe.predict(broad);selected_broad=[x for x,p in zip(broad.to_dict('records'),bp) if p>0]
     output.append({'market':market,'model':'A_BROADER','status':'EXPLORATORY_DIFFERENT_POPULATION','alpha':alpha,**sizes,'retrospective_test':len(broad),'test_mse':float(np.mean((bp-broad.profit)**2)),'selected_metrics':metrics(selected_broad)})
   for r,p in zip(te.to_dict('records'),pred):predictions.append({'market':market,'model':model,'fixture_id':r['fixture_id'],'day':r['football_day'],'observed_at':r['observed_at'],'profit':r['profit'],'predicted_return':float(p),'selected':bool(p>0)})
  for model in ['B','C']:
   # Positive is improved predictive loss, not ROI.
   diff=(preds['A']-te.profit.to_numpy())**2-(preds[model]-te.profit.to_numpy())**2
   bt=test(label+' '+market+' A-'+model+' MSE',diff,te.fixture_id.tolist());output.append({'market':market,'contrast':'A minus '+model+' test MSE',**bt})
 csv(label+'_predictions.csv',predictions);write_json(label+'_models.json',output);return output

def table(rows,cols):
 def fmt(v):
  if v is None:return 'N/A'
  if isinstance(v,float):return f'{v:.4f}'
  return str(v)
 return '| '+' | '.join(cols)+' |\n| '+' | '.join(['---']*len(cols))+' |\n'+'\n'.join('| '+' | '.join(fmt(r.get(c)) for c in cols)+' |' for r in rows)+'\n'

def write_reports(a,p,m,t,tp,s,sp,b,req,models,assoc,candidates):
 common='\n\nEXPLORATORY — NO PROVEN EDGE. ROI is units per unit staked (0.01 = 1%). CLV N/A; latest observed price is not a certified close. See [protocol](PROTOCOL.md), [input inventory](data_inventory.csv), [statistical tests with Holm adjustment](statistical_tests.csv). No frozen promotion gate changed.\n'
 coverage=f"""# Report 1 — Scan coverage audit

Pinned main `{BASE}`. Actual-current-shaped input rows: {a['raw_current_shape_rows']}; historical recovery: {a['historical_recovery_rows']}, kept separately. Clean current rows: {a['clean_current_observations']}. Primary in-scope Pinnacle actual pre-match rows: {a['primary_pinnacle_observations']}; same football day: {a['primary_pinnacle_same_day_observations']} across {a['primary_same_day_fixtures']} fixtures and {len(a['primary_dates'])} days, {a['primary_leagues']} league labels. Exact FT available: {a['primary_same_day_with_ft']}. Date range: {min(a['primary_dates'])}–{max(a['primary_dates'])}.

## Exclusions and denominator

"""+table([{'reason':k,'rows':v} for k,v in a['exclusions'].items()],['reason','rows'])+"""
All raw records are preserved. [coverage.csv](coverage.csv) breaks down fixture, slot, league, date, source and bookmaker. [exclusions.csv](exclusions.csv) has source row pointers. Master observations retain 1X2, both AH/OU sides, change time if present, actual observation time, flags and exact result source; master settlements expand the four sides using actual quarter-line settlement. Current league exclusions are flagged; not deleted. Retired/missing FT fixtures remain in coverage, not silently removed from denominators. Missing FT can bias settled ROI.

Raw receipts, provider caches, CSV archives and normalized mirrors are inventoried with SHA256. They are not independently added as new observations: parsing the same cache as a second observation would duplicate evidence. The versioned normalized scan files are the declared actual-scan population, not a claim that every past Actions artifact was retained. Unretained/deleted artifacts and pre-normalization missing scans cannot be recovered without new evidence. discovered_fixture_coverage.csv additionally enumerates the in-scope discovery universe with exact-ID current observation and FT flags. Discovery can occur after kickoff, so it is an audit denominator, not an ex-ante opportunity set. dashboard_audit.json reconciles dashboard source-population semantics; browser-rendered deployment was not re-certified. The daily-fixture discovery universe includes out-of-scope and unpriced fixtures; primary schedule coverage denominator is the union of observed in-scope fixtures, not all worldwide fixtures.

Historical tick audit is separate in historical_tick_audit.json; reconstructed AH slots are retained separately. FiveDollar opening/latest snapshots lack intra-day observation times and are unsuitable for schedule comparison. Current source sensitivity is in source_sensitivity.csv. No cross-provider names are fuzzy joined. Exact ID FT is inherited from existing verified result cache; external result provenance has not been independently re-certified. Conflicting identity/FT is quarantined. Repeated identical prices at distinct scan times remain valid observations; identical row/observation is deduplicated.

Current endpoint observations inherit the current active-market contract; this is evidence of polling time, not independent proof of execution availability. A quote unchanged for hours is not automatically stale. Missing source-change time/freshness receipt is a limitation, and no execution-ready EV is asserted. Post-kickoff or exactly-at-kickoff observations are excluded. Slots must meet nominal 15-minute completion SLA; actual times, not labels, determine availability.
"""
 (OUT/'01_scan_coverage_audit.md').write_text(coverage+common)
 (OUT/'02_first_vs_last_scan.md').write_text('# Report 2 — First vs last scan\n\n'+table(p,['market','comparison','settled_pairs','line_changes_excluded','first_roi','last_roi','effect','ci95_low','ci95_high','p'])+"\nPrice-only: first side held fixed, exact same line/book/provider, strictly later observation required. Includes actual valid prices outside core range to isolate pricing, unlike core-range independent benchmarks. Effect = later minus earlier unit return. First/last are within fixture Thai football day. A single observation is not evidence of multi-scan benefit.\n\n[stage_metrics.csv](stage_metrics.csv) reports independent AH-favorite, fixed H/A, O/U selections, all settlement counts, WR, ROI, confidence intervals, odds and normalized price share. These simple controls have no validated predictive selection rule. Last pre-match selection is a retrospective endpoint; it is not necessarily actionable because one cannot know ex ante which later scan will fail.\n\nWR counts resolved stake: (FW+0.5HW)/(FW+0.5HW+FL+0.5HL). Push stakes excluded from WR, included in ROI stake denominator; half wins are not full wins. Bootstrap resamples fixtures, not snapshots.\n"+common)
 modeltable=table([{'market':r['market'],'model':r['model'],'train':r['train'],'validation':r['validation'],'test':r['retrospective_test'],'MSE':r['test_mse'],**r['selected_metrics']} for r in models if 'model' in r],['market','model','train','validation','test','MSE','bets','wr','roi','roi_ci95_low','roi_ci95_high'])
 (OUT/'03_odds_movement_impact.md').write_text('# Report 3 — Odds movement impact\n\n'+table(m,['market','category','fixtures','wr','roi','roi_ci95_low','roi_ci95_high','roi_lift_descriptive','mean_goal_difference','mean_total_goals'])+'\nCategory ROI lift is a descriptive difference against all movement fixtures, not a controlled causal effect. Fixed first favorite side for AH; Over for OU. Signed handicap is from that selected side. Reversal requires both directions of >0.01 price changes on the same line; continuous movement requires >=3 observations on one line. These diagnostics overlap categories and are not independent tests.\n\n'+modeltable+'\nA=18 alone; B=18 plus 15→18 movement; C=18 plus all available earlier same-day observations. Same complete-case test population for all three.\n\ninitial_controlled_models.json provides chronological ridge comparisons conditioning on INITIAL price/line/share, league, kickoff distance, then movement. setup_decision_models.json conditions on current 18:00 market. Both are retrospective tests, not untouched holdouts. MSE improvements are predictive return loss, not FT winner accuracy; FT goal difference/total associations are in the table. Model ROI and EV thresholds are exploratory, not validated betting decisions.\n'+common)
 (OUT/'04_optimal_pre_kickoff_timing.md').write_text('# Report 4 — Pre-kickoff timing\n\n'+table(t,['time_bin','market','raw_observations','unique_fixtures','bets','wr','roi','roi_ci95_low','roi_ci95_high','stake_share_calibration_error'])+'\nBins are [lower,upper), e.g. exactly 1h belongs to T-2. Latest observed row per fixture/bin, no fabricated boundary price. Bet counts may be lower than unique fixtures due to missing markets, core range and FT. Each fixture may occur in several bins; inference below is paired, not independent observations.\n\n'+table(tp,['market','clusters','effect','ci95_low','ci95_high','p'])+'\nMatched 1–3h vs 6–12h controls exact fixture, league, selected side, bookmaker, provider, exact line and both prices within 1.80–2.20. Unmatched bin differences remain confounded by league/time/day; they must not be used to name an optimal window. Calibration is won-stake share vs two-sided de-vig price share, not full-win probability. No window declared optimal without forward confirmation. D uses preregistered T-3, not the best historical bin.\n'+common)
 (OUT/'05_scan_schedule_comparison.md').write_text('# Report 5 — Scan schedules\n\n'+table(s,['mode','strategy','market','snapshot_fixtures','opportunities','bets','wr','roi','profit_units','max_drawdown_units','longest_losing_streak'])+'\nA=00/15/18/21 plus weekend 12; B=15 setup, 18 decision only; C=15/18/21; D_T3=latest available at kickoff−3h (no future backfill). DEPLOYABLE_FIRST_ELIGIBLE uses first observed eligible round; LAST_AVAILABLE_ORACLE is clearly an ex-post availability upper bound, not a deployable betting policy. Both use the same descriptive side rule. Strict B_EXACT18_AVAILABLE can use earlier observations but never calls them an 18:00 quote. Operational B waits for the actual 18:00 poll, at most 18:15 and strictly pre-kickoff.\n\n'+table(b,['kickoff_band','fixtures','A_covered','B_18slot_covered','B_missing','setup_and_decision','B_exact18_prior_available'])+'\n03–06 includes 05–06 on its own football day; 03–05 belongs to previous football day. Matches before 18:00 cannot be betting decisions at 18:00. Missing 18 slot stays missing. Setup coverage and decision coverage are separate.\n\n'+table(sp,['market','clusters','effect','ci95_low','ci95_high','missing_B_vs_A','union_effect','additional_future_pairs_for_80pct_power'])+'\nMatched policy effect compares B vs A on common settled fixtures; differs from pure price comparison because policy may choose another side/line. Union effect assigns zero profit to no bet (no synthetic price), quantifying opportunity loss. No noninferiority claim: proposed margin −0.02 unit/bet requires prospective validation and <=5pp coverage loss.\n\nLedger: '+json.dumps(req,ensure_ascii=False)+'\n\nTheoretical rounds/week: A=30, B=14, C=21. Equal cost per round would save B 53.3%, C 30%; NOT a measured bill reduction. Monthly calls depend on batch size, repeats and changing fixture universe; extrapolating incomplete ledger is unreliable. D requires a batching design before request cost can be estimated. See current_era_sensitivity.csv for post-18-Oct and post-21-Oct cohorts; historical missing slots are not assumed to be current schedule failures. request_periods.csv shows known requests by Bangkok day/month, with unknowns retained. Closed registry has zero validated bets, so benchmark opportunities are not proven profitable missed bets.\n'+common)
 
 final=f"""# Report 6 — Final recommendation

**NO PROVEN EDGE. Keep production schedule unchanged; evaluate 15:00→18:00 in shadow mode.**

1. Multi-scan selection quality: not established. Multiple scans create price/movement evidence, but retrospective pricing gains are not incremental forecasting skill.
2. Movement predictive value: inspect setup_decision_models.json and initial_controlled_models.json, with corrected tests in statistical_tests.csv. Small split sizes or unconfirmed test improvements cannot pass frozen gates. No causation claimed.
3. First vs last: exact matched effects and CI in Report 2; line changes excluded from price-only comparison. WR alone cannot show better prices.
4. Best pre-kickoff hour: not established; matched result in Report 4. Unmatched high-ROI bins cannot justify schedule changes.
5. Reducing to 15/18: loses later coverage, late price information and all pre-18 final decisions. Actual primary pair coverage: {a['full_setup_decision_pairs']} fixture pairs versus {a['primary_same_day_fixtures']} union fixtures. See kickoff bands and missed core-range opportunities, not just snapshot counts.
6. Setup→decision sufficient for real betting: not proven. Existing frozen registry has zero approved patterns. Neither retrospective positive ROI nor model predicted return authorizes betting selection.
7. Two, three or many: retain current scans while running offline shadow. Benefit: retains evidence and a paired counterfactual. Cost: current API usage continues. Risk: provider/scope drift and missing FT can invalidate forward comparisons. Three rounds may preserve more coverage than two, but there is no established betting-performance superiority.
8. If forced to two: 15/18 is an operational candidate, not statistically best. Coverage-only alternatives are in two_slot_coverage_candidates.csv; later scans may fit night matches but lose early opportunities. Do not select a winner from these data and call its evidence confirmatory.

## Forward validation plan

Freeze the current protocol, feature sets and trained rule version before new outcomes. Retain all production rounds; evaluate B at ACTUAL decision time, no fallback from 21/00. Log eligible fixture universe, unavailable markets, active status, observed time, immutable provider IDs, actual requests and complete 90-minute FT. Paired ROI CI and coverage loss are co-primary. Require B−A lower one-sided 95% CI >−2pp, coverage loss <=5pp, missed validated opportunities <=5%, savings >=25%, in addition to all existing gates. A non-significant difference does not prove noninferiority.

Fresh prospective sample required (all historical rows have been inspected):

"""+table(sp,['market','paired_sd','additional_future_pairs_for_80pct_power'])+"""
These are paired return-difference variance-based planning estimates, not independent snapshot counts. Use max(AH,OU,150+80+40) future settled matched fixtures, >=60 football days, >=8 weeks and >=3 leagues. Increase for within-day clustering, serial dependence, multiple co-primary claims and attrition; reassess sample size without inspecting effect direction. ROI-difference planning is not power for nonlinear movement models; they need a separate simulation/power assessment before promotion. Freeze a future holdout before collection and reserve it until the analysis decision date. If current production approved patterns remain empty, validated real-bet performance comparison is unavailable, regardless of benchmark sample.

## Reproduction and evidence boundaries

Run `python research/multi_scan_20261101/run.py` from the pinned repository with research requirements. It writes only this research directory and performs zero network calls. Input inventory pins every versioned data/cache file. Master observations and settlements are derived, never replacements for production data. Six reports, detailed CSVs, model predictions and tests allow every reported calculation to be traced back to a source file and row. Future executions on newer data are a new exploratory analysis unless holdout restrictions are enforced separately.

Historical tick files are audited but not pooled into live-schedule inference. Existing normalized scan history is used; an audit of every unretained Actions artifact or independent verification of every cached result is outside available evidence. Genuine CLV and execution freshness remain unavailable; report N/A, never substitute the last scan and call it closing.
"""
 final+='\n## Numerical decision evidence\n\n'+table(p,['market','comparison','settled_pairs','effect','ci95_low','ci95_high'])
 final+='\n'+table([x for x in s if x['mode']=='DEPLOYABLE_FIRST_ELIGIBLE' and x['strategy'] in ['A','B','C','D_T3']],['strategy','market','snapshot_fixtures','bets','wr','roi','roi_ci95_low','roi_ci95_high'])
 final+='\nThe current-era sensitivity is crucial: since 2026-10-21, compare A/B/C on the same observed fixture union in current_era_sensitivity.csv. Missing historical schedules must not be mistaken for present-system reliability. Model test dates are only three football days (29–31 October), including incomplete FT at extraction; selected-bet samples are very small. Positive or negative selected ROI is not reliable proof. This dataset cannot establish global or multi-season stability.\n'
 (OUT/'06_final_recommendation.md').write_text(final+common)
 (OUT/'README.md').write_text('# Multi-scan value research — 2026-11-01\n\nResearch only; production unchanged. **EXPLORATORY / NO PROVEN EDGE.**\n\n'+ '\n'.join(f'- [{p.stem}](%s)'%p.name for p in sorted(OUT.glob('0*.md')))+'\n\n[Protocol](PROTOCOL.md) · [Audit JSON](audit.json) · [Reproduce](run.py) · [Tests](check_research.py)\n')

if __name__=='__main__':main()
