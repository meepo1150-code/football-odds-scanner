"""Append evidence onto latest main without rewriting existing raw bytes."""
import json
from pathlib import Path
from .research_v2_persistence import APPEND_PATHS
from .automatic_scan_manifest import MANIFESTS, cohort, rows
from .automatic_scan import LEDGER, REPORT

PATHS = (*APPEND_PATHS, str(MANIFESTS), str(LEDGER))


def append_union(target, incoming):
    # Canonical identity prevents duplicate serialization variants; existing bytes
    # stay intact, including divergent source records with the same fixture/time.
    key = lambda r: json.dumps(r, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    seen = {key(r) for r in rows(target)}
    additions = []
    for line in incoming.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict):
            raise ValueError('Forensic record must be an object')
        identity = key(record)
        if identity not in seen:
            seen.add(identity)
            additions.append(line+'\n')
    if additions:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('a') as out:
            if target.stat().st_size:
                with target.open('rb') as check:
                    check.seek(-1, 2)
                    if check.read(1) != b'\n':
                        out.write('\n')
            out.writelines(additions)


def merge(root, staged):
    for record in rows(staged/MANIFESTS):
        existing = cohort(root, record['football_day'])
        if existing and existing != record:
            raise ValueError('Refuse conflicting manifest publication')
    for relative in PATHS:
        if (staged/relative).exists():
            append_union(root/relative, staged/relative)
    from .scan_health import write_latest
    write_latest(root)
    for relative in (REPORT, Path('reports/europe_pinnacle_research_v2_status.json')):
        if not (staged/relative).exists():
            continue
        incoming = json.loads((staged/relative).read_text())
        current = json.loads((root/relative).read_text()) if (root/relative).exists() else {}
        if incoming.get('generated_at', '') >= current.get('generated_at', ''):
            (root/relative).parent.mkdir(parents=True, exist_ok=True)
            (root/relative).write_text(json.dumps(incoming, indent=2))


if __name__ == '__main__':
    import sys
    merge(Path('.'), Path(sys.argv[1]))
