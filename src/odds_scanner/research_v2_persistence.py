"""Preserve concurrent raw observations, then rebuild derived artifacts.

Never restore a full stale checkout over the latest main branch. Raw JSONL is
an exact-record union: divergent evidence is retained for downstream quarantine.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

APPEND_PATHS = (
    'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl',
    'data/normalized/europe_pinnacle_research_v2_audit.jsonl',
    'data/normalized/research_v2_slot_ledger.jsonl',
)


def merge_jsonl(target: Path, incoming: Path) -> int:
    records = {}
    for path in (target, incoming):
        if not path.exists():
            continue
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f'Non-object forensic record in {path}')
                key = json.dumps(row, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
                records[key] = row
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True)+'\n' for row in records.values()), encoding='utf-8')
    return len(records)


def merge_staged(root: Path, staged: Path) -> None:
    for relative in APPEND_PATHS:
        if (staged / relative).exists():
            merge_jsonl(root / relative, staged / relative)
    # Provider reports are latest-observation state, not append-only evidence.
    for incoming in (staged / 'reports').glob('*.json'):
        if incoming.name not in {
            'pinnwire_research_v2_status.json', 'propline_research_v2_status.json',
            'europe_pinnacle_research_v2_status.json',
        }:
            continue
        target = root / 'reports' / incoming.name
        new = json.loads(incoming.read_text())
        old = json.loads(target.read_text()) if target.exists() else {}
        if str(new.get('generated_at', '')) >= str(old.get('generated_at', '')):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(new, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('staged', type=Path)
    args = parser.parse_args()
    merge_staged(Path('.'), args.staged)
