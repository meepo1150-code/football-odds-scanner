from datetime import datetime, timezone

from odds_scanner.oddspapi_discovery import fixture_query


def test_fixture_query_is_exact_next_24h_prematch_bet365_window():
    now = datetime(2026, 9, 8, 8, 30, 15, tzinfo=timezone.utc)
    q = fixture_query(now)
    assert q == {
        "sportId": 10,
        "from": "2026-09-08T08:30:15Z",
        "to": "2026-09-09T08:30:15Z",
        "statusId": 0,
        "hasOdds": "true",
        "bookmakers": "bet365",
        "language": "en",
    }


def test_fixture_query_normalizes_non_utc_aware_input_to_utc():
    now = datetime.fromisoformat("2026-09-08T15:30:00+07:00")
    q = fixture_query(now, hours=6)
    assert q["from"] == "2026-09-08T08:30:00Z"
    assert q["to"] == "2026-09-08T14:30:00Z"
