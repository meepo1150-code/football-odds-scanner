from datetime import datetime, timezone

from odds_scanner.execution_safety import execution_snapshot_status
from odds_scanner.odds_api_io_provider import parse_event_odds


def _payload(updated="2026-09-08T06:20:00Z"):
    return {
        "id": 123,
        "sport": {"name": "Football", "slug": "football"},
        "league": {"name": "Premier League", "slug": "england-premier-league"},
        "home": "Alpha",
        "away": "Beta",
        "date": "2026-09-08T12:00:00Z",
        "status": "pending",
        "bookmakers": {
            "Bet365": [
                {"name": "ML", "updatedAt": updated, "odds": [{"home": "1.70", "draw": "3.80", "away": "5.00"}]},
                {"name": "Spread", "updatedAt": updated, "odds": [
                    {"hdp": -0.75, "home": "1.92", "away": "1.96"},
                    {"hdp": -1.0, "home": "2.10", "away": "1.80"},
                ]},
                {"name": "Totals", "updatedAt": updated, "odds": [
                    {"hdp": 2.75, "over": "1.94", "under": "1.94"},
                    {"hdp": 3.0, "over": "2.08", "under": "1.82"},
                ]},
            ]
        },
    }


def test_parser_emits_all_line_price_combinations_without_guessing_main():
    now = datetime(2026, 9, 8, 6, 25, tzinfo=timezone.utc)
    rows = parse_event_odds(_payload(), now=now)
    assert len(rows) == 4
    assert {(r.ah_home_line, r.ou_line) for r in rows} == {(-0.75, 2.75), (-0.75, 3.0), (-1.0, 2.75), (-1.0, 3.0)}
    row = rows[0]
    assert row.ah_away_line == -row.ah_home_line
    assert row.status == "scheduled"
    assert row.as_of == "2026-09-08T06:20:00+00:00"
    assert row.stale is False
    assert row.tradable is True


def test_oldest_required_market_timestamp_is_conservative():
    p = _payload("2026-09-08T06:20:00Z")
    p["bookmakers"]["Bet365"][1]["updatedAt"] = "2026-09-08T06:05:00Z"
    p["bookmakers"]["Bet365"][2]["updatedAt"] = "2026-09-08T06:24:00Z"
    rows = parse_event_odds(p, now=datetime(2026, 9, 8, 6, 25, tzinfo=timezone.utc))
    assert rows[0].as_of == "2026-09-08T06:05:00+00:00"
    assert rows[0].stale is False


def test_stale_snapshot_fails_execution_safety():
    rows = parse_event_odds(_payload("2026-09-08T05:00:00Z"), now=datetime(2026, 9, 8, 6, 0, tzinfo=timezone.utc))
    assert rows[0].stale is True
    ok, reason = execution_snapshot_status(rows[0], now=datetime(2026, 9, 8, 6, 0, tzinfo=timezone.utc))
    assert ok is False
    assert reason == "STALE_OR_UNVERIFIED_QUOTE"


def test_missing_market_timestamp_fails_closed():
    p = _payload()
    del p["bookmakers"]["Bet365"][1]["updatedAt"]
    rows = parse_event_odds(p, now=datetime(2026, 9, 8, 6, 25, tzinfo=timezone.utc))
    assert rows[0].as_of is None
    assert rows[0].stale is None
    ok, _ = execution_snapshot_status(rows[0], now=datetime(2026, 9, 8, 6, 25, tzinfo=timezone.utc))
    assert ok is False


def test_non_quarter_grid_line_is_ignored():
    p = _payload()
    p["bookmakers"]["Bet365"][1]["odds"] = [{"hdp": -0.7, "home": "1.92", "away": "1.96"}]
    assert parse_event_odds(p, now=datetime(2026, 9, 8, 6, 25, tzinfo=timezone.utc)) == []
