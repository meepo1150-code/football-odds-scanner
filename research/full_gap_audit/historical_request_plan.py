"""Simple offline historical request plan from verified missing-slot manifest.

One row per fixture and target time; no network, no API key, no production writes.
The request runner must resolve the provider's historical endpoint separately.
"""
import argparse,json
from pathlib import Path

def plan(rows):
    seen=set();out=[]
    for r in rows:
        if r.get('expected') is not True or r.get('status') not in ('SCAN_FAILED','NO_PRICE','MISSING_SLOT') or r.get('recovery_eligible') is not True:
            continue
        key=(r.get('provider_fixture_id'),r.get('slot_utc'))
        if not all(key) or key in seen:continue
        seen.add(key)
        out.append({
            'fixture_id':key[0],
            'requested_asof_utc':key[1],
            'kickoff_utc':r['kickoff_utc'],
            'market':'FULL_MATCH_AH',
            'bookmaker':'pinnacle',
            'source_slot_key':r['deduplication_key'],
            'mode':'HISTORICAL_READ_ONLY',
            'status':'AWAITING_PROVIDER_REQUEST_VALIDATION'
        })
    return sorted(out,key=lambda x:(x['requested_asof_utc'],x['fixture_id']))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    root=Path(__file__).resolve().parent
    if not a.output.resolve().is_relative_to(root):raise SystemExit('RESEARCH_OUTPUT_ONLY')
    rows=[json.loads(x) for x in a.manifest.read_text().splitlines() if x.strip()]
    requests=plan(rows)
    if a.output.exists():raise SystemExit('OUTPUT_ALREADY_EXISTS')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in requests))
    print(json.dumps({'request_plan_rows':len(requests),'unique_requests':len(requests),'api_calls':0,'output':str(a.output)}))
if __name__=='__main__':main()
