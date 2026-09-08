from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError

from . import oddspapi_history_archive as archive
from .oddspapi_provider import SPORT_ID, _get as provider_get


def _history_aware_get(path: str, key: str, params=None):
    """Translate provider-specific missing-history 404s into an empty history.

    OddsPapi returns HTTP 404 when a valid finished fixture has no retained
    historical-odds payload. That is a permanent data-availability result, not a
    transient transport failure. Other HTTP errors must propagate so the archive
    engine requeues the fixture instead of silently dropping it.
    """
    try:
        return provider_get(path, key, params)
    except HTTPError as exc:
        if path == "/historical-odds" and exc.code == 404:
            return {"bookmakers": {}}
        raise


def discover_finished_big5_window(key: str, start, end) -> list[dict]:
    """Discover finished Big-5 fixtures using the documented /v4/fixtures contract.

    Historical discovery intentionally does not require the fixture-level
    `hasOdds` flag. That flag describes current fixture-list odds availability and
    can be false/absent for already-finished matches even when the dedicated
    historical-odds endpoint retains Bet365 price history. We therefore request a
    minimal fixture list, filter only finished status and validated Big-5 league
    identity locally, then let `/historical-odds` be the authority on whether
    usable archived prices exist.
    """
    payload = provider_get(
        "/fixtures",
        key,
        {
            "sportId": SPORT_ID,
            "from": archive._iso(start),
            "to": archive._iso(end),
            "limit": 300,
            "language": "en",
        },
    )
    found: list[dict] = []
    for fixture in archive._rows(payload):
        if fixture.get("statusId") != 2:
            continue
        tid = fixture.get("tournamentId")
        try:
            tid_int = int(tid)
        except (TypeError, ValueError):
            continue
        if tid_int not in archive.BIG5_TOURNAMENTS:
            continue
        if fixture.get("fixtureId") is None:
            continue
        found.append(archive._compact_fixture(fixture))

    dedup = {str(f["fixtureId"]): f for f in found}
    rows = list(dedup.values())
    rows.sort(key=lambda f: str(f.get("startTime") or ""))
    return rows


def main() -> None:
    # Provider-specific adapters retain provider HTTP semantics outside the
    # provider-neutral archive engine.
    archive._discover_window = discover_finished_big5_window
    archive._get = _history_aware_get
    print(archive.run_archive(Path(".")))


if __name__ == "__main__":
    main()
