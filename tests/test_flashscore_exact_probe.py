import json
from pathlib import Path

from odds_scanner.flashscore_exact_probe import first_flashscore_ref


def test_first_flashscore_ref_requires_exact_external_provider_id(tmp_path: Path):
    path = tmp_path / "data/normalized/oddspapi_fixture_refs.jsonl"
    path.parent.mkdir(parents=True)
    rows = [
        {"fixture_id": "legacy", "sofascore_id": 1},
        {"fixture_id": "f1", "home": "Home", "away": "Away", "kickoff": "2026-02-08T12:00:00Z", "external_providers": {"flashscoreId": "ABC123", "betradarId": 99}},
    ]
    path.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
    ref = first_flashscore_ref(tmp_path)
    assert ref == {
        "fixture_id": "f1",
        "flashscore_id": "ABC123",
        "home": "Home",
        "away": "Away",
        "kickoff": "2026-02-08T12:00:00Z",
    }
