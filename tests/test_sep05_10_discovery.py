"""Network-free native-ID discovery and September 5-10 coverage tests."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from odds_scanner.historical_manual import planner, sep05_10_discovery as discovery
from odds_scanner.historical_manual.safety import StopPilot

NOW = datetime(2026, 10, 16, 16, tzinfo=timezone.utc)
ENV = dict(GITHUB_REF="refs/heads/main", PILOT_ENVIRONMENT="historical-research",
           HISTORICAL_ODDSPAPI_KEY="research-fixture-test-key",
           ACCOUNT_PROBE_KEY="production-fixture-test-key")


def sample_fixture(fid="id123", ko="2026-09-05T13:00:00Z", tid=17, status=2):
    return dict(fixtureId=fid, sportId=10, tournamentId=tid, statusId=status,
                startTime=ko, participant1Name="Home", participant2Name="Away",
                hasOdds=False)


@pytest.fixture(autouse=True)
def registry(monkeypatch):
    rows = [dict(tournament_id=17, tournament_name="Premier League")]
    monkeypatch.setattr(discovery, "registry", lambda: rows)
    monkeypatch.setattr("odds_scanner.master_schedule_plan.registry", lambda: rows)


def test_fixture_receipt_verified_without_provider_has_odds():
    receipt, coverage = discovery.validated_receipt([sample_fixture()], NOW)
    assert receipt["endpoint"] == "/fixtures"
    assert receipt["response_id"] == discovery.receipt_digest(
        {k: v for k, v in receipt.items() if k != "response_id"})
    assert coverage["approved_finished_fixture_rows"] == 1
    assert coverage["approved_by_football_day"] == {"2026-09-05": 1}


def test_bangkok_early_morning_is_previous_football_day():
    receipt, coverage = discovery.validated_receipt([
        sample_fixture("id1", "2026-09-10T21:30:00Z"),
        sample_fixture("id2", "2026-09-10T23:10:00Z"),
        sample_fixture("id3", "2026-09-04T22:30:00Z"),
        sample_fixture("id4", "2026-09-05T15:00:00Z", status=3),
    ], NOW)
    assert coverage["approved_finished_fixture_rows"] == 1
    assert coverage["approved_by_football_day"] == {"2026-09-10": 1}


def test_native_receipt_is_accepted_by_existing_planner(tmp_path):
    receipt, _ = discovery.validated_receipt([sample_fixture()], NOW)
    path = tmp_path / discovery.PATH
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(receipt) + "\n")
    manifest = planner.build(tmp_path, discovery.START, discovery.END,
                             "15:00,18:00,21:00,00:00", discovery.BOOKS, NOW)
    assert manifest["unique_fixtures"] == 1
    assert manifest["fixture_bookmaker_pairs"] == 2
    assert all(c["evidence"][0]["response_id"] == receipt["response_id"]
               for c in manifest["candidates"])
    assert all(c["football_day"] == "2026-09-05" for c in manifest["candidates"])


def test_receipt_tampering_rejected(tmp_path):
    receipt, _ = discovery.validated_receipt([sample_fixture()], NOW)
    receipt["payload"][0]["participant1Name"] = "Tampered"
    path = tmp_path / discovery.PATH
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(receipt) + "\n")
    with pytest.raises(ValueError, match="HASH_MISMATCH"):
        planner.build(tmp_path, discovery.START, discovery.END,
                      "15:00", "pinnacle", NOW)


def account_payload(name, calls):
    is_research = name == ENV["HISTORICAL_ODDSPAPI_KEY"]
    return dict(current_subscription_id=name,
        subscriptions=[dict(subscription_id=name, is_active=True, request_limit=180,
                            request_count=int(is_research and calls["fixtures"] > 0),
                            sport_ids=[10], bookmakers={"pinnacle": {}, "bet365": {}})])


def fake_transport(calls):
    def factory(key):
        def call(path, params):
            if path == "/account":
                return 200, {}, json.dumps(account_payload(key, calls)).encode()
            assert path == "/fixtures" and params == discovery.PARAMS
            assert key == ENV["HISTORICAL_ODDSPAPI_KEY"]
            calls["fixtures"] += 1
            return 200, {}, json.dumps([sample_fixture()]).encode()
        return call
    return factory


def test_one_billable_request_then_cache_no_duplicate(tmp_path):
    calls = {"fixtures": 0}
    health = lambda: dict(generated_at=NOW.isoformat(), status="PASS", issues=[])
    report = discovery.execute(root=tmp_path, now=NOW, env=ENV,
                 factory=fake_transport(calls), health_reader=health)
    assert report["billable_discovery_requests"] == 1
    assert report["approved_fixture_count"] == 1
    assert report["fixture_bookmaker_pairs"] == 2
    assert report["dispatch_recovery"] is True
    second = discovery.execute(root=tmp_path, now=NOW, env=ENV,
                 factory=lambda _: pytest.fail("Provider call forbidden on rerun"))
    assert second["billable_discovery_requests"] == 0
    assert calls["fixtures"] == 1


def test_shared_subscription_fails_before_fixture_request(tmp_path):
    calls = {"fixtures": 0}
    health = lambda: dict(generated_at=NOW.isoformat(), status="PASS", issues=[])
    with pytest.raises(StopPilot, match="NOT_ISOLATED"):
        discovery.execute(root=tmp_path, now=NOW,
            env=dict(ENV, ACCOUNT_PROBE_KEY=ENV["HISTORICAL_ODDSPAPI_KEY"]),
            factory=fake_transport(calls), health_reader=health)
    assert calls["fixtures"] == 0


def test_workflow_preserves_original_manual_action():
    import yaml
    wf = yaml.safe_load(Path(".github/workflows/sep05-10-fixture-discovery.yml").read_text())
    text = Path(".github/workflows/sep05-10-fixture-discovery.yml").read_text()
    assert "HISTORICAL_ODDSPAPI_KEY" in text
    assert "gh workflow run manual-historical-scan.yml" in text
    assert "confirm_live_requests=true" in text
    assert "pages.yml" not in text
    assert wf["jobs"]["discover"]["environment"] == "historical-research"
