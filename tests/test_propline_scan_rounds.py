import json
from datetime import datetime, time, timedelta, timezone

from odds_scanner import propline_research_v2 as scanner


def test_unchanged_bookmaker_quote_still_records_new_scan_round(tmp_path, monkeypatch):
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
    scanner.run(tmp_path)
    path = tmp_path / scanner.SNAPSHOT_PATH
    first = json.loads(path.read_text().splitlines()[0])
    assert first["price_changed_at"] == row["bookmaker_updated_at"]
    assert first["observed_at"] != row["bookmaker_updated_at"]

    # Re-running against unchanged prices must retain a separate observation.
    scanner.run(tmp_path)
    observations = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(observations) == 2
