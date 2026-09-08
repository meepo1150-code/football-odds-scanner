from datetime import datetime, timedelta, timezone

from odds_scanner.execution_safety import execution_snapshot_status
from odds_scanner.market_contract import CurrentMarket


def _row(**overrides):
    now = datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc)
    values = dict(
        source="current_test",
        league="TEST",
        date="2026-09-07",
        kickoff="18:00",
        home="Home",
        away="Away",
        ah_home_line=-0.75,
        ah_home_odds=1.92,
        ah_away_line=0.75,
        ah_away_odds=1.96,
        ou_line=2.75,
        over_odds=1.94,
        under_odds=1.94,
        one_x_two_home=1.70,
        one_x_two_draw=3.80,
        one_x_two_away=5.20,
        status="scheduled",
        as_of=(now - timedelta(minutes=5)).isoformat(),
        stale=False,
        tradable=True,
    )
    values.update(overrides)
    return now, CurrentMarket(**values)


def test_fresh_open_prematch_quote_is_safe():
    now, row = _row()
    assert execution_snapshot_status(row, now=now) == (True, "EXECUTION_SAFE")


def test_stale_or_unverified_quote_is_rejected():
    now, row = _row(stale=True)
    assert execution_snapshot_status(row, now=now)[1] == "STALE_OR_UNVERIFIED_QUOTE"
    now, row = _row(stale=None)
    assert execution_snapshot_status(row, now=now)[1] == "STALE_OR_UNVERIFIED_QUOTE"


def test_inplay_and_nontradable_quotes_are_rejected():
    now, row = _row(status="live")
    assert execution_snapshot_status(row, now=now)[1] == "EXECUTION_STATUS_INVALID_OR_MISSING"
    now, row = _row(tradable=False)
    assert execution_snapshot_status(row, now=now)[1] == "MARKET_NOT_VERIFIED_TRADABLE"


def test_old_quote_is_rejected():
    now, _ = _row()
    _, row = _row(as_of=(now - timedelta(minutes=31)).isoformat())
    assert execution_snapshot_status(row, now=now, max_age_minutes=30)[1] == "QUOTE_TOO_OLD"


def test_missing_timestamp_fails_closed():
    now, row = _row(as_of=None)
    assert execution_snapshot_status(row, now=now)[1] == "QUOTE_TIMESTAMP_MISSING"


def test_verified_current_endpoint_uses_observation_not_old_price_change_time():
    now, row = _row(
        as_of=(now - timedelta(hours=8)).isoformat(),
        observed_at=(now - timedelta(minutes=2)).isoformat(),
        price_changed_at=(now - timedelta(hours=8)).isoformat(),
        freshness_basis="CURRENT_PROVIDER_ENDPOINT_ACTIVE_MARKETS_OBSERVED",
        current_feed_verified=True,
    )
    assert execution_snapshot_status(row, now=now) == (True, "EXECUTION_SAFE")


def test_unverified_provider_cannot_bypass_old_as_of_with_fetch_observation():
    now, row = _row(
        as_of=(now - timedelta(hours=8)).isoformat(),
        observed_at=now.isoformat(),
        freshness_basis="FETCH_TIME_ONLY",
        current_feed_verified=False,
    )
    assert execution_snapshot_status(row, now=now)[1] == "QUOTE_TOO_OLD"


def test_verified_current_feed_requires_observation_and_basis():
    now, row = _row(current_feed_verified=True, observed_at=None, freshness_basis="CURRENT_FEED")
    assert execution_snapshot_status(row, now=now)[1] == "OBSERVATION_TIMESTAMP_MISSING"
    now, row = _row(current_feed_verified=True, observed_at=now.isoformat(), freshness_basis=None)
    assert execution_snapshot_status(row, now=now)[1] == "CURRENT_FEED_FRESHNESS_BASIS_MISSING"


def test_verified_observation_itself_still_expires():
    now, row = _row(
        observed_at=(now - timedelta(minutes=31)).isoformat(),
        freshness_basis="CURRENT_FEED",
        current_feed_verified=True,
    )
    assert execution_snapshot_status(row, now=now, max_age_minutes=30)[1] == "QUOTE_TOO_OLD"
