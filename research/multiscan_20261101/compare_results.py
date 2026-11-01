"""Require exact deterministic core data and numerically stable ML outputs."""
import json,math,sys,gzip
from pathlib import Path
left,right=map(Path,sys.argv[1:])
def equal(a,b):
    if isinstance(a,dict):return isinstance(b,dict) and a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
    if isinstance(a,list):return isinstance(b,list) and len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    if isinstance(a,float):return isinstance(b,(int,float)) and math.isclose(a,b,rel_tol=1e-7,abs_tol=1e-9)
    return a==b
for p in sorted(left.glob('*.json')):
    assert equal(json.loads(p.read_text()),json.loads((right/p.name).read_text())),p.name
for name in ['master_research_dataset.csv','paired_returns.csv','strategy_bets.csv','exclusions.csv','daily_slot_coverage.csv']:
    def data(root):
        p=root/name
        return p.read_bytes() if p.exists() else gzip.decompress(p.with_suffix(p.suffix+'.gz').read_bytes())
    assert data(left)==data(right),name
print('Core CSV exact and all JSON numerically reproducible')
