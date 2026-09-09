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
    before = len(existing)
    for result in results:
        if not isinstance(result, dict) or result.get("fixture_id") is None:
            continue
        hg, ag = result.get("ft_home_goals"), result.get("ft_away_goals")
        if not isinstance(hg, int) or not isinstance(ag, int) or hg < 0 or ag < 0:
            continue
        existing[str(result["fixture_id"])] = result
    _write(path, existing)
    return len(existing) - before


def merge_results(path: Path, fixtures: list[dict]) -> int:
    normalized = []
    for fixture in fixtures:
        result = normalize_result(fixture)
        if result:
            normalized.append(result)
    return merge_normalized_results(path, normalized)
