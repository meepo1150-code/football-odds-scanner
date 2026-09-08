from datetime import datetime, timezone

from odds_scanner.execution_safety import execution_snapshot_status
from odds_scanner.oddspapi_provider import parse_fixture_markets


def _catalog():
    return [
        {"marketId": 101, "marketName": "Full Time Result", "marketType": "1x2", "sportId": 10, "period": "fulltime", "playerProp": False, "handicap": 0, "outcomes": [{"outcomeId": 101, "outcomeName": "1"}, {"outcomeId": 102, "outcomeName": "X"}, {"outcomeId": 103, "outcomeName": "2"}]},
        {"marketId": 2001, "marketName": "Asian Handicap Full Time", "marketType": "handicap", "sportId": 10, "period": "fulltime", "playerProp": False, "handicap": -0.75, "outcomes": [{"outcomeId": 2001, "outcomeName": "Home"}, {"outcomeId": 2002, "outcomeName": "Away"}]},
        {"marketId": 3001, "marketName": "Over Under Full Time", "marketType": "totals", "sportId": 10, "period": "fulltime", "playerProp": False, "handicap": 2.75, "outcomes": [{"outcomeId": 3001, "outcomeName": "Over"}, {"outcomeId": 3002, "outcomeName": "Under"}]},
    ]


def _p(price, stamp="2026-09-08T10:00:00Z", active=True):
    return {"price": price, "active": active, "changedAt": stamp, "bookmakerChangedAt": None}


def _odds(stamp="2026-09-08T10:00:00Z"):
    return {"bookmakerOdds": {"bet365": {"bookmakerIsActive": True, "suspended": False, "markets": {
        "101": {"marketActive": True, "outcomes": {"101": {"players": {"0": _p(1.80, stamp)}}, "102": {"players": {"0": _p(3.80, stamp)}}, "103": {"players": {"0": _p(4.80, stamp)}}}},
        "2001": {"marketActive": True, "outcomes": {"2001": {"players": {"0": _p(1.92, stamp)}}, "2002": {"players": {"0": _p(1.96, stamp)}}}},
        "3001": {"marketActive": True, "outcomes": {"3001": {"players": {"0": _p(1.94, stamp)}}, "3002": {"players": {"0": _p(1.94, stamp)}}}},
    }}}}


def _fixture():
    return {"fixtureId": "id1", "startTime": "2026-09-08T18:00:00Z", "statusName": "Pre-Game", "tournamentName": "England Premier League", "participant1Name": "Alpha", "participant2Name": "Beta", "hasOdds": True}


def test_exact_quarter_lines_and_two_sided_prices_are_preserved():
    now = datetime(2026, 9, 8, 10, 10, tzinfo=timezone.utc)
    rows = parse_fixture_markets(_fixture(), _odds(), _catalog(), now=now)
    assert len(rows) == 1
    row = rows[0]
    assert row.ah_home_line == -0.75
    assert row.ah_away_line == 0.75
    assert row.ah_home_odds == 1.92
    assert row.ah_away_odds == 1.96
    assert row.ou_line == 2.75
    assert row.over_odds == row.under_odds == 1.94
    assert row.as_of == "2026-09-08T10:00:00Z"
    ok, reason = execution_snapshot_status(row, now=now)
    assert ok is True
    assert reason == "EXECUTION_SAFE"


def test_oldest_required_selection_timestamp_is_used_conservatively():
    odds = _odds("2026-09-08T10:08:00Z")
    odds["bookmakerOdds"]["bet365"]["markets"]["2001"]["outcomes"]["2001"]["players"]["0"]["bookmakerChangedAt"] = "2026-09-08T09:20:00Z"
    now = datetime(2026, 9, 8, 10, 10, tzinfo=timezone.utc)
    row = parse_fixture_markets(_fixture(), odds, _catalog(), now=now)[0]
    assert row.as_of == "2026-09-08T09:20:00Z"
    assert row.stale is True
    ok, reason = execution_snapshot_status(row, now=now)
    assert ok is False
    assert reason == "STALE_OR_UNVERIFIED_QUOTE"


def test_non_quarter_grid_market_is_not_rounded_or_emitted():
    catalog = _catalog()
    catalog[1]["handicap"] = -0.6
    rows = parse_fixture_markets(_fixture(), _odds(), catalog, now=datetime(2026, 9, 8, 10, 10, tzinfo=timezone.utc))
    assert rows == []


def test_suspended_bookmaker_fails_closed():
    odds = _odds()
    odds["bookmakerOdds"]["bet365"]["suspended"] = True
    assert parse_fixture_markets(_fixture(), odds, _catalog()) == []
