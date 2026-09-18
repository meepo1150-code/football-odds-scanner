from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

SNAP=Path('data/normalized/europe_pinnacle_research_v2_snapshots.jsonl')
OUT=Path('data/normalized/research_v2_movement_features.jsonl')
REPORT=Path('reports/research_v2_movement_status.json')

def _rows(path):
    out=[]
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            try:r=json.loads(line)
            except json.JSONDecodeError:continue
            if isinstance(r,dict):out.append(r)
    return out

def _num(x):
    try:return float(x)
    except (TypeError,ValueError):return None

def _get(row,key):
    # Research V2 snapshots store market values in nested canonical objects.
    if key=='ah_line': return (row.get('ah') or {}).get('selected_side_line')
    if key=='favorite_price': return (row.get('ah') or {}).get('selected_side_price')
    if key=='ou_line': return (row.get('ou') or {}).get('line')
    if key=='over_price': return (row.get('ou') or {}).get('over_price')
    if key=='under_price': return (row.get('ou') or {}).get('under_price')
    if key=='home_price': return (row.get('one_x_two') or {}).get('home')
    if key=='draw_price': return (row.get('one_x_two') or {}).get('draw')
    if key=='away_price': return (row.get('one_x_two') or {}).get('away')
    return row.get(key)

def run(root=Path('.')):
    groups=defaultdict(list)
    source=_rows(root/SNAP)
    for r in source: groups[str(r.get('fixture_id'))].append(r)
    features=[]
    numeric_delta_count=0
    for fid,rs in groups.items():
        rs.sort(key=lambda x:str(x.get('observed_at') or ''))
        if len(rs)<2:continue
        a,b=rs[0],rs[-1]
        row={'fixture_id':fid,'football_day':b.get('football_day'),'league':b.get('league'),'country':b.get('country'),'competition_type':b.get('competition_type'),'observations':len(rs),'first_observed_at':a.get('observed_at'),'last_observed_at':b.get('observed_at')}
        for key in ('ah_line','favorite_price','ou_line','over_price','under_price','home_price','draw_price','away_price'):
            av,bv=_num(_get(a,key)),_num(_get(b,key))
            row['first_'+key]=av; row['last_'+key]=bv
            row['delta_'+key]=None if av is None or bv is None else round(bv-av,4)
            if row['delta_'+key] is not None:numeric_delta_count+=1
        features.append(row)
    features.sort(key=lambda x:(str(x.get('football_day')),x['fixture_id']))
    p=root/OUT;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(''.join(json.dumps(x,separators=(',',':'))+'\n' for x in features),encoding='utf-8')
    report={'schema_version':'1.1','status':'MOVEMENT_BUILT','fixtures_with_two_plus_snapshots':len(features),'source_snapshot_rows':len(source),'numeric_delta_fields_built':numeric_delta_count}
    q=root/REPORT;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(report,indent=2),encoding='utf-8');return report

if __name__=='__main__':print(json.dumps(run()))
