"""Offline, exact-time report export; never calls a provider."""
import collections,csv,json
from pathlib import Path
from zoneinfo import ZoneInfo
from research.historical_backfill.reconstruct import parse_time
BASE=Path('research/historical_backfill/sep14')
def export(report):
 bkk=ZoneInfo('Asia/Bangkok')
 records=[]
 for item in report.get('results',[]):
  for slot in item['slots']:
   pick=slot.get('selected') or {};qs=pick.get('quotes',{})
   rejection=slot.get('rejection_counts',{})
   records.append(dict(fixture_id=item['fixture_id'],home=item['home'],away=item['away'],bookmaker=item['bookmaker'],
    target_bangkok=parse_time(slot['slot_utc']).astimezone(bkk).isoformat(),status=slot['status'],
    home_line=pick.get('home_line'),away_line=pick.get('away_line'),
    home_price=qs.get('home',{}).get('price'),away_price=qs.get('away',{}).get('price'),
    home_history_entry_at=qs.get('home',{}).get('quote_at_utc'),away_history_entry_at=qs.get('away',{}).get('quote_at_utc'),
    rejection_counts=rejection,comparison=item.get('comparisons',[])))
 result={k:v for k,v in report.items() if k not in ('results','requests')}
 result['requests']=report.get('requests',[])
 result['fixture_slots']=records
 (BASE/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
 fields=[k for k in records[0] if k not in ('comparison','rejection_counts')] if records else ['fixture_id','status']
 with (BASE/'RESULT.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(records)
 lines=['# September 14 historical recovery — research only','',
  'Run: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38860129483','',
  'Status: '+report['status'], '',
  'Historical requests: '+str(report['historical_requests'])+'; account requests: '+str(report['account_requests'])+'; cache hits: '+str(report['cache_hits'])+'.','',
  'The 20 Pinnacle matchday fixtures were observed at 21:52:05 Bangkok; the additional Bet365 Marseille–PSG fixture was collected on Sep14 for a Sep20 kickoff. IDs are taken directly from original OddsPapi snapshots.','',
  'Historical timestamps below are provider history-entry createdAt, not guaranteed bookmaker change times. Only active, pre-kickoff pairs with both prices 1.80–2.20 and age <=3600 seconds can be BALANCED_LINE. Older records do not mean no history exists. No official mainline is inferred.','',
  '| Fixture / bookmaker | Target Bangkok | Status | Home AH | Home / away price | Home / away history-entry time (Bangkok) |',
  '|---|---|---|---|---|---|']
 for r in records:
  fmt=lambda t:parse_time(t).astimezone(bkk).isoformat() if t else '—'
  lines.append('| '+r['home']+' – '+r['away']+' / '+r['bookmaker']+' | '+r['target_bangkok']+' | '+r['status']+' | '+str(r['home_line'])+' | '+str(r['home_price'])+' / '+str(r['away_price'])+' | '+fmt(r['home_history_entry_at'])+' / '+fmt(r['away_history_entry_at'])+' |')
 lines.extend(['','## Coverage by target',''])
 for target,rs in __import__('itertools').groupby(sorted(records,key=lambda r:r['target_bangkok']),key=lambda r:r['target_bangkok']):
  lines.append(target+': '+str(dict(collections.Counter(r['status'] for r in rs))))
 lines.extend(['','## Limits','',
  'NOT_PREMATCH_SLOT means target >= kickoff; excluded to prevent in-play contamination. MAINLINE_UNRESOLVED means the conservative representative selection failed; raw all-line reasons are preserved in the Actions artifact.',
  'All-line reconstruction and same-bookmaker/same-line original-snapshot comparisons are in the full report artifact. Production collector, scheduler, quota ledger and dashboard were not edited.'])
 (BASE/'RESULT.md').write_text('\n'.join(lines)+'\n')
 return result
if __name__=='__main__':
 r=json.loads((BASE/'results/report.json').read_text());export(r)
