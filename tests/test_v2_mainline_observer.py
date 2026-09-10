from datetime import datetime, timezone

import pytest

from odds_scanner.v2_mainline_observer import extract_mainline_snapshot, mainline_shape, match_candidates, split_target_batches


def _player(price, *, main=True):
    return {"active": True, "price": price, "mainLine": main, "changedAt": "2026-09-10T08:00:00Z"}


def _catalog(ah_line=-0.5, ou_line=2.5):
    return [
        {"marketId": 101, "sportId": 10, "period": "fulltime", "playerProp": False, "marketName": "Full Time Result", "marketType": "1x2", "handicap": 0, "outcomes": [
            {"outcomeId": 101, "outcomeName": "1"}, {"outcomeId": 102, "outcomeName": "X"}, {"outcomeId": 103, "outcomeName": "2"}
        ]},
        {"marketId": 201, "sportId": 10, "period": "fulltime", "playerProp": False, "marketName": "Asian Handicap", "marketType": "spreads", "handicap": ah_line, "outcomes": [
            {"outcomeId": 201, "outcomeName": "1"}, {"outcomeId": 202, "outcomeName": "2"}
        ]},
        {"marketId": 301, "sportId": 10, "period": "fulltime", "playerProp": False, "marketName": "Over Under Full Time", "marketType": "totals", "handicap": ou_line, "outcomes": [
            {"outcomeId": 301, "outcomeName": "Over"}, {"outcomeId": 302, "outcomeName": "Under"}
        ]},
    ]


def _market(outcomes):
    return {"marketActive": True, "outcomes": {str(k): {"players": {"0": v}} for k, v in outcomes.items()}}


def _fixture(*, ah_main=True, ou_main=True):
    return {
        "fixtureId": "id-test",
        "tournamentId": 17,
        "statusId": 0,
        "hasOdds": True,
        "startTime": "2026-09-11T12:00:00Z",
        "participant1Name": "Home",
        "participant2Name": "Away",
        "bookmakerOdds": {"bet365": {
            "bookmakerIsActive": True,
            "suspended": False,
            "markets": {
                "101": _market({101: _player(2.20), 102: _player(3.40), 103: _player(3.50)}),
                "201": _market({201: _player(1.90, main=ah_main), 202: _player(1.98, main=ah_main)}),
                "301": _market({301: _player(1.96, main=ou_main), 302: _player(1.90, main=ou_main)}),
            },
        }},
    }


def test_extract_requires_explicit_mainline_true():
    observed = datetime(2026, 9, 10, 9, tzinfo=timezone.utc)
    meta = {"universe": "BIG5_AH", "country": "England", "tournament_name": "Premier League"}
    snap, reason = extract_mainline_snapshot(_fixture(), _catalog(), observed_at=observed, tournament_meta=meta)
    assert reason == "OK"
    assert snap is not None
    assert snap["mainline_verified"] is True
    assert snap["ah"]["selected_side_line"] == -0.5
    assert snap["ah"]["selected_side_price"] == 1.90
    assert snap["ou"]["line"] == 2.5

    missing, reason = extract_mainline_snapshot(_fixture(ah_main=False), _catalog(), observed_at=observed, tournament_meta=meta)
    assert missing is None
    assert reason == "AMBIGUOUS_OR_MISSING_MAIN_AH"


def test_mainline_shape_reports_one_match_ah_and_one_match_total():
    shape = mainline_shape(_fixture(), _catalog())
    assert shape == {"ah_main_count": 1, "ou_main_count": 1, "ah_lines": [-0.5], "ou_lines": [2.5]}


def test_big5_home_minus_half_candidate_matches_exact_current_mainline():
    observed = datetime(2026, 9, 10, 9, tzinfo=timezone.utc)
    meta = {"universe": "BIG5_AH", "country": "England", "tournament_name": "Premier League"}
    snap, _ = extract_mainline_snapshot(_fixture(), _catalog(), observed_at=observed, tournament_meta=meta)
    candidates = [{
        "pattern_id": "FD_AH_4E30F9F2EC34", "universe": "BIG5_AH", "market": "AH",
        "pattern_key": {"favorite_side": "H", "ah_line": -0.5, "ah_price_band": [1.8, 2.0], "favorite_probability_band": [0.4, 0.5]},
    }]
    assert snap is not None
    assert match_candidates(snap, candidates) == ["FD_AH_4E30F9F2EC34"]


