from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

MOVEMENT_PATH=Path('reports/europe_pinnacle_discovery_movement.json')
REPORT_PATH=Path('reports/europe_pinnacle_discovery_movement_research.json')


def summarize(doc:dict|None)->dict:
    rows=(doc or {}).get('movement_rows') or []
    by=defaultdict(lambda:{'fixtures':0,'ah':Counter(),'ou':Counter(),'favorite_changes':0})
    ah=Counter(); ou=Counter(); favorite_changes=0
    for r in rows:
        league=f"{r.get('country') or ''} · {r.get('league') or '—'}"
        ab=str((r.get('ah') or {}).get('line_bucket') or 'UNKNOWN'); ob=str((r.get('ou') or {}).get('line_bucket') or 'UNKNOWN')
        ah[ab]+=1; ou[ob]+=1; x=by[league]; x['fixtures']+=1; x['ah'][ab]+=1; x['ou'][ob]+=1
        if r.get('favorite_side_changed'): favorite_changes+=1; x['favorite_changes']+=1
    return {'schema_version':'1.0','generated_at':datetime.now(timezone.utc).isoformat(),'classification':'EUROPE_PINNACLE_DISCOVERY_ONLY','bookmaker':'pinnacle','production_promotion_allowed':False,'validation_gate_effect':'NONE','outcomes_joined':False,'roi_calculated':False,'repeated_fixtures':len(rows),'favorite_side_changes':favorite_changes,'ah_line_buckets':dict(sorted(ah.items())),'ou_line_buckets':dict(sorted(ou.items())),'league_patterns':[{'league':k,'repeated_fixtures':x['fixtures'],'favorite_side_changes':x['favorite_changes'],'ah_line_buckets':dict(sorted(x['ah'].items())),'ou_line_buckets':dict(sorted(x['ou'].items()))} for k,x in sorted(by.items())],'interpretation':'Descriptive frequency research only. No outcomes, win rate, ROI, CLV, profitability, edge, or promotion inference is permitted.'}


def run(root:Path=Path('.'))->dict:
    try: doc=json.loads((root/MOVEMENT_PATH).read_text(encoding='utf-8'))
    except (FileNotFoundError,json.JSONDecodeError): doc={}
    report=summarize(doc); p=root/REPORT_PATH; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); return report

if __name__=='__main__': print(json.dumps(run(),ensure_ascii=False))
