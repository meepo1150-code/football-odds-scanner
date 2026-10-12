"""Rebuild one coherent offline evidence bundle without transport or raw writes."""
import json
from pathlib import Path
from .research_v2_movement import run as movement
from .research_v2_pattern_stats import build as statistics
from .research_v2_operational_audit import build as operational
from .research_v2_end_to_end_audit import build as end_to_end
from .dashboard_scope import build as scope
from .oddspapi_history_audit import write_audit as history


def build(root=Path('.')):
    movement(root)
    stats=statistics(root)
    op=operational(root)
    if not op['data_assertions_passed']:
        raise ValueError('Inconsistent offline evidence: '+str(op['assertion_failures']))
    e2e=end_to_end(root)
    scope(root)
    history(root)
    if e2e['settled_fixtures']!=stats['settled_fixtures']:
        raise ValueError('Settled population differs between reports')
    return {'status':op['status'],'settled_identity_groups':stats['settled_fixtures'],
            'raw_deleted':0,'network_requests':0,'promotion_allowed':False}


if __name__=='__main__':print(json.dumps(build()))
