from pathlib import Path

from odds_scanner.oddspapi_fixture_refs import merge_fixture_refs, normalize_fixture_ref


def test_normalize_fixture_ref_requires_exact_sofascore_id():
    assert normalize_fixture_ref({"fixtureId": "f1", "externalProviders": {}}) is None
    row = normalize_fixture_ref({
        "fixtureId": "f1",
        "participant1Name": "Home",
        "participant2Name": "Away",
        "startTime": "2026-01-01T12:00:00Z",
        "externalProviders": {"sofascoreId": 12345},
    })
    assert row["fixture_id"] == "f1"
    assert row["sofascore_id"] == 12345
    assert row["mapping_source"] == "ODDSPAPI_EXTERNALPROVIDERS_SOFASCOREID"


def test_merge_fixture_refs_deduplicates_by_oddspapi_fixture_id(tmp_path: Path):
    path = tmp_path / "refs.jsonl"
    fixtures = [
        {"fixtureId": "f1", "externalProviders": {"sofascoreId": 10}},
        {"fixtureId": "f1", "externalProviders": {"sofascoreId": 10}},
        {"fixtureId": "f2", "externalProviders": {"sofascoreId": 20}},
    ]
    assert merge_fixture_refs(path, fixtures) == 2
    assert len(path.read_text().splitlines()) == 2
