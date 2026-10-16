"""Offline proof that sharding covers all fixtures with no duplicates or cap."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from odds_scanner.historical_manual import runner

NOW = datetime(2026, 10, 16, 16, tzinfo=timezone.utc)


def args(shard, shards=16):
    return argparse.Namespace(start_day="2026-09-05", end_day="2026-09-10",
        times="15:00,18:00,21:00,00:00", bookmakers="pinnacle",
        mode="plan", confirm_live_requests=False, fixture_shard=shard,
        fixture_shards=shards)


def write_source(root, number=64):
    path = root / "data/normalized/europe_pinnacle_research_v2_snapshots.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    fixtures = []
    for i in range(number):
        fid = "id" + str(500000+i)
        row = dict(fixture_id=fid, bookmaker="pinnacle",
            home="Home " + str(i), away="Away " + str(i),
            league="Premier League", kickoff="2026-09-05T14:00:00Z",
            observed_at="2026-09-05T08:00:00Z",
            source_semantics="CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED")
        fixtures.append(fid)
        with path.open("a") as out:
            out.write(json.dumps(row) + "\n")
    return fixtures


def test_shard_union_covers_all_known_fixtures_exactly_once(tmp_path):
    original = set(write_source(tmp_path))
    found = set()
    for i in range(16):
        report = runner.execute(args(i), root=tmp_path, clock=lambda: NOW,
            client_factory=lambda *_: (_ for _ in ()).throw(AssertionError("No HTTP")))
        assert report["status"] in ("PLANNED", "NO_VERIFIED_FIXTURES")
        manifest = json.loads((tmp_path/runner.OUT/"manifest.json").read_text())
        ids = {c["fixture_id"] for c in manifest["candidates"]}
        assert not (ids & found)
        assert all(int(hashlib.sha256(fid.encode()).hexdigest(), 16) % 16 == i
                   for fid in ids)
        assert manifest["all_candidate_pairs_before_sharding"] == len(original)
        assert manifest["fixture_bookmaker_pairs"] == len(ids)
        found.update(ids)
    assert found == original


def test_invalid_shard_arguments_block_without_http(tmp_path):
    write_source(tmp_path, 1)
    for opts in [args(16), args(-1), args(0, 0), args(0, 129),
                 argparse.Namespace(**{**vars(args(0)), "fixture_shards": None})]:
        report = runner.execute(opts, root=tmp_path, clock=lambda: NOW,
                client_factory=lambda *_: (_ for _ in ()).throw(AssertionError("No HTTP")))
        assert report["status"] == "BLOCKED"
        assert report["historical_requests"] == 0


def test_sharded_workflow_does_not_change_existing_manual_collector():
    f = Path(".github/workflows/sep05-10-sharded-recovery.yml")
    y = yaml.safe_load(f.read_text())
    jobs = y["jobs"]
    shards = jobs["recover"]["strategy"]["matrix"]["shard"]
    assert shards == list(range(16))
    assert jobs["recover"]["strategy"]["max-parallel"] == 1
    assert jobs["recover"]["environment"] == "historical-research"
    assert jobs["recover"]["timeout-minutes"] == 30
    assert jobs["publish"]["needs"] == "recover"
    assert "--fixture-shard" in f.read_text()
    assert "--fixture-shard" not in Path(".github/workflows/manual-historical-scan.yml").read_text()