def test_third_universe_under_candidate_uses_main_ah_context_and_main_total():
    observed = datetime(2026, 9, 10, 9, tzinfo=timezone.utc)
    meta = {"universe": "THIRD_UNIVERSE_OU", "country": "Netherlands", "tournament_name": "Eredivisie"}
    fixture = _fixture()
    fixture["tournamentId"] = 99
    snap, reason = extract_mainline_snapshot(fixture, _catalog(ah_line=-0.25), observed_at=observed, tournament_meta=meta)
    candidates = [{
        "pattern_id": "FD_OU25_D0A17AE7DB9C", "universe": "THIRD_UNIVERSE_OU", "market": "OU",
        "pattern_key": {"favorite_side": "H", "ah_line": -0.25, "ou_side": "U", "ou_line": 2.5, "ou_price_band": [1.8, 2.0], "favorite_probability_band": [0.4, 0.5]},
    }]
    assert reason == "OK"
    assert snap is not None
    assert match_candidates(snap, candidates) == ["FD_OU25_D0A17AE7DB9C"]


def test_duplicate_main_ah_is_reported_and_rejected():
    observed = datetime(2026, 9, 10, 9, tzinfo=timezone.utc)
    fixture = _fixture()
    fixture["bookmakerOdds"]["bet365"]["markets"]["202"] = _market({201: _player(1.88), 202: _player(2.00)})
    catalog = _catalog() + [{
        "marketId": 202, "sportId": 10, "period": "fulltime", "playerProp": False,
        "marketName": "Asian Handicap", "marketType": "spreads", "handicap": -0.75,
        "outcomes": [{"outcomeId": 201, "outcomeName": "1"}, {"outcomeId": 202, "outcomeName": "2"}],
    }]
    shape = mainline_shape(fixture, catalog)
    assert shape["ah_main_count"] == 2
    assert shape["ah_lines"] == [-0.75, -0.5]
    snap, reason = extract_mainline_snapshot(fixture, catalog, observed_at=observed, tournament_meta={"universe": "BIG5_AH"})
    assert snap is None
    assert reason == "AMBIGUOUS_OR_MISSING_MAIN_AH"


def test_team_total_mainline_does_not_ambiguate_match_total():
    observed = datetime(2026, 9, 10, 9, tzinfo=timezone.utc)
    fixture = _fixture()
    fixture["bookmakerOdds"]["bet365"]["markets"]["401"] = _market({401: _player(1.91), 402: _player(1.91)})
    catalog = _catalog() + [{
        "marketId": 401, "sportId": 10, "period": "fulltime", "playerProp": False,
        "marketName": "Over Under Team 1", "marketType": "teamtotals-team1", "handicap": 1.5,
        "outcomes": [{"outcomeId": 401, "outcomeName": "Over"}, {"outcomeId": 402, "outcomeName": "Under"}],
    }]
    shape = mainline_shape(fixture, catalog)
    assert shape["ou_main_count"] == 1
    assert shape["ou_lines"] == [2.5]
    snap, reason = extract_mainline_snapshot(fixture, catalog, observed_at=observed, tournament_meta={"universe": "BIG5_AH"})
    assert reason == "OK"
    assert snap is not None


def test_split_target_batches_is_exactly_two_groups_of_five():
    selected = [
        *[{"universe": "BIG5_AH", "country": c, "tournament_id": i} for i, c in enumerate(["England", "France", "Germany", "Italy", "Spain"], 1)],
        *[{"universe": "THIRD_UNIVERSE_OU", "country": c, "tournament_id": i} for i, c in enumerate(["Belgium", "Netherlands", "Portugal", "Scotland", "Turkey"], 11)],
    ]
    batches = split_target_batches(selected)
    assert [name for name, _ in batches] == ["BIG5_AH", "THIRD_UNIVERSE_OU"]
    assert [len(rows) for _, rows in batches] == [5, 5]
    assert [row["country"] for row in batches[0][1]] == ["England", "France", "Germany", "Italy", "Spain"]


def test_split_target_batches_fails_closed_if_universe_is_incomplete():
    selected = [{"universe": "BIG5_AH", "country": "England", "tournament_id": 17}]
    with pytest.raises(ValueError):
        split_target_batches(selected)
