from __future__ import annotations

import json
from pathlib import Path

REFS_PATH = Path("data/normalized/oddspapi_fixture_refs.jsonl")

# Documented/current OddsPapi externalProviders keys that are useful as exact
# cross-provider fixture identifiers. Preserve only IDs supplied by OddsPapi;
# never synthesize or name-match a missing mapping.
EXTERNAL_PROVIDER_KEYS = (
    "betradarId",
    "mollybetId",
    "opticoddsId",
    "lsportsId",
    "txoddsId",
    "sofascoreId",
    "betgeniusId",
    "flashscoreId",
    "pinnacleId",
    "oddinId",
)


def _clean_external_id(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not value.is_integer():
            return None
        value = int(value)
        return value if value > 0 else None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return None


def normalize_fixture_ref(fixture: dict) -> dict | None:
    """Preserve exact OddsPapi-provided external provider event IDs.

    No team-name/date matching is used. At least one external identifier must
    be present directly in `externalProviders`.
    """
    fixture_id = fixture.get("fixtureId")
    providers = fixture.get("externalProviders")
    if fixture_id is None or not isinstance(providers, dict):
        return None

    exact = {}
    for key in EXTERNAL_PROVIDER_KEYS:
        value = _clean_external_id(providers.get(key))
        if value is not None:
            exact[key] = value
    if not exact:
        return None

    row = {
        "schema_version": "1.1",
        "fixture_id": str(fixture_id),
        "home": fixture.get("participant1Name"),
        "away": fixture.get("participant2Name"),
        "kickoff": fixture.get("startTime"),
        "external_providers": exact,
        "mapping_source": "ODDSPAPI_EXTERNALPROVIDERS_EXACT_IDS",
    }
    # Compatibility field for the existing isolated SofaScore adapter while
    # downstream code migrates to external_providers.
    if "sofascoreId" in exact:
        row["sofascore_id"] = exact["sofascoreId"]
    return row


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
            previous = existing.get(row["fixture_id"])
            if isinstance(previous, dict):
                old_external = previous.get("external_providers")
                if isinstance(old_external, dict):
                    merged = dict(old_external)
                    merged.update(row["external_providers"])
                    row["external_providers"] = merged
                # Migrate legacy SofaScore-only rows without losing the ID.
                legacy_sofa = _clean_external_id(previous.get("sofascore_id"))
                if legacy_sofa is not None:
                    row["external_providers"].setdefault("sofascoreId", legacy_sofa)
                    row["sofascore_id"] = row["external_providers"]["sofascoreId"]
            existing[row["fixture_id"]] = row
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(existing[k], ensure_ascii=False, separators=(",", ":")) + "\n" for k in sorted(existing)),
        encoding="utf-8",
    )
    return len(existing) - before
