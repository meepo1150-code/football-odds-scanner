import pytest

from odds_scanner.five_dollar_history import normalize_finished_snapshot


def _fixture():
    return {
        "id": 99,
        "league": {"id": 1, "name": "Premier League"},
        "teams": {"home": {"name": "Alpha"}, "away": {"name": "Beta"}},
        "kickoff_utc": "2026-08-15T16:30:00+00:00",
        "status": "finished",
        "goals": {"home": 3, "away": 1},
    }


def _odds():
    return {
        "success": 1,
        "data": {
            "bookmakers": [{
                "slug": "bet365",
                "odds": {
                    "1x2": {
                        "opening": {"home": 1.70, "draw": 3.80, "away": 5.20},
                        "closing": {"home": 1.62, "draw": 4.00, "away": 5.80},
                    },
                    "asian_handicap": {
                        "opening": {"line": -0.75, "home": 1.92, "away": 1.96},
                        "closing": {"line": -1.0, "home": 2.02, "away": 1.86},
                    },
                    "goal_line": {
                        "opening": {"line": 2.5, "over": 1.90, "under": 1.98},
                        "closing": {"line": 2.75, "over": 1.95, "under": 1.93},
                    },
                },
            }],
        },
    }


def test_snapshot_normalizer_preserves_open_close_quarter_movement():
    row = normalize_finished_snapshot(_fixture(), _odds())
    assert row["favorite_side"] == "H"
    assert row["favorite_ah_line"] == -0.75
    assert row["favorite_ah_price"] == 1.92
    assert row["favorite_ah_other_price"] == 1.96
    assert row["closing_favorite_ah_line"] == -1.0
    assert row["closing_favorite_ah_price"] == 2.02
    assert row["closing_favorite_ah_other_price"] == 1.86
    assert row["ah_line_move"] == pytest.approx(-0.25)
    assert 0 < row["favorite_ah_normalized_price_share"] < 1
    assert 0 < row["closing_favorite_ah_normalized_price_share"] < 1
    assert row["ou_line"] == 2.5
    assert row["closing_ou_line"] == 2.75
    assert row["ou_line_move"] == pytest.approx(0.25)
    assert row["over_normalized_price_share"] + row["under_normalized_price_share"] == pytest.approx(1.0)
    assert row["closing_over_normalized_price_share"] + row["closing_under_normalized_price_share"] == pytest.approx(1.0)
    assert row["snapshot_semantics"].endswith("NO_TICKS")


def test_finished_fixture_is_required():
    fixture = _fixture()
    fixture["status"] = "scheduled"
    with pytest.raises(ValueError):
        normalize_finished_snapshot(fixture, _odds())


def test_non_quarter_line_fails_closed():
    odds = _odds()
    odds["data"]["bookmakers"][0]["odds"]["goal_line"]["opening"]["line"] = 2.6
    with pytest.raises(ValueError):
        normalize_finished_snapshot(_fixture(), odds)
