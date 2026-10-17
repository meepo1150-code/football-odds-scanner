"""Persist a conservative run grant BEFORE billable transport in Actions.

CAS fast-forward commits change only the grant ledger. No checkout/reset, no
raw quote rewrite, and no transport if quota or durable persistence fails.
"""
import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from datetime import datetime, timezone
from .automatic_scan_budget import allocation
from .research_request_budget import RESERVATIONS


class ResearchQuotaBlocked(RuntimeError):
    pass


def _git(root, *args, input=None, env=None, check=True):
    return subprocess.run(['git', *args], cwd=root, input=input, text=True,
                          capture_output=True, check=check, env=env, timeout=45)


def _refresh(root):
    from .research_v2_persistence import merge_jsonl
    _git(root, 'fetch', 'origin', 'main')
    base = _git(root, 'rev-parse', 'origin/main').stdout.strip()
    for path in (RESERVATIONS, Path('data/normalized/research_v2_slot_ledger.jsonl')):
        exists = _git(root, 'cat-file', '-e', f'{base}:{path}', check=False)
        if exists.returncode:
            continue
        contents = _git(root, 'show', f'{base}:{path}').stdout
        with tempfile.TemporaryDirectory() as folder:
            incoming = Path(folder)/'ledger'
            incoming.write_text(contents)
            merge_jsonl(root/path, incoming)
    return base


def _publish(root, base):
    with tempfile.TemporaryDirectory() as folder:
        env = {**os.environ, 'GIT_INDEX_FILE': str(Path(folder)/'index'),
               'GIT_AUTHOR_NAME': 'github-actions[bot]',
               'GIT_COMMITTER_NAME': 'github-actions[bot]',
               'GIT_AUTHOR_EMAIL': '41898282+github-actions[bot]@users.noreply.github.com',
               'GIT_COMMITTER_EMAIL': '41898282+github-actions[bot]@users.noreply.github.com'}
        blob = _git(root, 'hash-object', '-w', str(RESERVATIONS)).stdout.strip()
        _git(root, 'read-tree', base, env=env)
        _git(root, 'update-index', '--add', '--cacheinfo', f'100644,{blob},{RESERVATIONS}', env=env)
        tree = _git(root, 'write-tree', env=env).stdout.strip()
        commit = _git(root, 'commit-tree', tree, '-p', base, env=env,
                      input='data: reserve UTC research quota before transport [skip ci]\n').stdout.strip()
        return _git(root, 'push', 'origin', f'{commit}:refs/heads/main', check=False).returncode == 0


def reserve(root, ids, now, *, overhead=0, manual=False, max_requests=None):
    durable = os.getenv('RESEARCH_QUOTA_DURABLE') == 'true'
    from .automatic_scan import slot_at
    target = slot_at(now)['target_at']
    target = datetime.fromisoformat(target).astimezone(timezone.utc).isoformat()
    reservation_id = uuid.uuid4().hex
    path = root/RESERVATIONS
    for attempt in range(3):
        try:
            base = _refresh(root) if durable else None
            # Exclude our unpublished candidate on CAS retry only. Remote receipts
            # are never removed; a failed push cannot have authorized transport.
            existing = path.read_text().splitlines() if path.exists() else []
            filtered = [line for line in existing if json.loads(line).get('reservation_id') != reservation_id]
            if len(filtered) != len(existing):
                path.write_text(''.join(line+'\n' for line in filtered))
            # A grant without a finalized receipt may already have reached the
            # provider before runner cancellation. Do not pay for it again.
            if target:
                receipts = root/'data/normalized/research_v2_slot_ledger.jsonl'
                finalized = {r.get('budget_reservation_id') for r in
                             (json.loads(l) for l in receipts.read_text().splitlines() if l.strip())} if receipts.exists() else set()
                for line in filtered:
                    prior = json.loads(line)
                    if prior.get('scheduled_target_at') == target and prior.get('reservation_id') not in finalized:
                        raise ResearchQuotaBlocked('Canonical grant outcome unconfirmed; duplicate transport blocked')
            chosen, budget = allocation(root/'data/normalized/research_v2_slot_ledger.jsonl',
                                        ids, now, prioritized=True, overhead=overhead, manual=manual)
            if not chosen:
                raise ResearchQuotaBlocked('UTC research capacity reserved or exhausted')
            count = overhead + (len(chosen)+4)//5
            if max_requests is not None:
                if type(max_requests) is not int or max_requests <= overhead:
                    raise ResearchQuotaBlocked('Insufficient capacity for discovery and odds')
                count = min(count, max_requests)
            budget['research_run_limit'] = count
            receipt = {'reservation_id': reservation_id, 'provider': 'oddspapi',
                       'finalized_at': now.astimezone(timezone.utc).isoformat(),
                       'requests_used': count, 'state': 'RESERVED_BEFORE_TRANSPORT',
                       'github_run_id': os.getenv('GITHUB_RUN_ID'),
                       'scheduled_target_at': target, 'manual_supplementary_scan': manual}
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('a') as handle:
                handle.write(json.dumps(receipt, sort_keys=True)+'\n')
            if not durable or _publish(root, base):
                return chosen, budget, reservation_id, count
        except ResearchQuotaBlocked:
            raise
        except (OSError, ValueError, subprocess.SubprocessError):
            raise ResearchQuotaBlocked('Quota checkpoint unavailable; no billable transport authorized') from None
    raise ResearchQuotaBlocked('Quota checkpoint contention; no billable transport authorized')
