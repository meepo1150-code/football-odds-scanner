from __future__ import annotations

import json
from pathlib import Path

from .oddspapi_result_cache import RESULTS_PATH
from .v2_forward_performance import settle_entry

SNAPSHOTS_PATH = Path('data/normalized/europe_discovery_snapshots.jsonl')
ENTRIES_PATH = Path('data/normalized/europe_discovery_entries.jsonl')
SETTLEMENTS_PATH = Path('data/normalized/europe_discovery_settlements.jsonl')
REPORT_PATH = Path('reports/europe_discovery_evidence.json')


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists(): return []
    out=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        try: row=json.loads(line)
        except json.JSONDecodeError: continue
        if isinstance(row,dict): out.append(row)
    return out


def entry_from_snapshot(s: dict, candidate_id: str) -> dict:
    if candidate_id.startswith('FD_OU'):
        market='OU'; selection='U'; line=(s.get('ou') or {}).get('line'); price=(s.get('ou') or {}).get('under_price')
    else:
        market='AH'; selection=s.get('favorite_side'); line=(s.get('ah') or {}).get('selected_side_line'); price=(s.get('ah') or {}).get('selected_side_price')
    row={
        'candidate_id':candidate_id,'fixture_id':s.get('fixture_id'),'league':s.get('league'),'country':s.get('country'),
        'home':s.get('home'),'away':s.get('away'),'kickoff':s.get('kickoff'),'entry_observed_at':s.get('observed_at'),
        'market':market,'selection':selection,'entry_line':line,'entry_price':price,'stake_units':1.0,
        'favorite_fair_probability':s.get('favorite_fair_probability'),'discovery_only':True,'production_eligible':False,
    }
    if isinstance(s.get('external_providers'),dict) and s['external_providers']:
        row['external_providers']=dict(s['external_providers'])
        row['external_provider_mapping_source']=s.get('external_provider_mapping_source') or 'ODDSPAPI_CURRENT_EXTERNALPROVIDERS_EXACT_IDS'
    return row


def build(root: Path=Path('.')) -> dict:
    snapshots=sorted(load_jsonl(root/SNAPSHOTS_PATH),key=lambda r:(str(r.get('observed_at') or ''),str(r.get('fixture_id') or '')))
    existing=load_jsonl(root/ENTRIES_PATH)
    by_key={(str(r.get('candidate_id') or ''),str(r.get('fixture_id') or '')):r for r in existing if r.get('candidate_id') and r.get('fixture_id')}
    added=0
    for s in snapshots:
        for cid in s.get('candidate_like_matches') or []:
            key=(str(cid),str(s.get('fixture_id') or ''))
            if not key[1] or key in by_key: continue
            by_key[key]=entry_from_snapshot(s,str(cid)); added+=1
    entries=sorted(by_key.values(),key=lambda r:(str(r.get('entry_observed_at') or ''),str(r.get('candidate_id') or ''),str(r.get('fixture_id') or '')))
    p=root/ENTRIES_PATH; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in entries),encoding='utf-8')

    result_index={str(r.get('fixture_id')):r for r in load_jsonl(root/RESULTS_PATH) if r.get('fixture_id') is not None}
    settled=[]
    for e in entries:
        result=result_index.get(str(e.get('fixture_id') or ''))
        if not result: continue
        try:
            row=settle_entry(e,result); row['discovery_only']=True; row['production_eligible']=False; settled.append(row)
        except ValueError: continue
    sp=root/SETTLEMENTS_PATH; sp.parent.mkdir(parents=True,exist_ok=True); sp.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in settled),encoding='utf-8')
    net=sum(float(r.get('profit_units') or 0) for r in settled)
    report={'schema_version':'1.0','classification':'EUROPE_DISCOVERY_EVIDENCE_ONLY','snapshots_seen':len(snapshots),'entries_total':len(entries),'entries_added':added,'entries_with_exact_external_ids':sum(1 for r in entries if isinstance(r.get('external_providers'),dict) and r['external_providers']),'settled_entries':len(settled),'net_units':net,'production_promotion_allowed':False,'validation_gate_effect':'NONE'}
    rp=root/REPORT_PATH; rp.parent.mkdir(parents=True,exist_ok=True); rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); return report

if __name__=='__main__': print(json.dumps(build(),ensure_ascii=False))
