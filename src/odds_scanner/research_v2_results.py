from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .oddspapi_provider import ENV_KEY, _get
from .oddspapi_result_cache import merge_results

AUDIT_PATH = Path('data/normalized/europe_pinnacle_research_v2_audit.jsonl')
RESULTS_PATH = Path('data/normalized/oddspapi_finished_results.jsonl')
REPORT_PATH = Path('reports/research_v2_result_backfill_status.json')


def _load_jsonl(path: Path) -> list[dict]:
    rows=[]
    if not path.exists(): return rows
    for line in path.read_text(encoding='utf-8').splitlines():
        try: row=json.loads(line)
        except json.JSONDecodeError: continue
        if isinstance(row,dict): rows.append(row)
    return rows


def run(root: Path=Path('.')) -> dict:
    now=datetime.now(timezone.utc)
    report={'schema_version':'1.0','generated_at':now.isoformat(),'classification':'RESEARCH_V2_RESULT_BACKFILL','join_policy':'EXACT_FIXTURE_ID_ONLY'}
    key=os.getenv(ENV_KEY,'').strip()
    if not key:
        report['status']='API_KEY_NOT_CONFIGURED'
    else:
        audit=_load_jsonl(root/AUDIT_PATH)
        wanted={str(r.get('fixture_id')) for r in audit if r.get('fixture_id')}
        existing={str(r.get('fixture_id')) for r in _load_jsonl(root/RESULTS_PATH) if r.get('fixture_id')}
        missing=wanted-existing
        # One soccer query covers the recent research window; exact fixture IDs gate the merge.
        start=(now-timedelta(days=3)).isoformat().replace('+00:00','Z')
        end=now.isoformat().replace('+00:00','Z')
        payload=_get('/fixtures',key,{'sportId':10,'from':start,'to':end,'statusId':2,'language':'en'},45)
        fixtures=payload if isinstance(payload,list) else payload.get('fixtures',[]) if isinstance(payload,dict) else []
        exact=[x for x in fixtures if str(x.get('fixtureId')) in missing]
        added=merge_results(root/RESULTS_PATH,exact)
        report.update(status='BACKFILL_COMPLETE',requests_used=1,research_fixture_ids=len(wanted),missing_before=len(missing),finished_exact_matches=len(exact),results_added=added)
    path=root/REPORT_PATH; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


if __name__=='__main__': print(json.dumps(run(),ensure_ascii=False))
