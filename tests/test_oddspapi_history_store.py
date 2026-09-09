import json
from pathlib import Path

from odds_scanner.oddspapi_history_store import append_row, archived_fixture_ids, iter_rows, shard_path


def test_shard_path_uses_utc_kickoff_day(tmp_path: Path):
    row = {"fixture_id": "f1", "kickoff": "2026-02-14T23:30:00-02:00"}
    path = shard_path(tmp_path, row)
    assert path.name == "2026-02-15.jsonl"


def test_store_reads_legacy_and_daily_shards_without_duplicates_by_storage(tmp_path: Path):
    legacy = tmp_path / "data/normalized/oddspapi_history_ticks.jsonl"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({"fixture_id": "legacy", "kickoff": "2026-01-01T12:00:00Z"}) + "\n", encoding="utf-8")

    append_row(tmp_path, {"fixture_id": "new", "kickoff": "2026-02-08T14:00:00Z"})

    rows = list(iter_rows(tmp_path))
    assert {row["fixture_id"] for row in rows} == {"legacy", "new"}
    assert archived_fixture_ids(tmp_path) == {"legacy", "new"}


def test_append_row_never_modifies_legacy_monolith(tmp_path: Path):
    legacy = tmp_path / "data/normalized/oddspapi_history_ticks.jsonl"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("legacy-content\n", encoding="utf-8")

    path = append_row(tmp_path, {"fixture_id": "f2", "kickoff": "2026-02-08T14:00:00Z"})

    assert legacy.read_text(encoding="utf-8") == "legacy-content\n"
    assert path.name == "2026-02-08.jsonl"
    assert '"fixture_id":"f2"' in path.read_text(encoding="utf-8")
