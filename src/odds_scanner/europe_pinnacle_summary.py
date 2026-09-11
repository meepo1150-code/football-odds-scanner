from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOT_PATH = Path('data/normalized/europe_pinnacle_discovery_snapshots.jsonl')
TARGET_PATH = Path('reports/europe_discovery_tournaments.json')
REPORT_PATH = Path('reports/europe_pinnacle_discovery_summary.json')


def _json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _jsonl(path: Path) -> list[dict]:
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except FileNotFoundError:
        return []
    out=[]
    for line in lines:
        if not line.strip(): continue
        try: row=json.loads(line)
        except json.JSONDecodeError: continue
        if isinstance(row,dict): out.append(row)
    return out


def summarize(rows: list[dict], targets: list[dict] | None = None) -> dict:
    targets=targets or []
    expected={(str(x.get('country') or ''),str(x.get('tournament_name') or '')) for x in targets if isinstance(x,dict)}
    by=defaultdict(lambda:{'observations':0,'fixtures':set()})
    days=set(); fixtures=set()
    for row in rows:
        key=(str(row.get('country') or ''),str(row.get('league') or 'UNKNOWN'))
        fid=str(row.get('fixture_id') or ''); observed=str(row.get('observed_at') or '')
        if observed: days.add(observed[:10])
        if fid: fixtures.add(fid); by[key]['fixtures'].add(fid)
        by[key]['observations']+=1
    leagues=[]
    for country,league in sorted(expected|set(by)):
        x=by[(country,league)]
        leagues.append({'country':country,'league':league,'observations':x['observations'],'unique_fixtures':len(x['fixtures']),'coverage_status':'OBSERVED' if x['observations'] else 'NO_STRICT_OBSERVATION_YET'})
    return {
        'schema_version':'1.0','generated_at':datetime.now(timezone.utc).isoformat(),
        'classification':'EUROPE_PINNACLE_DISCOVERY_ONLY','bookmaker':'pinnacle',
        'production_promotion_allowed':False,'validation_gate_effect':'NONE','candidate_matching_allowed':False,
        'observation_days':len(days),'strict_observations':len(rows),'unique_fixtures':len(fixtures),
        'target_leagues':len(expected),'leagues_with_strict_observations':sum(1 for x in leagues if x['observations']>0),
        'league_coverage':leagues,
        'interpretation':'Descriptive Pinnacle accumulation only. This stream is separate from Bet365 candidate price bands and frozen Validation v2.'
    }


def run(root: Path=Path('.')) -> dict:
    target=_json(root/TARGET_PATH) or {}; targets=target.get('tournaments',[]) if isinstance(target,dict) else []
    report=summarize(_jsonl(root/SNAPSHOT_PATH),targets)
    path=root/REPORT_PATH; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__': print(json.dumps(run(),ensure_ascii=False))
