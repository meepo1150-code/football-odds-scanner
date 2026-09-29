import json
from datetime import datetime, timedelta, timezone

from odds_scanner import propline_research_v2 as scanner


def test_unqualified_propline_quote_is_quarantined_not_canonical(tmp_path, monkeypatch):
    window_start, _, _ = scanner._football_day(datetime.now(timezone.utc))
    kickoff = (window_start + timedelta(hours=8)).astimezone(timezone.utc)
    row = {
        "kickoff": kickoff.isoformat(), "sport": "soccer_epl",
        "event_id": "123", "bookmaker": "pinnacle", "home": "A", "away": "B",
        "ah_home_line": -0.5, "ah_home_odds": 1.9,
        "ah_away_line": 0.5, "ah_away_odds": 1.95,
        "bookmaker_updated_at": (kickoff - timedelta(hours=6)).isoformat(),
    }
    monkeypatch.setattr(scanner, "fetch", lambda: ([row], []))
    report = scanner.run(tmp_path)

    assert not (tmp_path / scanner.SNAPSHOT_PATH).exists()
    audit_path = tmp_path / scanner.AUDIT_PATH
    audit = json.loads(audit_path.read_text().splitlines()[0])
    assert audit["eligibility_status"] == "QUARANTINED"
    assert audit["eligibility_reason"] == "PROPLINE_AH_SEMANTICS_UNVERIFIED"
    assert audit["research_population"] is False
    assert audit["quarantined"] is True
    assert report["strict_snapshots_this_run"] == 0
    assert report["quarantined_observations_this_run"] == 1

    # Re-running preserves a separate audit observation while canonical snapshots stay empty.
    scanner.run(tmp_path)
    observations = [json.loads(line) for line in audit_path.read_text().splitlines()]
    assert len(observations) == 2
    assert all(x["eligibility_status"] == "QUARANTINED" for x in observations)
