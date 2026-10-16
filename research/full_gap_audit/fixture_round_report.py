"""Read-only fixture-by-round report from the pinned expected/actual matrix.

Run locally with a checked-out research branch. No network or production writes.
"""
import argparse
import csv
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

def records(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8') as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)

def summarize(rows):
    fixtures=defaultdict(list)
    for r in rows:
        fixtures[(r['fixture_id'],r['football_day'])].append(r)
    output=[]
    for (fid,day),slots in sorted(fixtures.items()):
        slots.sort(key=lambda x:x['slot_utc'])
        known=[s for s in slots if s.get('expected') is True]
        counts=Counter(s['status'] for s in known)
        output.append({
            'fixture_id':fid,'football_day':day,
            'home':next((s.get('home') for s in slots if s.get('home')), ''),
            'away':next((s.get('away') for s in slots if s.get('away')), ''),
            'league':next((s.get('league') for s in slots if s.get('league')), ''),
            'expected_proven':len(known),
            'complete':counts['COMPLETE'],
            'scan_failed':counts['SCAN_FAILED'],
            'no_price':counts['NO_PRICE'],
            'unmatched':counts['UNMATCHED'],
            'expected_unknown_ah':counts['UNKNOWN_EVIDENCE'],
            'unknown_membership':sum(s.get('expected') is None for s in slots),
            'observed_slots':';'.join(s['slot_bangkok'] for s in slots if s['status']=='COMPLETE'),
            'candidate_deficit_slots':';'.join(s['slot_bangkok'] for s in known if s['status'] in ('SCAN_FAILED','NO_PRICE')),
            'needs_evidence_slots':';'.join(s['slot_bangkok'] for s in slots if s.get('expected') is None or (s.get('expected') is True and s['status'] in ('UNMATCHED','UNKNOWN_EVIDENCE')))
        })
    return output

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--matrix',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    root=Path(__file__).resolve().parent
    if not a.output.resolve().is_relative_to(root):
        raise SystemExit('RESEARCH_OUTPUT_ONLY')
    data=summarize(records(a.matrix))
    fields=list(data[0]) if data else []
    a.output.parent.mkdir(parents=True,exist_ok=True)
    if a.output.exists():raise SystemExit('OUTPUT_ALREADY_EXISTS')
    with a.output.open('x',newline='',encoding='utf-8') as fh:
        writer=csv.DictWriter(fh,fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)
    print(json.dumps({'fixture_days':len(data),'rows_written':len(data),'output':str(a.output),'historical_api_calls':0}))
if __name__=='__main__':main()
