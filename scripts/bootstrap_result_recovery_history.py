"""Reconstruct attempts from versioned successful source reports; run from repository root.

No request is sent. Historical canonical results and snapshots establish eligibility.
Legacy direct-fetch report commit times are report-recording times, not invented
provider timestamps. Cached evidence is deduplicated by recorded retrieval proof.
"""
import json,subprocess
from pathlib import Path
from odds_scanner.result_recovery_lifecycle import record,rows,RESULTS,review
root=Path('.')
known={r['fixture_id'] for r in rows(root/RESULTS)}
for provider in ('fotmob','espn'):
 path=f'reports/{provider}_result_backfill.json'
 commits=subprocess.check_output(['git','log','-14','--format=%H','--',path],text=True).splitlines()
 for sha in reversed(commits):
  report=json.loads(subprocess.check_output(['git','show',sha+':'+path]))
  old_snaps=[json.loads(x) for x in subprocess.check_output(['git','show',sha+':data/normalized/europe_pinnacle_research_v2_snapshots.jsonl'],text=True).splitlines() if x.strip()]
  old_results=[json.loads(x) for x in subprocess.check_output(['git','show',sha+':data/normalized/oddspapi_finished_results.jsonl'],text=True).splitlines() if x.strip()]
  code=subprocess.check_output(['git','show',sha+':src/odds_scanner/'+provider+'_result_backfill.py'],text=True)
  direct=provider=='fotmob' and 'fetch_day' not in code
  stamp=subprocess.check_output(['git','show','-s','--format=%cI',sha],text=True).strip()
  record(root,provider,report,[s for s in old_snaps if s['fixture_id'] not in known],old_results,sha,stamp,direct)
r=review(root);print({k:v for k,v in r.items() if k!='pending'})
print('ledger_bytes',(root/'data/normalized/result_recovery_attempts.json').stat().st_size)
