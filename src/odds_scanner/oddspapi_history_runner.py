from __future__ import annotations

from pathlib import Path

from . import oddspapi_history_archive as archive
from .oddspapi_provider import SPORT_ID, _get


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
    payload = _get(
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
    # Provider-specific discovery adapter; the archive engine retains all state,
    # pacing, dedupe, normalization, and promotion blocking semantics.
    archive._discover_window = discover_finished_big5_window
    print(archive.run_archive(Path(".")))


if __name__ == "__main__":
    main()
