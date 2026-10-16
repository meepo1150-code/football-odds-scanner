"""Check the actual Pages gate against PR, fork and failed-run events."""
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def workflow(name):
    return yaml.safe_load((ROOT / '.github/workflows' / name).read_text())


@pytest.mark.parametrize('event,ref,conclusion,branch,source_event,repo,expected', [
    ('push', 'refs/heads/main', 'success', 'main', 'push', 'owner/repo', True),
    ('push', 'refs/heads/feature', 'success', 'main', 'push', 'owner/repo', False),
    ('workflow_dispatch', 'refs/heads/main', 'success', 'main', 'push', 'owner/repo', True),
    ('workflow_dispatch', 'refs/heads/feature', 'success', 'main', 'push', 'owner/repo', False),
    ('workflow_run', '', 'success', 'main', 'schedule', 'owner/repo', True),
    ('workflow_run', '', 'success', 'main', 'workflow_dispatch', 'owner/repo', True),
    ('workflow_run', '', 'failure', 'main', 'push', 'owner/repo', False),
    ('workflow_run', '', 'cancelled', 'main', 'push', 'owner/repo', False),
    ('workflow_run', '', 'success', 'feature', 'push', 'owner/repo', False),
    ('workflow_run', '', 'success', 'main', 'pull_request', 'owner/repo', False),
    ('workflow_run', '', 'success', 'main', 'pull_request_target', 'owner/repo', False),
    ('workflow_run', '', 'success', 'main', 'push', 'fork/repo', False),
    ('pull_request', 'refs/pull/123/merge', 'success', 'main', 'push', 'owner/repo', False),
])
def test_pages_gate(event, ref, conclusion, branch, source_event, repo, expected):
    gate = workflow('pages.yml')['jobs']['deploy']['if']
    run = SimpleNamespace(name='Research V2 Offline Evidence Audit', conclusion=conclusion, head_branch=branch, event=source_event,
                          head_repository=SimpleNamespace(full_name=repo))
    github = SimpleNamespace(event_name=event, ref=ref, repository='owner/repo',
                             event=SimpleNamespace(workflow_run=run))
    assert eval(gate.replace('&&', ' and ').replace('||', ' or '),
                {'__builtins__': {}}, {'github': github}) is expected


def test_pr_checks_do_not_wake_pages_or_persist():
    pr = workflow('offline-pr-validation.yml')
    events = pr.get('on', pr.get(True))  # PyYAML's YAML 1.1 boolean spelling
    assert set(events) == {'pull_request'}
    assert pr['permissions'] == {'contents': 'read'}
    assert pr['name'] not in workflow('pages.yml').get('on', workflow('pages.yml').get(True))['workflow_run']['workflows']
    steps = pr['jobs']['tests']['steps']
    assert steps[0]['with']['persist-credentials'] is False
    assert any('python -m pytest -q' in s.get('run', '') for s in steps)
    assert not any('git push' in s.get('run', '') for s in steps)
    old = workflow('research-v2-offline-evidence.yml')
    assert 'pull_request' not in old.get('on', old.get(True))
    persist = next(s for s in old['jobs']['audit']['steps'] if s.get('name', '').startswith('Persist'))
    assert "github.ref == 'refs/heads/main'" in persist['if']
