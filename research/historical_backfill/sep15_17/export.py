"""Offline three-day reports. No provider access."""
import collections,csv,json
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from research.historical_backfill.isolated_runner import load_cache
from research.historical_backfill.normalizer import normalize
from research.historical_backfill.comparison import reconstruct_candidate
from research.historical_backfill.reconstruct import parse_time
from research.historical_backfill import storage
BASE=Path('research/historical_backfill/sep15_17')
BKK=ZoneInfo('Asia/Bangkok')
def day_of_slot(slot):
 t=parse_time(slot).astimezone(BKK)
 return (t-timedelta(days=1) if t.hour==0 else t).date().isoformat()
def export():
 m=json.loads((BASE/'manifest.json').read_text())
 reports=[json.loads(p.read_text()) for p in sorted((BASE/'results').glob('batch-*/report.json'))]
 results={ (i['fixture_id'],i['bookmaker']):i for r in reports for i in r['results'] }
 catalog=json.loads(Path('research/historical_backfill/reports/reviewed_catalog.json').read_text())
 summary=dict(date_range=m['date_range'],source_commit=m['source_main_commit'],
  run_url='https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38866711140',
  batches=[{k:v for k,v in r.items() if k not in ('results','requests')} for r in reports],
  actual_historical_requests=sum(r['historical_requests'] for r in reports),
  actual_account_requests=sum(r['account_requests'] for r in reports),
  cache_hits=sum(r['cache_hits'] for r in reports),
  planned_fixture_bookmaker_pairs=len(m['candidates']),unique_fixtures=len({c['fixture_id'] for c in m['candidates']}),
  evaluated_fixture_bookmaker_pairs=len(results),days={},fixture_slots=[],comparisons=[])
 latest=[];all_lines=[];fresh_count=0
 for c in m['candidates']:
  item=results.get((c['fixture_id'],c['bookmaker']))
  if not item:continue
  summary['comparisons'].append(dict(fixture_id=c['fixture_id'],bookmaker=c['bookmaker'],comparisons=item['comparisons']))
  for slot in item['slots']:
   selected=slot.get('selected');q=(selected or {}).get('quotes',{})
   row=dict(day=day_of_slot(slot['slot_utc']),fixture_id=c['fixture_id'],bookmaker=c['bookmaker'],home=c['home'],away=c['away'],kickoff=c['kickoff'],
    target_utc=slot['slot_utc'],target_bangkok=parse_time(slot['slot_utc']).astimezone(BKK).isoformat(),status=slot['status'],
    home_line=(selected or {}).get('line'),away_line=-(selected or {})['line'] if selected else None,
    home_price=q.get('home',{}).get('price'),away_price=q.get('away',{}).get('price'),
    home_history_entry_at=q.get('home',{}).get('quote_at_utc'),away_history_entry_at=q.get('away',{}).get('quote_at_utc'),
    rejection_counts=slot.get('rejection_counts',{}),historical_ah_available=item['historical_ah_available'])
   summary['fixture_slots'].append(row)
  if not c['missing_rounds']:continue
  payload=load_cache(storage.ROOT,c)
  if payload is None:continue
  markets=normalize(payload,c,catalog,active_semantics_verified=True)
  lines=reconstruct_candidate(c,markets,state_semantics_verified=True,max_age_seconds=10**9)
  for r in lines:
   q=r.get('quotes',{})
   all_lines.append(dict(day=day_of_slot(r['slot_utc']),fixture_id=c['fixture_id'],bookmaker=c['bookmaker'],target_utc=r['slot_utc'],
    market_id=r.get('market_id'),home_line=r.get('line'),status=r['status'],home_price=q.get('home',{}).get('price'),away_price=q.get('away',{}).get('price'),
    home_history_entry_at=q.get('home',{}).get('quote_at_utc'),away_history_entry_at=q.get('away',{}).get('quote_at_utc'),
    raw_record_hash=r.get('raw_record_hash'),age_filter_applied=False))
  for target in c['missing_rounds']:
   rows=[r for r in lines if r['slot_utc']==target];complete=[r for r in rows if r['status']=='COMPLETE']
   balanced=[r for r in complete if all(1.8<=r['quotes'][s]['price']<=2.2 for s in ('home','away'))]
   chosen=min(balanced,key=lambda r:((r['quotes']['home']['price']-2)**2+(r['quotes']['away']['price']-2)**2,abs(r['quotes']['home']['price']-r['quotes']['away']['price']),r['line'])) if balanced else None
   qs=(chosen or {}).get('quotes',{})
   ages={s:(parse_time(target)-parse_time(q['quote_at_utc'])).total_seconds() for s,q in qs.items()}
   latest.append(dict(day=day_of_slot(target),fixture_id=c['fixture_id'],bookmaker=c['bookmaker'],home=c['home'],away=c['away'],target_utc=target,
    complete_recorded_pairs=len(complete),balanced_recorded_pairs=len(balanced),home_line=(chosen or {}).get('line'),
    home_price=qs.get('home',{}).get('price'),away_price=qs.get('away',{}).get('price'),
    home_history_entry_at=qs.get('home',{}).get('quote_at_utc'),away_history_entry_at=qs.get('away',{}).get('quote_at_utc'),
    age_seconds=ages,older_than_1h=any(v>3600 for v in ages.values()),continuous_availability_at_target_verified=False))
 for day in ('2026-09-15','2026-09-16','2026-09-17'):
  rows=[r for r in summary['fixture_slots'] if r['day']==day]
  ls=[r for r in latest if r['day']==day]
  summary['days'][day]=dict(unique_fixtures=len({r['fixture_id'] for r in rows}),fixture_bookmaker_pairs=len({(r['fixture_id'],r['bookmaker']) for r in rows}),
   slot_status_counts=dict(collections.Counter(r['status'] for r in rows)),any_recorded_pair_slots=sum(r['complete_recorded_pairs']>0 for r in ls),
   balanced_last_recorded_slots=sum(r['balanced_recorded_pairs']>0 for r in ls),balanced_older_than_1h_slots=sum(r['older_than_1h'] for r in ls),
   by_target={target:dict(collections.Counter(r['status'] for r in rows if r['target_utc']==target)) for target in sorted({r['target_utc'] for r in rows})})
 (BASE/'RESULT.json').write_text(json.dumps(summary,indent=2)+'\n')
 (BASE/'LAST_REPORTED.json').write_text(json.dumps(dict(semantics='Provider-createdAt at or before target. No age filter. Not official mainline or proof of continuous availability.',rows=latest),indent=2)+'\n')
 with (BASE/'ALL_REPORTED_LINES.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(all_lines[0]));w.writeheader();w.writerows(all_lines)
 with (BASE/'RESULT.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=[k for k in summary['fixture_slots'][0] if k!='rejection_counts'],extrasaction='ignore');w.writeheader();w.writerows(summary['fixture_slots'])
 md=['# September 15–17 historical odds experiment','',summary['run_url'],'',
  'Research only. Timestamped original OddsPapi observations define date membership; some fixtures have a different kickoff date. Same fixture/bookmaker is fetched once and reused across dates. Targets at or after kickoff are NOT_PREMATCH_SLOT; candidates with no pre-kickoff target are not requested.','',
  'Historical calls: '+str(summary['actual_historical_requests'])+'; account calls: '+str(summary['actual_account_requests'])+'; cache hits: '+str(summary['cache_hits'])+'.','',
  'BALANCED_LINE requires active pairs, both decimal prices 1.80–2.20, each history-entry age <=3600 seconds. It does not mean official mainline. LAST_REPORTED.json and ALL_REPORTED_LINES.csv preserve older entries separately without a freshness claim. createdAt is the provider history-entry timestamp, not guaranteed bookmaker change time.','',
  '| Day | Unique fixtures | Fixture × bookmaker | Any recorded pair before target | Fresh balanced slots | Unresolved | At/after kickoff |',
  '|---|---:|---:|---:|---:|---:|---:|']
 for day,d in summary['days'].items():
  s=d['slot_status_counts']
  md.append('| '+day+' | '+str(d['unique_fixtures'])+' | '+str(d['fixture_bookmaker_pairs'])+' | '+str(d['any_recorded_pair_slots'])+' | '+str(s.get('BALANCED_LINE',0))+' | '+str(s.get('MAINLINE_UNRESOLVED',0))+' | '+str(s.get('NOT_PREMATCH_SLOT',0))+' |')
 md.extend(['','## Prices and original timestamps (Bangkok)','',
  '| Day | Fixture / bookmaker | Target | Home AH | Home / away odds | Home / away history-entry time | Status |',
  '|---|---|---|---|---|---|---|'])
 fmt=lambda x:parse_time(x).astimezone(BKK).isoformat() if x else '—'
 for r in summary['fixture_slots']:
  md.append('| '+r['day']+' | '+r['home']+' – '+r['away']+' / '+r['bookmaker']+' | '+r['target_bangkok']+' | '+str(r['home_line'])+' | '+str(r['home_price'])+' / '+str(r['away_price'])+' | '+fmt(r['home_history_entry_at'])+' / '+fmt(r['away_history_entry_at'])+' | '+r['status']+' |')
 (BASE/'RESULT.md').write_text('\n'.join(md)+'\n')
 print(json.dumps({k:v for k,v in summary.items() if k not in ('fixture_slots','comparisons','batches')},indent=2))
 return summary
if __name__=='__main__':export()
