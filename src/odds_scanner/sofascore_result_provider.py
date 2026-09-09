from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.request import Request, urlopen

from .oddspapi_fixture_refs import REFS_PATH
from .oddspapi_result_cache import RESULTS_PATH, merge_normalized_results

BASE_URL = "https://www.sofascore.com/api/v1/event/{event_id}"
DEFAULT_RESULTS_PER_RUN = 20
REQUEST_SPACING_SECONDS = 1.2


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def normalize_sofascore_result(payload: dict, *, fixture_id: str, sofascore_id: int) -> dict | None:
    """Normalize an explicit finished normal-time result from one exact SofaScore event ID."""
    event = payload.get("event") if isinstance(payload.get("event"), dict) else payload
    if not isinstance(event, dict):
        return None
    status = event.get("status")
    if not isinstance(status, dict) or str(status.get("type") or "").lower() != "finished":
        return None
    event_id = event.get("id")
    if not isinstance(event_id, (int, float)) or int(event_id) != int(sofascore_id):
        return None
    home_score = event.get("homeScore")
    away_score = event.get("awayScore")
    if not isinstance(home_score, dict) or not isinstance(away_score, dict):
        return None
    hg, ag = home_score.get("normaltime"), away_score.get("normaltime")
    if not isinstance(hg, (int, float)) or not isinstance(ag, (int, float)):
        return None
    hg, ag = int(hg), int(ag)
    if hg < 0 or ag < 0:
        return None
    return {
        "fixture_id": str(fixture_id),
        "ft_home_goals": hg,
        "ft_away_goals": ag,
        "result_source": "SOFASCORE_EXACT_EXTERNAL_ID_NORMALTIME",
        "sofascore_id": int(sofascore_id),
    }


def fetch_sofascore_result(fixture_ref: dict, *, opener=urlopen) -> dict | None:
    fixture_id = fixture_ref.get("fixture_id")
    sofascore_id = fixture_ref.get("sofascore_id")
    if fixture_id is None or not isinstance(sofascore_id, int) or sofascore_id <= 0:
        return None
    req = Request(
        BASE_URL.format(event_id=sofascore_id),
        headers={"User-Agent": "football-odds-scanner/1.0"},
    )
    with opener(req, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return normalize_sofascore_result(payload, fixture_id=str(fixture_id), sofascore_id=sofascore_id)


def backfill_results(
    root: Path = Path("."),
    *,
    max_results: int = DEFAULT_RESULTS_PER_RUN,
    opener=urlopen,
    sleep_fn=time.sleep,
) -> dict:
    refs = _read_jsonl(root / REFS_PATH)
    existing = {str(r.get("fixture_id")) for r in _read_jsonl(root / RESULTS_PATH) if r.get("fixture_id") is not None}
    pending = [r for r in refs if str(r.get("fixture_id")) not in existing]
    fetched: list[dict] = []
    attempted = 0
    errors: list[str] = []
    for ref in pending[:max(0, max_results)]:
        if attempted:
            sleep_fn(REQUEST_SPACING_SECONDS)
        attempted += 1
        try:
            result = fetch_sofascore_result(ref, opener=opener)
            if result:
                fetched.append(result)
        except Exception as exc:
            errors.append(f"{ref.get('fixture_id')}:{type(exc).__name__}:{exc}")
    added = merge_normalized_results(root / RESULTS_PATH, fetched)
    return {
        "schema_version": "1.0",
        "classification": "EXACT_EXTERNAL_ID_RESULT_BACKFILL",
        "reference_rows": len(refs),
        "already_cached": len(existing),
        "attempted": attempted,
        "normalized_results": len(fetched),
        "results_added": added,
        "remaining_refs": max(0, len(pending) - attempted),
        "promotion_allowed": False,
        "errors": errors[:10],
    }


if __name__ == "__main__":
    print(backfill_results())
