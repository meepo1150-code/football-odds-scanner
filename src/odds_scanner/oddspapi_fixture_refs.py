from __future__ import annotations

import json
from pathlib import Path

REFS_PATH = Path("data/normalized/oddspapi_fixture_refs.jsonl")


def normalize_fixture_ref(fixture: dict) -> dict | None:
    """Preserve an exact OddsPapi -> external provider event-id mapping.

    No team-name matching is used. The external ID must be supplied directly
    by OddsPapi in the fixture payload.
    """
    fixture_id = fixture.get("fixtureId")
    providers = fixture.get("externalProviders")
    sofascore_id = providers.get("sofascoreId") if isinstance(providers, dict) else None
    if fixture_id is None or not isinstance(sofascore_id, (int, float)):
        return None
    sofascore_id = int(sofascore_id)
    if sofascore_id <= 0:
        return None
    return {
        "fixture_id": str(fixture_id),
        "sofascore_id": sofascore_id,
        "home": fixture.get("participant1Name"),
        "away": fixture.get("participant2Name"),
        "kickoff": fixture.get("startTime"),
        "mapping_source": "ODDSPAPI_EXTERNALPROVIDERS_SOFASCOREID",
    }


def merge_fixture_refs(path: Path, fixtures: list[dict]) -> int:
    existing: dict[str, dict] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("fixture_id") is not None:
                existing[str(row["fixture_id"])] = row
    before = len(existing)
    for fixture in fixtures:
        row = normalize_fixture_ref(fixture)
        if row:
            existing[row["fixture_id"]] = row
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(existing[k], ensure_ascii=False, separators=(",", ":")) + "\n" for k in sorted(existing)),
        encoding="utf-8",
    )
    return len(existing) - before
