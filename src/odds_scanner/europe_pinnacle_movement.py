from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOT_PATH=Path('data/normalized/europe_pinnacle_discovery_snapshots.jsonl')
REPORT_PATH=Path('reports/europe_pinnacle_discovery_movement.json')


def _load(path: Path)->list[dict]:
    try: lines=path.read_text(encoding='utf-8').splitlines()
    except FileNotFoundError: return []
    out=[]
    for line in lines:
        if not line.strip(): continue
        try:r=json.loads(line)
        except json.JSONDecodeError: continue
        if isinstance(r,dict): out.append(r)
    return out


def _num(v):
    try:return float(v)
    except (TypeError,ValueError):return None


def _bucket(delta):
    if delta is None:return None
    q=round(delta*4)/4
    if abs(q-delta)>1e-9:return 'NON_QUARTER_DELTA'
    if abs(q)<1e-9:return 'FLAT'
    if abs(q)>=.5:return 'UP_.50_PLUS' if q>0 else 'DOWN_.50_PLUS'
    return 'UP_.25' if q>0 else 'DOWN_.25'


def summarize(rows:list[dict])->dict:
    grouped=defaultdict(list)
    for r in rows:
        if r.get('fixture_id') is not None and r.get('observed_at'): grouped[str(r['fixture_id'])].append(r)
    movement=[]
    for fid,rs in grouped.items():
        rs.sort(key=lambda r:str(r.get('observed_at') or ''))
        if len(rs)<2: continue
        first,last=rs[0],rs[-1]; fa=first.get('ah') or {}; la=last.get('ah') or {}; fo=first.get('ou') or {}; lo=last.get('ou') or {}
        fal,lal=_num(fa.get('selected_side_line')),_num(la.get('selected_side_line')); fol,lol=_num(fo.get('line')),_num(lo.get('line'))
        fap,lap=_num(fa.get('selected_side_price')),_num(la.get('selected_side_price')); fop,lop=_num(fo.get('over_price')),_num(lo.get('over_price')); fup,lup=_num(fo.get('under_price')),_num(lo.get('under_price'))
        ad=None if fal is None or lal is None else round(lal-fal,4); od=None if fol is None or lol is None else round(lol-fol,4)
        movement.append({'fixture_id':fid,'country':last.get('country') or first.get('country'),'league':last.get('league') or first.get('league'),'home':last.get('home') or first.get('home'),'away':last.get('away') or first.get('away'),'kickoff':last.get('kickoff') or first.get('kickoff'),'observations':len(rs),'first_observed_at':first.get('observed_at'),'latest_observed_at':last.get('observed_at'),'favorite_side_first':first.get('favorite_side'),'favorite_side_latest':last.get('favorite_side'),'favorite_side_changed':first.get('favorite_side')!=last.get('favorite_side'),'ah':{'first_observed_line':fal,'latest_observed_line':lal,'line_delta':ad,'line_bucket':_bucket(ad),'first_observed_price':fap,'latest_observed_price':lap,'price_delta':None if fap is None or lap is None else round(lap-fap,4)},'ou':{'first_observed_line':fol,'latest_observed_line':lol,'line_delta':od,'line_bucket':_bucket(od),'first_observed_over_price':fop,'latest_observed_over_price':lop,'over_price_delta':None if fop is None or lop is None else round(lop-fop,4),'first_observed_under_price':fup,'latest_observed_under_price':lup,'under_price_delta':None if fup is None or lup is None else round(lup-fup,4)}})
    movement.sort(key=lambda x:(str(x.get('latest_observed_at') or ''),str(x.get('fixture_id'))),reverse=True)
    return {'schema_version':'1.0','generated_at':datetime.now(timezone.utc).isoformat(),'classification':'EUROPE_PINNACLE_DISCOVERY_ONLY','bookmaker':'pinnacle','production_promotion_allowed':False,'validation_gate_effect':'NONE','source_semantics':'FIRST_OBSERVED_VS_LATEST_OBSERVED_STRICT_PINNACLE_DISCOVERY','fixtures_seen':len(grouped),'fixtures_with_repeated_observations':len(movement),'movement_rows':movement,'interpretation':'Descriptive movement only. First observed is not guaranteed bookmaker opening price; latest observed is not guaranteed closing price. This is not CLV, ROI, edge, or promotion evidence.'}


def run(root:Path=Path('.'))->dict:
    report=summarize(_load(root/SNAPSHOT_PATH)); p=root/REPORT_PATH; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); return report

if __name__=='__main__': print(json.dumps(run(),ensure_ascii=False))
