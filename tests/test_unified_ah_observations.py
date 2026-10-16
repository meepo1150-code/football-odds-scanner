import pytest
from odds_scanner.unified_ah_observations import merge


def sample(provenance="HISTORICAL_RECONSTRUCTED", price=1.95):
    return {
        "fixture_id": "fixture-1", "bookmaker": "pinnacle",
        "market": "AH", "slot_utc": "2026-09-20T08:00:00+00:00",
        "line_selection": "BALANCED_LINE", "provenance": provenance,
        "mainline_verified": False,
        "quotes": {
            "home": {"price": price, "quote_at_utc": "2026-09-20T07:59:00+00:00"},
            "away": {"price": 2.05, "quote_at_utc": "2026-09-20T07:59:00+00:00"},
        },
    }


def test_historical_replaces_matching_slot():
    live = {**sample(), "provenance": "LIVE", "quotes": sample( price=1.85)["quotes"]}
    assert merge([live], [sample()]) == [sample()]


def test_new_historical_slot_is_added():
    second = {**sample(), "fixture_id": "fixture-2"}
    assert len(merge([sample()], [second])) == 2


def test_idempotent_import():
    assert merge([sample()], [sample()]) == [sample()]


def test_reject_unreviewed_historical_quote():
    with pytest.raises(ValueError):
        merge([], [{**sample(), "line_selection": "MAINLINE_UNRESOLVED"}])


def test_reject_conflicting_live_duplicate():
    with pytest.raises(ValueError):
        merge([sample(price=1.85), sample(price=1.95)], [])
