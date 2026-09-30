from __future__ import annotations

from pathlib import Path
import json
from datetime import datetime, timezone
from urllib.error import HTTPError

from . import oddspapi_history_archive_sharded as archive
from .oddspapi_fixture_refs import REFS_PATH, merge_fixture_refs
from .oddspapi_provider import SPORT_ID, _get as provider_get
from .oddspapi_result_cache import RESULTS_PATH, merge_results

_ROOT = Path(".")


def _history_aware_get(path: str, key: str, params=None):
    """Translate provider-specific missing-history 404s into an empty history."""
    try:
        return provider_get(path, key, params)
    except HTTPError as exc:
        if path == "/historical-odds" and exc.code == 404:
            return {"bookmakers": {}}
        raise


def discover_finished_big5_window(key: str, start, end) -> list[dict]:
    """Discover finished Big-5 fixtures and retain exact provider references."""
    payload = provider_get(
        "/fixtures", key,
        {"sportId": SPORT_ID, "from": archive._iso(start), "to": archive._iso(end), "limit": 300, "language": "en"},
    )
    raw_finished: list[dict] = []
    found: list[dict] = []
    for fixture in archive._rows(payload):
        if fixture.get("statusId") != 2:
            continue
        try:
            tid_int = int(fixture.get("tournamentId"))
        except (TypeError, ValueError):
            continue
        if tid_int not in archive.BIG5_TOURNAMENTS or fixture.get("fixtureId") is None:
            continue
        raw_finished.append(fixture)
        found.append(archive._compact_fixture(fixture))

    # No extra OddsPapi request: preserve any explicit scores and exact external IDs
    # from the already-billable fixture discovery response.
    merge_results(_ROOT / RESULTS_PATH, raw_finished)
    merge_fixture_refs(_ROOT / REFS_PATH, raw_finished)

    dedup = {str(f["fixtureId"]): f for f in found}
    rows = list(dedup.values())
    rows.sort(key=lambda f: str(f.get("startTime") or ""))
    return rows


def main() -> None:
    archive._discover_window = discover_finished_big5_window
    archive._get = _history_aware_get
    from .provider_request_budget import QuotaBlocked
    try:
        print(archive.run_archive(_ROOT))
    except QuotaBlocked as exc:
        path = _ROOT / 'reports/oddspapi_history_state.json'
        state = json.loads(path.read_text()) if path.exists() else {}
        state.update(status='WAITING_EXTERNAL_DATA', provider_health='QUOTA_BLOCKED',
                     generated_at=datetime.now(timezone.utc).isoformat(), reason=str(exc))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2))
        print(json.dumps({'status':state['status'],'reason':str(exc),'cursor_preserved':True}))


if __name__ == "__main__":
    main()
