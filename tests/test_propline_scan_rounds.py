import json
from datetime import datetime, timedelta, timezone
import pytest

from odds_scanner import propline_research_v2 as scanner


@pytest.fixture(autouse=True)
def fixed_scan_clock(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            value = cls(2026, 10, 3, 10, tzinfo=timezone.utc)
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)
    monkeypatch.setattr(scanner, 'datetime', Clock)


def _row(kickoff, *, price=1.9, book="pinnacle"):
    return {
        "kickoff": kickoff.isoformat(), "sport": "soccer_epl",
        "event_id": "123", "bookmaker": book, "home": "A", "away": "B",
        "ah_home_line": -0.5, "ah_home_odds": price,
        "ah_away_line": 0.5, "ah_away_odds": 1.95,
        "bookmaker_updated_at": (kickoff - timedelta(hours=6)).isoformat(),
    }


def test_verified_pinnacle_core_mainline_is_canonical(tmp_path, monkeypatch):
    window_start, _, _ = scanner._football_day(scanner.datetime.now(timezone.utc))
    kickoff = (window_start + timedelta(hours=8)).astimezone(timezone.utc)
    monkeypatch.setattr(scanner, "fetch", lambda: ([_row(kickoff)], []))
    report = scanner.run(tmp_path)
    snap=json.loads((tmp_path/scanner.SNAPSHOT_PATH).read_text().splitlines()[0])
    audit=json.loads((tmp_path/scanner.AUDIT_PATH).read_text().splitlines()[0])
    assert snap["mainline_verified"] is True
    assert snap["source_semantics"] == "PROPLINE_PINNACLE_TWO_SIDED_CORE_MAINLINE"
    assert 1.80 <= snap["ah"]["selected_side_price"] <= 2.20
    assert audit["eligibility_status"] == "ELIGIBLE"
    assert report["strict_snapshots_this_run"] == 1


def test_noncore_or_nonpinnacle_quote_is_quarantined(tmp_path, monkeypatch):
    window_start, _, _ = scanner._football_day(scanner.datetime.now(timezone.utc))
    kickoff = (window_start + timedelta(hours=8)).astimezone(timezone.utc)
    monkeypatch.setattr(scanner, "fetch", lambda: ([_row(kickoff, price=4.3)], []))
    report=scanner.run(tmp_path)
    assert not (tmp_path/scanner.SNAPSHOT_PATH).exists()
    audit=json.loads((tmp_path/scanner.AUDIT_PATH).read_text().splitlines()[0])
    assert audit["eligibility_status"] == "QUARANTINED"
    assert report["quarantined_observations_this_run"] == 1
