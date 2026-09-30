from __future__ import annotations

import json
from pathlib import Path
from .oddspapi_result_join import normalize_result

RESULTS_PATH = Path("data/normalized/oddspapi_finished_results.jsonl")


def _load(path: Path) -> dict[str, dict]:
    existing: dict[str, dict] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("fixture_id") is not None:
                existing[str(row["fixture_id"])] = row
    return existing


def _write(path: Path, existing: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(existing[k], separators=(",", ":")) + "\n" for k in sorted(existing)),
        encoding="utf-8",
    )


def merge_normalized_results(path: Path, results: list[dict]) -> int:
    """Merge already-normalized exact-ID result rows into the shared cache."""
    existing = _load(path)
    before_ids = set(existing)
    conflict_path = path.with_suffix('.conflicts.jsonl')
    conflicts = []
    if conflict_path.exists():
        for line in conflict_path.read_text(encoding="utf-8").splitlines():
            try: conflicts.append(json.loads(line))
            except json.JSONDecodeError: continue
    blocked = {str(r.get('fixture_id')) for r in conflicts}
    for result in results:
        if not isinstance(result, dict) or result.get("fixture_id") is None:
            continue
        hg, ag = result.get("ft_home_goals"), result.get("ft_away_goals")
        if type(hg) is not int or type(ag) is not int or hg < 0 or ag < 0:
            continue
        fid = str(result['fixture_id'])
        old = existing.get(fid)
        if old and (old.get('ft_home_goals'),old.get('ft_away_goals')) != (hg,ag):
            conflicts.append({'fixture_id':fid,'reason':'CONFLICTING_EXACT_RESULT_SCORES','existing':old,'incoming':result})
            blocked.add(fid)
        elif fid not in blocked and old is None:
            existing[fid] = result
    for fid in blocked:
        existing.pop(fid,None)
    if conflicts:
        conflict_path.parent.mkdir(parents=True,exist_ok=True)
        conflict_path.write_text(''.join(json.dumps(r,separators=(",",":"))+"\n" for r in conflicts),encoding='utf-8')
    _write(path, existing)
    return len(set(existing)-before_ids)


def merge_results(path: Path, fixtures: list[dict]) -> int:
    normalized = []
    for fixture in fixtures:
        result = normalize_result(fixture)
        if result:
            normalized.append(result)
    return merge_normalized_results(path, normalized)
