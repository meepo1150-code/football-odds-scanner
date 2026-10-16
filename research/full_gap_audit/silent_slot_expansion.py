"""Conservative, deterministic silent-slot expansion from pinned evidence.

No API calls or production writes. Input: immutable matrix exported by audit.py.
Never promotes unknown membership without same-day deployed cohort evidence.
"""
import argparse
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

def read_rows(path):
    op = gzip.open if str(path).endswith('.gz') else open
    with op(path, 'rt', encoding='utf-8') as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)

def expand(rows):
    data=list(rows)
    by_day=defaultdict(list)
    for r in data:
        by_day[(r['fixture_id'],r['football_day'])].append(r)
    expanded=[];counts=Counter()
    for r in data:
        if r.get('expected') is not None or r.get('status')!='UNKNOWN_EVIDENCE':
            continue
        if r.get('policy_version')!='FIXED_1500':
            counts['unsupported_policy']+=1
            continue
        siblings=by_day[(r['fixture_id'],r['football_day'])]
        cohort=[s for s in siblings if s.get('membership')=='EXACT_ATTEMPT_OR_DEPLOYED_COHORT' and s.get('expected') is True]
        # A sibling's direct attempt alone is not sufficient to prove fixed cohort.
        # A true day-level cohort must be explicitly identified in a separate trusted source.
        counts['needs_explicit_cohort_proof']+=1
    return {'newly_proven_expected':0,'newly_proven_missing':0,
            'reviewed_unknown':sum(counts.values()),'reasons':dict(counts),
            'classification':'EVIDENCE_REQUIRED_NOT_MISSING'}, expanded

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--matrix',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    inp=Path(a.matrix);out=Path(a.output)
    if not out.resolve().is_relative_to(Path(__file__).resolve().parent):
        raise SystemExit('RESEARCH_OUTPUT_ONLY')
    raw=inp.read_bytes();summary,rows=expand(read_rows(inp))
    summary['input_sha256']=hashlib.sha256(raw).hexdigest()
    summary['input_path']=str(inp)
    summary['note']='No new missing slots proven without immutable cohort membership evidence'
    payload=json.dumps(summary,sort_keys=True,indent=2)+'\n'
    if out.exists():
        if out.read_text()!=payload:raise SystemExit('IMMUTABLE_CONFLICT')
    else:
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(payload)
    print(payload)
if __name__=='__main__':main()
