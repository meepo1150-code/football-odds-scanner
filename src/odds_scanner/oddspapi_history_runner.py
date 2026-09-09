from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError

from . import oddspapi_history_archive as archive
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
    """Discover finished Big-5 fixtures and cache explicit FT results from the same payload."""
    payload = provider_get(
        "/fixtures", key,
        {"sportId": SPORT_ID, "from": archive._iso(start), "to": archive._iso(end), "limit": 300, "language": "en"},
    )
    raw_finished: list[dict] = []
    found: list[dict] = []
    for fixture in archive._rows(payload):
        if fixture.get("statusId") != 2:
            continue
        try: tid_int = int(fixture.get("tournamentId"))
        except (TypeError, ValueError): continue
        if tid_int not in archive.BIG5_TOURNAMENTS or fixture.get("fixtureId") is None:
            continue
        raw_finished.append(fixture)
        found.append(archive._compact_fixture(fixture))

    # No extra provider request: result cache is harvested from discovery itself.
    merge_results(_ROOT / RESULTS_PATH, raw_finished)
    dedup = {str(f["fixtureId"]): f for f in found}
    rows = list(dedup.values())
    rows.sort(key=lambda f: str(f.get("startTime") or ""))
    return rows


def main() -> None:
    archive._discover_window = discover_finished_big5_window
    archive._get = _history_aware_get
    print(archive.run_archive(_ROOT))


if __name__ == "__main__":
    main()
