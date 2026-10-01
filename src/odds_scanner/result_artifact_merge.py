"""Merge staged exact-result output onto fresh main before deriving statistics."""
from pathlib import Path
import json
import sys
from .oddspapi_result_cache import merge_normalized_results, RESULTS_PATH
from .daily_fixture_result_sync import _merge, FIXTURES_PATH


def rows(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []


def merge(staged, root=Path('.')):
    from .result_response_cache import merge_cache
    merge_cache(staged,root)
    from .result_recovery_lifecycle import merge as merge_recovery
    merge_recovery(staged,root)
    relative=RESULTS_PATH.with_suffix('.conflicts.jsonl')
    conflicts=rows(root/relative)+rows(staged/relative)
    if conflicts:
        path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(''.join(x+'\n' for x in sorted({json.dumps(r,sort_keys=True) for r in conflicts})))
    merge_normalized_results(root/RESULTS_PATH,rows(staged/RESULTS_PATH))
    if (staged/FIXTURES_PATH).exists():
        current=rows(root/FIXTURES_PATH)
        _merge(root/FIXTURES_PATH,rows(staged/FIXTURES_PATH)+current)


if __name__=='__main__': merge(Path(sys.argv[1]))
