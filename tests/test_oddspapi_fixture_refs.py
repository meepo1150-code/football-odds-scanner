import json
from pathlib import Path

from odds_scanner.oddspapi_fixture_refs import merge_fixture_refs, normalize_fixture_ref


def test_normalize_fixture_ref_requires_at_least_one_exact_external_id():
    assert normalize_fixture_ref({"fixtureId": "f1", "externalProviders": {}}) is None
    row = normalize_fixture_ref({
        "fixtureId": "f1",
        "participant1Name": "Home",
        "participant2Name": "Away",
        "startTime": "2026-01-01T12:00:00Z",
        "externalProviders": {"sofascoreId": 12345, "betradarId": "sr:match:987", "flashscoreId": None},
    })
    assert row["fixture_id"] == "f1"
    assert row["sofascore_id"] == 12345
    assert row["external_providers"] == {"betradarId": "sr:match:987", "sofascoreId": 12345}
    assert row["mapping_source"] == "ODDSPAPI_EXTERNALPROVIDERS_EXACT_IDS"


def test_normalize_accepts_non_sofascore_exact_provider():
    row = normalize_fixture_ref({"fixtureId": "f1", "externalProviders": {"betradarId": 999}})
    assert row["external_providers"] == {"betradarId": 999}
    assert "sofascore_id" not in row


def test_merge_fixture_refs_deduplicates_and_merges_provider_ids(tmp_path: Path):
    path = tmp_path / "refs.jsonl"
    fixtures = [
        {"fixtureId": "f1", "externalProviders": {"sofascoreId": 10}},
        {"fixtureId": "f1", "externalProviders": {"sofascoreId": 10, "betradarId": 100}},
        {"fixtureId": "f2", "externalProviders": {"flashscoreId": "abc"}},
    ]
    assert merge_fixture_refs(path, fixtures) == 2
    rows = {r["fixture_id"]: r for r in map(json.loads, path.read_text().splitlines())}
    assert rows["f1"]["external_providers"] == {"betradarId": 100, "sofascoreId": 10}
    assert rows["f2"]["external_providers"] == {"flashscoreId": "abc"}


def test_merge_migrates_legacy_sofascore_only_row(tmp_path: Path):
    path = tmp_path / "refs.jsonl"
    path.write_text('{"fixture_id":"f1","sofascore_id":10,"mapping_source":"legacy"}\n', encoding="utf-8")
    merge_fixture_refs(path, [{"fixtureId":"f1","externalProviders":{"betradarId":100}}])
    row = json.loads(path.read_text())
    assert row["external_providers"] == {"betradarId": 100, "sofascoreId": 10}
    assert row["sofascore_id"] == 10
