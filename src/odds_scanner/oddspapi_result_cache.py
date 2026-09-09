from __future__ import annotations

import json
from pathlib import Path
from .oddspapi_result_join import normalize_result

RESULTS_PATH=Path("data/normalized/oddspapi_finished_results.jsonl")


def merge_results(path: Path, fixtures: list[dict]) -> int:
    existing={}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try: row=json.loads(line)
            except json.JSONDecodeError: continue
            if isinstance(row,dict) and row.get("fixture_id") is not None:
                existing[str(row["fixture_id"])]=row
    before=len(existing)
    for fixture in fixtures:
        result=normalize_result(fixture)
        if result: existing[result["fixture_id"]]=result
    path.parent.mkdir(parents=True,exist_ok=True)
    rows=[existing[k] for k in sorted(existing)]
    path.write_text("".join(json.dumps(r,separators=(",",":"))+"\n" for r in rows),encoding="utf-8")
    return len(existing)-before
