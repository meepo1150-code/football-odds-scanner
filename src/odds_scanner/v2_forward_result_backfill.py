from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .flashscore_result_provider import fetch_exact_result
from .oddspapi_result_cache import RESULTS_PATH, merge_normalized_results
from .v2_forward_entries import ENTRIES_PATH

REPORT_PATH = Path("reports/v2_forward_result_backfill.json")
RESULT_MATURITY_DELAY = timedelta(hours=3)


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _utc(value) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def select_result_candidates(entries: list[dict], existing_result_ids: set[str], *, now: datetime) -> list[dict]:
    """Choose one exact external-provider ref per matured forward fixture.

    No team/date discovery is allowed. A fixture must already carry the exact
    OddsPapi-supplied Flashscore event ID captured prospectively with the entry.
    """
    by_fixture: dict[str, dict] = {}
    for entry in entries:
        fixture_id = str(entry.get("fixture_id") or "")
        if not fixture_id or fixture_id in existing_result_ids or fixture_id in by_fixture:
            continue
        kickoff = _utc(entry.get("kickoff"))
        if kickoff is None or now.astimezone(timezone.utc) < kickoff + RESULT_MATURITY_DELAY:
            continue
        external = entry.get("external_providers")
        flashscore_id = external.get("flashscoreId") if isinstance(external, dict) else None
        if flashscore_id is None or not str(flashscore_id).strip():
            continue
        by_fixture[fixture_id] = {
            "fixture_id": fixture_id,
            "home": entry.get("home"),
            "away": entry.get("away"),
            "kickoff": entry.get("kickoff"),
            "external_providers": {"flashscoreId": flashscore_id},
            "mapping_source": "ODDSPAPI_CURRENT_EXTERNALPROVIDERS_EXACT_IDS_FROM_IMMUTABLE_FORWARD_ENTRY",
        }
    return sorted(by_fixture.values(), key=lambda r: (str(r.get("kickoff") or ""), str(r.get("fixture_id") or "")))


def run_backfill(
    root: Path = Path("."),
    *,
    now: datetime | None = None,
    max_requests: int = 10,
    sleep_seconds: float = 1.0,
) -> dict:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    entries = _load_jsonl(root / ENTRIES_PATH)
    existing_rows = _load_jsonl(root / RESULTS_PATH)
    existing_ids = {str(r.get("fixture_id")) for r in existing_rows if r.get("fixture_id") is not None}
    candidates = select_result_candidates(entries, existing_ids, now=current)

    attempted = 0
    normalized: list[dict] = []
    failures: list[dict] = []
    for ref in candidates[:max_requests]:
        attempted += 1
        result, meta = fetch_exact_result(ref)
        if result:
            result["forward_result_track"] = "VALIDATION_V2_PAPER_RESEARCH_ONLY"
            normalized.append(result)
        else:
            failures.append({
                "fixture_id": ref.get("fixture_id"),
                "flashscore_id": (ref.get("external_providers") or {}).get("flashscoreId"),
                **meta,
            })
        if sleep_seconds > 0 and attempted < min(max_requests, len(candidates)):
            time.sleep(sleep_seconds)

    added = merge_normalized_results(root / RESULTS_PATH, normalized)
    payload = {
        "schema_version": "1.0",
        "classification": "VALIDATION_V2_FORWARD_EXACT_RESULT_BACKFILL",
        "status": "RESULTS_ADDED" if added else ("REQUESTS_ATTEMPTED_NO_NEW_RESULTS" if attempted else "NO_MATURE_EXACT_ID_CANDIDATES"),
        "generated_at": current.isoformat(),
        "entry_rows": len(entries),
        "existing_result_rows": len(existing_rows),
        "maturity_delay_hours": RESULT_MATURITY_DELAY.total_seconds() / 3600.0,
        "eligible_exact_id_fixtures": len(candidates),
        "requests_attempted": attempted,
        "results_parsed": len(normalized),
        "results_added": added,
        "mapping_policy": "ODDSPAPI_CURRENT_EXTERNALPROVIDERS_FLASHSCOREID_EXACT_ONLY_FROM_FORWARD_ENTRY",
        "team_name_or_date_fuzzy_matching_allowed": False,
        "odds_api_requests": 0,
        "failures": failures[:20],
        "paper_label": "PAPER_RESEARCH_ONLY",
        "production_promotion_allowed": False,
    }
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(run_backfill(), ensure_ascii=False))
