"""A backend-generated policy receipt consumed by the dashboard; raw stays intact."""
import json
from datetime import datetime, timezone
from pathlib import Path
from .research_population import exclusion_reason, POLICY
from .research_v2_integrity import trusted_snapshot
from .research_v2_pattern_stats import _rows, SNAPSHOTS


def build(root=Path('.')):
    raw=_rows(root/SNAPSHOTS)
    reasons={str(r['fixture_id']):exclusion_reason(r) for r in raw if r.get('fixture_id') and exclusion_reason(r)}
    invalid={(str(r.get('fixture_id')),str(r.get('observed_at'))) for r in raw if not trusted_snapshot(r)}
    payload={'generated_at':datetime.now(timezone.utc).isoformat(),'policy':POLICY,
             'excluded_fixture_reasons':reasons,'untrusted_observations':[list(x) for x in sorted(invalid)],
             'raw_rows':len(raw),'raw_deleted':0}
    p=root/'reports/dashboard_scope.json';p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    return payload

if __name__=='__main__':print(json.dumps(build()))
